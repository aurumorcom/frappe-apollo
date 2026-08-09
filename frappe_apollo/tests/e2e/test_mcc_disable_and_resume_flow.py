from unittest.mock import patch
import frappe
from frappe.tests import IntegrationTestCase

from frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence import (
	update_sequence_contact_status,
)


class TestMCCDisableAndResumeFlow(IntegrationTestCase):
	def test_e2e_mcc_disable_and_resume_sequence_contact_journey(self) -> None:
		"""E2E Journey Test:
		1. MCC in Scheduled status with active sequence contact.
		2. Disable MCC -> triggers update_sequence_contact_status(mode="stop").
		3. Re-enable MCC -> re-enqueues add_contact_to_sequence.
		"""
		account_name = "E2E-Acc-2"
		lead_name = "E2E-LEAD-002"
		mcc_name = "MCC-E2E-002"

		# Setup Cadence Provider
		if not frappe.db.exists("Cadence Provider", "Apollo"):
			frappe.get_doc({"doctype": "Cadence Provider", "provider_name": "Apollo", "enabled": 1}).insert()

		# Setup Apollo Account
		if not frappe.db.exists("Apollo Account", account_name):
			frappe.get_doc(
				{
					"doctype": "Apollo Account",
					"account_name": account_name,
					"status": "Authorized",
					"apollo_sequence_id": "seq_e2e_200",
				}
			).insert()

		# Setup Cadence
		if not frappe.db.exists("Email Template", "Test Template"):
			frappe.get_doc({"doctype": "Email Template", "name": "Test Template", "subject": "Test", "response": "Hello"}).insert(ignore_permissions=True)

		if not frappe.db.exists("Cadence", "E2E Cadence"):
			cadence = frappe.get_doc(
				{
					"doctype": "Cadence",
					"cadence_name": "E2E Cadence",
					"apollo_ids": [{"account": account_name, "sender": "Administrator", "email_account": "E2E Email"}],
					"cadence_schedules": [{"reference_doctype": "Email Template", "reference_name": "Test Template", "send_after_days": 1}],
				}
			)
			cadence.flags.ignore_links = True
			cadence.insert(ignore_permissions=True)
		else:
			cadence = frappe.get_doc("Cadence", "E2E Cadence")

		# Setup Lead
		if frappe.db.exists("CRM Lead", lead_name):
			frappe.delete_doc("CRM Lead", lead_name, force=True)

		lead = frappe.get_doc(
			{
				"doctype": "CRM Lead",
				"name": lead_name,
				"first_name": "Jane",
				"last_name": "Doe",
				"email": "jane.doe2@example.com",
				"apollo_ids": [{"account": account_name, "apollo_id": "contact_e2e_888"}],
			}
		)
		lead.flags.ignore_mandatory = True
		lead.insert(ignore_permissions=True)

		# Setup MCC
		if frappe.db.exists("Multi Channel Cadence", mcc_name):
			frappe.delete_doc("Multi Channel Cadence", mcc_name, force=True)

		mcc = frappe.get_doc(
			{
				"doctype": "Multi Channel Cadence",
				"name": mcc_name,
				"status": "Scheduled",
				"cadence_name": cadence.name,
				"sender": "Administrator",
				"recipient": lead.name,
				"apollo_account": account_name,
				"apollo_sequence_id": "seq_e2e_200",
				"apollo_contact_id": "contact_e2e_888",
				"provider": [{"cadence_provider": "Apollo"}],
			}
		).insert()

		from frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence import on_update

		# Step 1: Transition to Disabled -> should enqueue update_sequence_contact_status with mode="stop"
		with patch("frappe.enqueue") as mock_enqueue:
			mcc.db_set("status", "Disabled")
			mcc.get_doc_before_save = lambda: frappe._dict({"status": "Scheduled"})
			on_update(mcc)

			mock_enqueue.assert_called_once_with(
				method="frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.update_sequence_contact_status",
				queue="medium",
				mcc_name=mcc.name,
				mode="stop",
			)

		# Step 2: Execute update_sequence_contact_status directly
		with patch("frappe_apollo.integrations.apollo.ApolloClient") as mock_apollo_cls:
			mock_client = mock_apollo_cls.return_value
			update_sequence_contact_status(mcc.name, mode="stop")

			mock_client.update_sequence_contact_status.assert_called_once_with(
				"contact_e2e_888", "seq_e2e_200", "stop"
			)

		# Step 3: Transition back to Scheduled -> should enqueue add_contact_to_sequence
		with patch("frappe.enqueue") as mock_enqueue:
			mcc.db_set("status", "Scheduled")
			mcc.get_doc_before_save = lambda: frappe._dict({"status": "Disabled"})
			on_update(mcc)

			mock_enqueue.assert_called_once_with(
				method="frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.add_contact_to_sequence",
				queue="high",
				mcc_name=mcc.name,
			)

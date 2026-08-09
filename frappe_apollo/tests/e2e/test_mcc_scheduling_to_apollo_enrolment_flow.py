from unittest.mock import MagicMock, patch
import frappe
from frappe.tests import IntegrationTestCase
from frappe_controller.utils.controller import SuspendJob, emit_event

from frappe_apollo.apollo.doctype.crm_lead.crm_lead import _create_a_contact
from frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence import (
	add_contact_to_sequence,
)


class TestMCCSchedulingToApolloEnrolmentFlow(IntegrationTestCase):
	def setUp(self) -> None:
		frappe.db.delete("FS Job")
		frappe.db.delete("FS Event")
		frappe.db.delete("FS Match Condition")

	def test_e2e_mcc_scheduling_to_apollo_enrolment_journey(self) -> None:
		"""E2E Journey Test:
		1. Transition MCC from Draft to Scheduled.
		2. Verify background jobs are enqueued.
		3. Verify add_contact_to_sequence suspends waiting for doc:CRM Lead:<recipient>:on_update.
		4. Simulate _create_a_contact updating CRM Lead child table with apollo_id.
		5. Verify add_contact_to_sequence resumes and assigns contact to sequence in Apollo.
		"""
		account_name = "E2E-Acc-1"
		lead_name = "E2E-LEAD-001"
		mcc_name = "MCC-E2E-001"

		# Ensure Provider Enabled
		if not frappe.db.exists("Cadence Provider", "Apollo"):
			frappe.get_doc({"doctype": "Cadence Provider", "provider_name": "Apollo", "enabled": 1}).insert()
		else:
			frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 1)

		# Ensure Apollo Account
		if not frappe.db.exists("Apollo Account", account_name):
			frappe.get_doc(
				{
					"doctype": "Apollo Account",
					"account_name": account_name,
					"status": "Authorized",
					"apollo_sequence_id": "seq_e2e_100",
				}
			).insert()

		# Ensure Email Account
		if not frappe.db.exists("Email Account", "E2E Email"):
			frappe.get_doc(
				{
					"doctype": "Email Account",
					"email_account_name": "E2E Email",
					"email_id": "e2e_sender@example.com",
					"apollo_ids": [{"account": account_name, "apollo_id": "mb_e2e_200"}],
				}
			).insert()

		# Ensure User Email Mapping
		if not frappe.db.exists("User Email", {"parent": "Administrator", "email_account": "E2E Email"}):
			frappe.get_doc(
				{
					"doctype": "User Email",
					"parent": "Administrator",
					"parenttype": "User",
					"parentfield": "user_emails",
					"email_account": "E2E Email",
				}
			).insert()

		# Create Lead without apollo_id
		if frappe.db.exists("CRM Lead", lead_name):
			frappe.delete_doc("CRM Lead", lead_name, force=True)

		if not frappe.db.exists("CRM Organization", "Acme Corp"):
			frappe.get_doc({"doctype": "CRM Organization", "organization_name": "Acme Corp"}).insert(ignore_permissions=True)

		lead = frappe.get_doc(
			{
				"doctype": "CRM Lead",
				"name": lead_name,
				"first_name": "Jane",
				"last_name": "Doe",
				"email": "jane.doe@example.com",
				"organization": "Acme Corp",
				"apollo_ids": [{"account": account_name, "apollo_id": ""}],
			}
		)
		lead.flags.ignore_mandatory = True
		lead.insert(ignore_permissions=True)

		# Create Cadence
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

		# Create MCC in Draft
		if frappe.db.exists("Multi Channel Cadence", mcc_name):
			frappe.delete_doc("Multi Channel Cadence", mcc_name, force=True)

		mcc = frappe.get_doc(
			{
				"doctype": "Multi Channel Cadence",
				"name": mcc_name,
				"status": "Draft",
				"cadence_name": cadence.name,
				"sender": "Administrator",
				"recipient": lead.name,
				"apollo_account": account_name,
				"provider": [{"cadence_provider": "Apollo"}],
			}
		).insert()

		# Step 1 & 2: Change status to Scheduled and save
		with patch("frappe.enqueue") as mock_enqueue:
			mcc.status = "Scheduled"
			mcc.save()

			# Assert two enqueue calls: _create_a_contact and add_contact_to_sequence
			self.assertEqual(mock_enqueue.call_count, 2)
			enqueued_methods = [call.kwargs.get("method") for call in mock_enqueue.call_args_list]
			self.assertIn("frappe_apollo.apollo.doctype.crm_lead.crm_lead._create_a_contact", enqueued_methods)
			self.assertIn(
				"frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.add_contact_to_sequence",
				enqueued_methods,
			)

		# Set FS Job context for wait_for_event
		job_id = "test_e2e_mcc_job_1"
		if frappe.db.table_exists("FS Job"):
			frappe.db.sql(
				"INSERT IGNORE INTO `tabFS Job` (name, job_name, status, queue, creation, modified, modified_by, owner) VALUES (%s, %s, %s, %s, NOW(), NOW(), 'Administrator', 'Administrator')",
				(job_id, "test_e2e_job_func", "started", "high"),
			)
			frappe.db.commit()
		frappe.flags.current_job_id = job_id
		frappe.flags.current_job_step = 0

		# Step 3: Run add_contact_to_sequence directly - must suspend because lead missing apollo_id
		with patch("frappe_apollo.integrations.apollo.ApolloClient"):
			with self.assertRaises(SuspendJob) as cm:
				add_contact_to_sequence(mcc.name)

			# Verify correct event key format doc:CRM Lead:<recipient>:on_update
			self.assertEqual(cm.exception.event_key, f"doc:CRM Lead:{lead.name}:on_update")

		# Reset job flags for lead save
		frappe.flags.current_job_id = None
		frappe.flags.current_job_step = None

		# Step 4: Update lead with apollo_id and emit event
		lead.reload()
		for row in lead.apollo_ids:
			if row.account == account_name:
				row.apollo_id = "ap_contact_e2e_999"
		lead.flags.ignore_mandatory = True
		lead.save(ignore_permissions=True)

		emit_event(
			f"doc:CRM Lead:{lead.name}:on_update",
			lead.as_dict(),
		)

		# Step 5: Run add_contact_to_sequence again - must complete and assign contact in Apollo
		with patch("frappe_apollo.integrations.apollo.ApolloClient") as mock_apollo_cls:
			mock_client = mock_apollo_cls.return_value
			add_contact_to_sequence(mcc.name)

			mock_client.add_contacts_to_sequence.assert_called_once_with(
				"ap_contact_e2e_999",
				"seq_e2e_100",
				"mb_e2e_200",
				email_address="e2e_sender@example.com",
			)

			mcc.reload()
			self.assertEqual(mcc.apollo_contact_id, "ap_contact_e2e_999")

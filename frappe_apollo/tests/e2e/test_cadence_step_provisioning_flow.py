from unittest.mock import MagicMock, patch
import frappe
from frappe.tests import IntegrationTestCase
from frappe_controller.utils.background_jobs import JobPromise

from frappe_apollo.apollo.doctype.cadence.cadence import update_sequence_steps


class TestCadenceStepProvisioningFlow(IntegrationTestCase):
	def setUp(self) -> None:
		if frappe.db.table_exists("FS Job"):
			frappe.db.delete("FS Job")

	def test_e2e_cadence_step_provisioning_and_job_promise_execution(self) -> None:
		"""E2E Journey Test:
		1. Set up Cadence Provider, Apollo Account, Email Template, and Cadence with schedule.
		2. Enqueue update_sequence_steps and verify JobPromise returned.
		3. Execute update_sequence_steps with mocked ApolloClient.
		4. Assert that fields are created without 'ApolloField' object has no attribute 'field_type' error.
		5. Assert Apollo Field document 'subject_1' exists with apollo_ids mapping.
		"""
		account_name = "E2E-Provision-Acc"
		cadence_name = "E2E Provision Cadence"

		# Setup Cadence Provider
		if not frappe.db.exists("Cadence Provider", "Apollo"):
			frappe.get_doc({"doctype": "Cadence Provider", "provider_name": "Apollo", "enabled": 1}).insert()
		else:
			frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 1)

		# Setup Apollo Account
		if not frappe.db.exists("Apollo Account", account_name):
			frappe.get_doc(
				{
					"doctype": "Apollo Account",
					"account_name": account_name,
					"status": "Authorized",
					"apollo_sequence_id": "seq_e2e_999",
				}
			).insert()

		# Setup Email Template
		if not frappe.db.exists("Email Template", "E2E Provision Template"):
			frappe.get_doc(
				{
					"doctype": "Email Template",
					"name": "E2E Provision Template",
					"subject": "E2E Subject",
					"response": "E2E Response",
				}
			).insert(ignore_permissions=True)

		# Setup Cadence
		if frappe.db.exists("Cadence", cadence_name):
			frappe.delete_doc("Cadence", cadence_name, force=True)

		cadence = frappe.get_doc(
			{
				"doctype": "Cadence",
				"cadence_name": cadence_name,
				"apollo_ids": [{"account": account_name, "sender": "Administrator", "email_account": "E2E Email"}],
				"cadence_schedules": [
					{
						"channel": "Email",
						"reference_doctype": "Email Template",
						"reference_name": "E2E Provision Template",
						"send_after_days": 1,
					}
				],
			}
		)
		cadence.flags.ignore_links = True
		cadence.insert(ignore_permissions=True)

		# Clean up pre-existing Apollo Field records for subject_1 and body_1
		frappe.delete_doc_if_exists("Apollo Field", "subject_1", force=True)
		frappe.delete_doc_if_exists("Apollo Field", "body_1", force=True)

		# Step 1: Enqueue background job and inspect JobPromise
		promise = frappe.enqueue(
			"frappe_apollo.apollo.doctype.cadence.cadence.update_sequence_steps",
			queue="low",
			cadence_name=cadence.name,
			account_name=account_name,
		)
		self.assertIsInstance(promise, JobPromise)

		# Step 2: Execute update_sequence_steps with mocked Apollo API client
		mock_client = MagicMock()
		mock_client.create_custom_field.side_effect = lambda label, field_type: {
			"typed_custom_fields": [{"id": f"apollo_field_id_{label}"}]
		}
		mock_client.get_sequence.return_value = {"emailer_steps": []}

		with patch("frappe_apollo.apollo.doctype.cadence.cadence.ApolloClient", return_value=mock_client):
			# Should execute smoothly without 'ApolloField' object has no attribute 'field_type'
			update_sequence_steps(cadence.name, account_name)

		# Step 3: Verify created Apollo Field documents and child table apollo_ids mappings
		self.assertTrue(frappe.db.exists("Apollo Field", "subject_1"))
		subject_field_doc = frappe.get_doc("Apollo Field", "subject_1")
		mapped_accounts = [r.account for r in subject_field_doc.apollo_ids]
		self.assertIn(account_name, mapped_accounts)

		mapped_id = next(r.apollo_id for r in subject_field_doc.apollo_ids if r.account == account_name)
		self.assertEqual(mapped_id, "apollo_field_id_subject_1")

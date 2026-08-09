from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe_controller.utils.controller import SuspendJob

from frappe_apollo.apollo.doctype.apollo_field.apollo_field import provision_a_field
from frappe_apollo.apollo.doctype.cadence.cadence import (
	_disable_cadence_mccs,
	_validate_for_sequence,
	on_update,
)
from frappe_apollo.apollo.doctype.crm_lead.crm_lead import (
	_create_a_contact,
	create_a_contact,
	update_a_contact,
)
from frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence import (
	add_contact_to_sequence,
	before_save,
)
from frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence import (
	on_update as mcc_on_update,
)


class TestApolloLifecycleE2E(IntegrationTestCase):
	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def setUp(self):
		super().setUp()

		if not frappe.db.exists("Cadence Provider", "Apollo"):
			frappe.get_doc({"doctype": "Cadence Provider", "provider_name": "Apollo", "enabled": 0}).insert(
				ignore_permissions=True
			)
		else:
			frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 0)

		if not frappe.db.exists("Apollo Account", "TestAccount1"):
			frappe.get_doc(
				{
					"doctype": "Apollo Account",
					"account_name": "TestAccount1",
					"apollo_sequence_id": "seq_account_1",
					"status": "Unauthorized",
					"api_key": "test_key_1",
				}
			).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Apollo Account", "TestAccount1", "status", "Unauthorized")
			frappe.db.set_value("Apollo Account", "TestAccount1", "apollo_sequence_id", "seq_account_1")

		if not frappe.db.exists("Apollo Account", "TestAccount2"):
			frappe.get_doc(
				{
					"doctype": "Apollo Account",
					"account_name": "TestAccount2",
					"apollo_sequence_id": "seq_account_2",
					"status": "Authorized",
					"api_key": "test_key_2",
				}
			).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Apollo Account", "TestAccount2", "status", "Authorized")
			frappe.db.set_value("Apollo Account", "TestAccount2", "apollo_sequence_id", "seq_account_2")

		if not frappe.db.exists("User", "test_sender@example.com"):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": "test_sender@example.com",
					"first_name": "Test",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Email Account", "TestEmailAccount1"):
			frappe.get_doc(
				{
					"doctype": "Email Account",
					"email_account_name": "TestEmailAccount1",
					"email_id": "test_sender@example.com",
					"apollo_ids": [
						{"account": "TestAccount1", "apollo_id": "mailbox_1"},
						{"account": "TestAccount2", "apollo_id": "mailbox_1"},
					],
					"append_to": "Communication",
				}
			).insert(ignore_permissions=True)
		else:
			email_doc = frappe.get_doc("Email Account", "TestEmailAccount1")
			if not any(r.account == "TestAccount2" for r in email_doc.apollo_ids):
				email_doc.append("apollo_ids", {"account": "TestAccount2", "apollo_id": "mailbox_1"})
				email_doc.save(ignore_permissions=True)

		if not frappe.db.exists(
			"User Email", {"parent": "test_sender@example.com", "email_account": "TestEmailAccount1"}
		):
			user = frappe.get_doc("User", "test_sender@example.com")
			user.append(
				"user_emails", {"email_account": "TestEmailAccount1", "email_id": "test_sender@example.com"}
			)
			user.save(ignore_permissions=True)

		lead_id = frappe.db.get_value("CRM Lead", {"email": "lead1@example.com"}, "name")
		if not lead_id:
			lead = frappe.get_doc(
				{
					"doctype": "CRM Lead",
					"first_name": "Lead",
					"last_name": "1",
					"email": "lead1@example.com",
					"apollo_ids": [{"account": "TestAccount1", "apollo_id": ""}],
				}
			).insert(ignore_permissions=True, ignore_mandatory=True)
			self.lead_id = lead.name
		else:
			self.lead_id = lead_id

		if not frappe.db.exists("Email Template", "Test Template"):
			frappe.get_doc(
				{
					"doctype": "Email Template",
					"name": "Test Template",
					"subject": "Test Subject",
					"response": "Test Response",
				}
			).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	def _create_test_cadence(self):
		cadence = frappe.get_doc(
			{
				"doctype": "Cadence",
				"cadence_name": frappe.generate_hash(length=10),
				"enabled": 1,
				"cadence_schedules": [
					{
						"reference_doctype": "Email Template",
						"reference_name": "Test Template",
						"send_after_days": 1,
					}
				],
				"users": [{"user": "test_sender@example.com"}],
			}
		).insert(ignore_permissions=True, ignore_mandatory=True)
		return cadence

	@patch("frappe_controller.utils.controller.wait_for_event")
	def test_provision_field_suspension_provider_disabled(self, mock_wait):
		frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 0)
		mock_wait.side_effect = SuspendJob("wait")

		with self.assertRaises(SuspendJob):
			provision_a_field("subject_1", "string", "TestAccount1")

		mock_wait.assert_called_once()

	@patch("frappe_controller.utils.controller.wait_for_event")
	def test_provision_field_suspension_account_unauthorized(self, mock_wait):
		frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 1)
		frappe.db.set_value("Apollo Account", "TestAccount1", "status", "Unauthorized")
		mock_wait.side_effect = SuspendJob("wait")

		with self.assertRaises(SuspendJob):
			provision_a_field("subject_1", "string", "TestAccount1")

		mock_wait.assert_called_once()

	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	def test_provision_field_creates_apollo_fields(self, mock_client_cls):
		frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 1)
		frappe.db.set_value("Apollo Account", "TestAccount2", "status", "Authorized")

		mock_client = mock_client_cls.return_value
		mock_client.create_custom_field.return_value = {"typed_custom_fields": [{"id": "custom_field_555"}]}
		mock_client.get_sequence.return_value = {"emailer_steps": []}

		provision_a_field("subject_1", "string", "TestAccount2")

		field_doc = frappe.get_doc("Apollo Field", "subject_1")
		self.assertTrue(
			any(
				r.account == "TestAccount2" and r.apollo_id == "custom_field_555"
				for r in field_doc.apollo_ids
			)
		)

	def test_mcc_draft_reassignment(self):
		cadence = self._create_test_cadence()
		cadence.append("apollo_ids", {"account": "TestAccount1", "sender": "test_sender@example.com"})
		cadence.append("apollo_ids", {"account": "TestAccount2", "sender": "test_sender@example.com"})
		cadence.save(ignore_permissions=True)

		mcc = frappe.get_doc(
			{
				"doctype": "Multi Channel Cadence",
				"provider": [{"cadence_provider": "Apollo"}],
				"sender": "test_sender@example.com",
				"recipient": self.lead_id,
				"cadence_name": cadence.name,
				"cadence": cadence.name,
				"status": "Draft",
			}
		)

		before_save(mcc)
		mcc.apollo_account = "TestAccount1"
		mcc.apollo_sequence_id = "seq_account_1"

		cadence.apollo_ids = [row for row in cadence.apollo_ids if row.account != "TestAccount1"]
		cadence.save(ignore_permissions=True)

		before_save(mcc)
		self.assertEqual(mcc.apollo_account, "TestAccount2")
		self.assertEqual(mcc.apollo_sequence_id, "seq_account_2")

	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event")
	def test_mcc_sequence_assignment(self, mock_mcc_wait, mock_client_cls):
		cadence = self._create_test_cadence()
		mcc = frappe.get_doc(
			{
				"doctype": "Multi Channel Cadence",
				"provider": [{"cadence_provider": "Apollo"}],
				"sender": "test_sender@example.com",
				"recipient": self.lead_id,
				"cadence_name": cadence.name,
				"cadence": cadence.name,
				"status": "Scheduled",
				"apollo_account": "TestAccount2",
				"apollo_sequence_id": "seq_account_2",
			}
		).insert(ignore_permissions=True, ignore_mandatory=True)

		lead = frappe.get_doc("CRM Lead", self.lead_id)
		if not lead.apollo_ids:
			lead.append("apollo_ids", {"account": "TestAccount2", "apollo_id": "apollo_contact_1"})
		else:
			found = False
			for row in lead.apollo_ids:
				if row.account == "TestAccount2":
					row.apollo_id = "apollo_contact_1"
					found = True
					break
			if not found:
				lead.append("apollo_ids", {"account": "TestAccount2", "apollo_id": "apollo_contact_1"})
		lead.flags.ignore_mandatory = True
		lead.save(ignore_permissions=True)

		frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 1)
		frappe.db.set_value("Apollo Account", "TestAccount2", "status", "Authorized")

		mock_client = mock_client_cls.return_value
		add_contact_to_sequence(mcc.name)
		mock_client.add_contacts_to_sequence.assert_called_once_with(
			"apollo_contact_1", "seq_account_2", "mailbox_1"
		)

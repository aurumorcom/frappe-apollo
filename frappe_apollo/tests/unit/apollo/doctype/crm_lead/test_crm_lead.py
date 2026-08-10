from unittest.mock import MagicMock, call, patch

import frappe
from frappe.tests import UnitTestCase
from frappe_controller.utils.controller import SuspendJob

from frappe_apollo.apollo.doctype.crm_lead.crm_lead import (
	_create_a_contact,
	create_a_contact,
	update_a_contact,
)


class TestCRMLead(UnitTestCase):
	@patch("frappe.get_doc")
	@patch("frappe.db.count")
	@patch("frappe_controller.utils.controller.wait_for_event")
	def test_create_a_contact_suspends_for_missing_communications(self, mock_wait, mock_count, mock_get_doc):
		mcc = MagicMock()
		mcc.name = "mcc1"
		mcc.status = "Scheduled"
		mcc.sender = "sender"
		mcc.recipient = "lead1"
		mcc.cadence = "cad1"

		cadence = MagicMock()
		cadence.get.return_value = [{"reference_doctype": "Email Template"}]  # 1 expected comm

		mock_get_doc.side_effect = lambda dt, name: mcc if dt == "Multi Channel Cadence" else cadence
		mock_count.return_value = 0  # 0 actual comms

		mock_wait.side_effect = SuspendJob("wait")

		with self.assertRaises(SuspendJob):
			_create_a_contact("mcc1")

		mock_wait.assert_called_once()

	@patch("frappe.get_doc")
	@patch("frappe.db.count")
	@patch("frappe.db.get_value")
	@patch("frappe.enqueue")
	@patch("frappe_controller.utils.controller.wait_for_event")
	def test_create_a_contact_enqueues_create_if_no_apollo_id(
		self, mock_wait, mock_enqueue, mock_get_value, mock_count, mock_get_doc
	):
		mcc = MagicMock()
		mcc.name = "mcc1"
		mcc.status = "Scheduled"
		mcc.sender = "sender"
		mcc.recipient = "lead1"
		mcc.cadence = "cad1"
		mcc.apollo_account = "Acc1"

		cadence = MagicMock()
		cadence.get.return_value = [{"reference_doctype": "Email Template"}]  # 1 expected comm

		email_acc = MagicMock()
		email_acc_row = MagicMock(account="Acc1")
		email_acc.apollo_ids = [email_acc_row]

		lead = MagicMock()
		lead.get.return_value = [MagicMock(account="Acc1", apollo_id=None)]

		def get_doc_side_effect(dt, name):
			if dt == "Multi Channel Cadence":
				return mcc
			if dt == "Cadence":
				return cadence
			if dt == "Email Account":
				return email_acc
			if dt == "Apollo Account":
				return MagicMock(status="Authorized")
			if dt == "CRM Lead":
				return lead
			return MagicMock()

		mock_get_doc.side_effect = get_doc_side_effect
		mock_count.return_value = 1

		def get_value_side_effect(dt, *args):
			if dt == "Cadence Provider":
				return 1
			if dt == "User Email":
				return "EmailAccount1"
			return None

		mock_get_value.side_effect = get_value_side_effect

		mock_wait.side_effect = SuspendJob("wait")

		with self.assertRaises(SuspendJob):
			_create_a_contact("mcc1")

		mock_enqueue.assert_called_once_with(
			method="frappe_apollo.apollo.doctype.crm_lead.crm_lead.create_a_contact",
			queue="low",
			lead_name="lead1",
			account_name="Acc1",
		)
		mock_wait.assert_called_once()
		# Verify condition string safely inspects child table dicts
		condition_arg = mock_wait.call_args[1].get("condition") or mock_wait.call_args[0][1]
		self.assertIn("row.get('account')", condition_arg)
		self.assertNotIn("argument.get('apollo_id')", condition_arg)

	@patch("frappe.get_doc")
	@patch("frappe.db.count")
	@patch("frappe.db.get_value")
	@patch("frappe.enqueue")
	def test_create_a_contact_enqueues_update_if_apollo_id_exists(
		self, mock_enqueue, mock_get_value, mock_count, mock_get_doc
	):
		mcc = MagicMock()
		mcc.name = "mcc1"
		mcc.status = "Scheduled"
		mcc.sender = "sender"
		mcc.recipient = "lead1"
		mcc.cadence = "cad1"
		mcc.apollo_account = "Acc1"

		cadence = MagicMock()
		cadence.get.return_value = [{"reference_doctype": "Email Template"}]

		email_acc = MagicMock()
		email_acc.apollo_ids = [MagicMock(account="Acc1")]

		lead = MagicMock()
		lead.get.return_value = [MagicMock(account="Acc1", apollo_id="contact123")]

		def get_doc_side_effect(dt, name):
			if dt == "Multi Channel Cadence":
				return mcc
			if dt == "Cadence":
				return cadence
			if dt == "Email Account":
				return email_acc
			if dt == "Apollo Account":
				return MagicMock(status="Authorized")
			if dt == "CRM Lead":
				return lead
			return MagicMock()

		mock_get_doc.side_effect = get_doc_side_effect
		mock_count.return_value = 1

		def get_value_side_effect(dt, *args):
			if dt == "Cadence Provider":
				return 1
			if dt == "User Email":
				return "EmailAccount1"
			return None

		mock_get_value.side_effect = get_value_side_effect

		_create_a_contact("mcc1")

		mock_enqueue.assert_called_once_with(
			method="frappe_apollo.apollo.doctype.crm_lead.crm_lead.update_a_contact",
			queue="low",
			lead_name="lead1",
			account_name="Acc1",
		)

	@patch("frappe.get_doc")
	@patch("frappe.db.get_value")
	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	def test_update_a_contact(self, mock_client_cls, mock_get_value, mock_get_doc):
		mock_get_value.side_effect = lambda dt, name, *args: 1 if dt == "Cadence Provider" else "Authorized"

		lead = MagicMock()
		lead.first_name = "John"
		lead.last_name = "Doe"
		lead.email = "john@example.com"
		lead.organization = "Acme"
		lead.get.return_value = [MagicMock(account="Acc1", apollo_id="contact123")]

		mock_get_doc.return_value = lead

		mock_client = mock_client_cls.return_value

		update_a_contact("lead1", "Acc1")

		mock_client.update_contact.assert_called_once_with(
			"contact123",
			{
				"first_name": "John",
				"last_name": "Doe",
				"email": "john@example.com",
				"organization_name": "Acme",
			},
		)

	@patch("frappe.get_doc")
	@patch("frappe.db.count")
	@patch("frappe.db.get_value")
	@patch("frappe.enqueue")
	@patch("frappe_controller.utils.controller.wait_for_event")
	def test_create_a_contact_refetches_email_account_name_after_resumption(
		self, mock_wait, mock_enqueue, mock_get_value, mock_count, mock_get_doc
	):
		mcc = MagicMock()
		mcc.name = "mcc1"
		mcc.status = "Scheduled"
		mcc.sender = "sender1"
		mcc.recipient = "lead1"
		mcc.cadence_name = "cad1"
		mcc.apollo_account = "Acc2"

		cadence = MagicMock()
		cadence.get.return_value = [{"reference_doctype": "Email Template"}]

		email_acc = MagicMock()
		email_acc.apollo_ids = [MagicMock(account="Acc1"), MagicMock(account="Acc2")]

		lead = MagicMock()
		lead.get.return_value = [MagicMock(account="Acc2", apollo_id=None)]

		mock_get_doc.side_effect = lambda dt, name: (
			mcc
			if dt == "Multi Channel Cadence"
			else (cadence if dt == "Cadence" else (email_acc if dt == "Email Account" else lead))
		)
		mock_count.return_value = 1

		user_email_calls = []

		def get_value_side_effect(dt, name_or_filters=None, *args):
			if dt == "User Email":
				user_email_calls.append(1)
				return "EmailAcc1" if len(user_email_calls) > 1 else None
			if dt == "Cadence Provider":
				return 1
			if dt == "Apollo Account":
				return "Authorized"
			return None

		mock_get_value.side_effect = get_value_side_effect

		def wait_side_effect(*args, **kwargs):
			return None  # Simulate resumption

		mock_wait.side_effect = wait_side_effect

		_create_a_contact("mcc1")

		# Verify User Email was queried again after wait
		user_email_calls = [c for c in mock_get_value.call_args_list if c[0][0] == "User Email"]
		self.assertGreaterEqual(
			len(user_email_calls), 2, "email_account_name was not re-fetched after resumption"
		)

	@patch("frappe.get_doc")
	@patch("frappe.db.get_value")
	@patch("frappe_controller.utils.controller.wait_for_event")
	def test_create_a_contact_registers_event_listener_when_account_unauthorized(
		self, mock_wait, mock_get_value, mock_get_doc
	):
		def get_value_side_effect(dt, name_or_filters=None, *args):
			if dt == "Cadence Provider":
				return 1
			if dt == "Apollo Account":
				return "Unauthorized"
			return None

		mock_get_value.side_effect = get_value_side_effect
		mock_wait.side_effect = SuspendJob("suspend")

		with self.assertRaises(SuspendJob):
			create_a_contact("lead1", "Acc_Unauthorized")

		mock_wait.assert_called_once_with(
			event_key="doc:Apollo Account:Acc_Unauthorized:on_update",
			condition="argument.get('status') == 'Authorized'",
		)

	@patch("frappe.get_doc")
	@patch("frappe.db.get_value")
	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	def test_create_a_contact_extracts_id_from_dict_response(
		self, mock_client_cls, mock_get_value, mock_get_doc
	):
		mock_get_value.side_effect = lambda dt, name, *args: 1 if dt == "Cadence Provider" else "Authorized"

		lead = MagicMock()
		lead.first_name = "Sanky"
		lead.last_name = ""
		lead.email = "sanky@example.com"
		lead.organization = "Acme"
		row = MagicMock(account="Acc1", apollo_id="")
		lead.get.return_value = [row]

		mock_get_doc.return_value = lead
		mock_client = mock_client_cls.return_value
		mock_client.create_contact.return_value = {
			"contact": {"id": "contact_dict_6a791162", "first_name": "Sanky"},
			"labels": [],
		}

		create_a_contact("lead1", "Acc1")

		self.assertEqual(row.apollo_id, "contact_dict_6a791162")
		lead.save.assert_called_once_with(ignore_permissions=True)

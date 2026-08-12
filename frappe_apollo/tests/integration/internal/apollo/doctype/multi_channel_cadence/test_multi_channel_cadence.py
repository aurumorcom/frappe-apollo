from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from frappe_apollo.apollo.doctype.crm_lead.crm_lead import _create_a_contact
from frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence import (
	add_contact_to_sequence,
)


class TestMCCIntegration(IntegrationTestCase):
	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	@patch(
		"frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event",
		side_effect=SuspendJob("wait"),
	)
	@patch("frappe.db.get_value")
	@patch("frappe.get_doc")
	@patch("frappe.get_all")
	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	def test_sequence_inactive_raises_wait(
		self, mock_client_class, mock_get_all, mock_get_doc, mock_get_value, mock_wait
	):
		from frappe.database.database import Database

		real_get_value = Database.get_value

		def mock_get_value_side_effect(*args, **kwargs):
			dt = args[0] if args else kwargs.get("doctype")
			if dt == "DocType":
				return real_get_value(frappe.db, *args, **kwargs)
			if dt == "Cadence Provider":
				return 1
			if dt == "User Email":
				return "Email-Acc-1"
			if dt == "Apollo Account":
				return None  # apollo_sequence_id is None
			return "val"

		mock_get_value.side_effect = mock_get_value_side_effect

		mock_mcc = MagicMock()
		mock_mcc.name = "mcc1"
		mock_mcc.sender = "user1"
		mock_mcc.recipient = "lead1"
		mock_mcc.cadence = "cad1"
		mock_mcc.status = "Scheduled"
		mock_mcc.apollo_account = "acc1"
		mock_mcc.apollo_sequence_id = None

		mock_email_account = MagicMock()
		mock_acc = MagicMock(account="acc1", apollo_id="mb_apollo_1")
		mock_email_account.apollo_ids = [mock_acc]
		mock_email_account.get.return_value = [mock_acc]

		mock_account = MagicMock(status="Authorized")

		def mock_get_doc_side_effect(*args, **kwargs):
			doctype = (
				args[0]
				if args and isinstance(args[0], str)
				else (args[0].get("doctype") if args else kwargs.get("doctype"))
			)
			if doctype == "Multi Channel Cadence":
				return mock_mcc
			if doctype == "Email Account":
				return mock_email_account
			if doctype == "Apollo Account":
				return mock_account
			return MagicMock()

		mock_get_doc.side_effect = mock_get_doc_side_effect
		mock_get_all.side_effect = lambda *args, **kwargs: (
			[frappe._dict({"apollo_id": "pid1"})] if args[0] == "CRM Lead Apollo ID" else []
		)

		with self.assertRaises(SuspendJob):
			add_contact_to_sequence("mcc1")

	@patch(
		"frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event",
		side_effect=SuspendJob("wait"),
	)
	@patch("frappe.db.get_value")
	@patch("frappe.get_doc")
	@patch("frappe.get_all")
	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe.enqueue")
	def test_valid_sync(
		self, mock_enqueue, mock_client_class, mock_get_all, mock_get_doc, mock_get_value, mock_wait
	):
		from frappe.database.database import Database

		real_get_value = Database.get_value

		def mock_get_value_side_effect(*args, **kwargs):
			dt = args[0] if args else kwargs.get("doctype")
			if dt == "DocType":
				return real_get_value(frappe.db, *args, **kwargs)
			if dt == "Cadence Provider":
				return 1
			if dt == "User Email":
				return "Email-Acc-1"
			return "val"

		mock_get_value.side_effect = mock_get_value_side_effect

		mock_mcc = MagicMock()
		mock_mcc.name = "mcc1"
		mock_mcc.sender = "user1"
		mock_mcc.recipient = "lead1"
		mock_mcc.cadence_name = "cad1"
		mock_mcc.status = "Scheduled"
		mock_mcc.apollo_account = "acc1"
		mock_mcc.apollo_sequence_id = "seq1"

		mock_email_account = MagicMock()
		mock_acc = MagicMock(account="acc1", apollo_id="mb_apollo_1")
		mock_email_account.apollo_ids = [mock_acc]
		mock_email_account.get.return_value = [mock_acc]

		mock_account = MagicMock(status="Authorized")

		mock_lead = MagicMock()
		mock_lead_acc = MagicMock(account="acc1", apollo_id="pid1")
		mock_lead.get.return_value = [mock_lead_acc]

		def mock_get_doc_side_effect(*args, **kwargs):
			doctype = (
				args[0]
				if args and isinstance(args[0], str)
				else (args[0].get("doctype") if args else kwargs.get("doctype"))
			)
			if doctype == "Multi Channel Cadence":
				return mock_mcc
			if doctype == "Cadence":
				mock_cadence = MagicMock()
				mock_cadence.get.side_effect = lambda k, d=[]: [] if k == "cadence_schedules" else d
				return mock_cadence
			if doctype == "Email Account":
				return mock_email_account
			if doctype == "Apollo Account":
				return mock_account
			if doctype == "CRM Lead":
				return mock_lead
			return MagicMock()

		mock_get_doc.side_effect = mock_get_doc_side_effect
		mock_get_all.side_effect = lambda *args, **kwargs: (
			[frappe._dict({"apollo_id": "pid1"})] if args[0] == "CRM Lead Apollo ID" else []
		)

		mock_client = MagicMock()
		mock_client_class.return_value = mock_client

		_create_a_contact("mcc1")
		add_contact_to_sequence("mcc1")

		mock_client.add_contacts_to_sequence.assert_called_once_with(
			"pid1", "seq1", "mb_apollo_1", email_address=mock_email_account.email_id
		)

	@patch("frappe.get_doc")
	def test_wait_condition_evaluation_with_single_quote_account_name(self, mock_get_doc):
		from frappe.model.document import get_doc as real_get_doc

		job_id = "test_job_single_quote_1"
		if frappe.db.table_exists("FS Job"):
			frappe.db.sql(
				"INSERT IGNORE INTO `tabFS Job` (name, job_name, status, queue, creation, modified, modified_by, owner) VALUES (%s, %s, %s, %s, NOW(), NOW(), 'Administrator', 'Administrator')",
				(job_id, "test_job_single_quote_func", "started", "high"),
			)
			frappe.db.commit()

		frappe.flags.current_job_id = job_id
		account_name = "Abhishek's Apollo"
		mcc = MagicMock()
		mcc.status = "Scheduled"
		mcc.sender = "user1"
		mcc.apollo_account = account_name
		mcc.apollo_sequence_id = "seq1"
		mcc.cadence_name = None

		email_account = MagicMock()
		email_account.get.return_value = []  # Missing apollo_ids, forcing wait_for_event

		real_db_get_value = frappe.db.get_value

		def mock_get_value_side_effect(*args, **kwargs):
			dt = args[0] if args else kwargs.get("doctype")
			if dt == "Cadence Provider":
				return 1
			if dt == "User Email":
				return "Email-Acc-1"
			if dt == "Apollo Account":
				fieldname = kwargs.get("fieldname") or (args[1] if len(args) > 1 and isinstance(args[1], str) else None)
				if fieldname == "status":
					return "Authorized"
				if fieldname == "apollo_sequence_id":
					return "seq1"
			return real_db_get_value(*args, **kwargs)

		def mock_get_doc_side_effect(*args, **kwargs):
			doctype = (
				args[0]
				if args and isinstance(args[0], str)
				else (args[0].get("doctype") if args and isinstance(args[0], dict) else kwargs.get("doctype"))
			)
			if doctype == "Multi Channel Cadence":
				return mcc
			if doctype == "Email Account":
				return email_account
			return real_get_doc(*args, **kwargs)

		mock_get_doc.side_effect = mock_get_doc_side_effect
		patcher = patch("frappe.db.get_value", side_effect=mock_get_value_side_effect)
		patcher.start()
		self.addCleanup(patcher.stop)

		with self.assertRaises(SuspendJob):
			add_contact_to_sequence("mcc1")

		# Retrieve inserted FS Match Condition
		match_cond = frappe.db.get_value(
			"FS Match Condition", {"job": frappe.flags.current_job_id}, ["condition"], as_dict=True
		)
		self.assertIsNotNone(match_cond)
		condition_str = match_cond.condition

		# Simulate event argument payload from Email Account save event
		event_argument = {"apollo_ids": [{"account": account_name, "apollo_id": "mb_123"}]}

		# Evaluate condition via frappe.safe_eval
		result = frappe.safe_eval(condition_str, None, {"argument": event_argument})
		self.assertTrue(bool(result))

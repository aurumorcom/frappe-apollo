from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase
from frappe_controller.utils.controller import SuspendJob

from frappe_apollo.apollo.doctype.cadence.cadence import (
	_create_fields,
	_update_sequence,
	_validate_for_sequence,
	on_update,
	toggle_cadence_mccs,
	update_sequence_steps,
)


class TestCadenceProvisioning(UnitTestCase):
	@patch("frappe_apollo.apollo.doctype.cadence.cadence.enqueue")
	@patch("frappe_apollo.apollo.doctype.cadence.cadence._check_account_requires_update")
	@patch("frappe_apollo.apollo.doctype.cadence.cadence._ensure_local_apollo_fields")
	def test_on_update_ensures_local_fields_and_enqueues_update_sequence_steps(
		self, mock_ensure_fields, mock_check_update, mock_enqueue
	):
		doc = MagicMock()
		doc.name = "Test Cadence"
		doc.has_value_changed.return_value = False

		row1 = {"account": "Acc1"}
		row2 = {"account": "Acc2"}
		doc.get.side_effect = lambda k, default=[]: [row1, row2] if k == "apollo_ids" else default

		mock_ensure_fields.return_value = [("subject_1", "string", {})]
		mock_check_update.side_effect = lambda doc_obj, acc, labels: acc == "Acc1"

		on_update(doc)

		mock_ensure_fields.assert_called_once_with(doc)
		mock_enqueue.assert_called_once_with(
			"frappe_apollo.apollo.doctype.cadence.cadence.update_sequence_steps",
			queue="low",
			cadence_name="Test Cadence",
			account_name="Acc1",
		)

	@patch("frappe_apollo.apollo.doctype.cadence.cadence.enqueue")
	@patch("frappe_apollo.apollo.doctype.cadence.cadence._check_account_requires_update")
	@patch("frappe_apollo.apollo.doctype.cadence.cadence._ensure_local_apollo_fields")
	def test_on_update_disabling_enqueues_toggle_mccs(
		self, mock_ensure_fields, mock_check_update, mock_enqueue
	):
		doc = MagicMock()
		doc.name = "Test Cadence"
		doc.enabled = 0
		doc.has_value_changed.side_effect = lambda k: True if k == "enabled" else False
		doc.get.return_value = []
		mock_ensure_fields.return_value = []

		on_update(doc)

		mock_enqueue.assert_called_once_with(
			"frappe_apollo.apollo.doctype.cadence.cadence.toggle_cadence_mccs",
			queue="low",
			cadence_name="Test Cadence",
		)

	@patch("frappe_apollo.apollo.doctype.cadence.cadence.wait_for_event")
	@patch("frappe.db.get_value")
	def test_update_sequence_steps_suspends_when_provider_disabled(self, mock_db_get_value, mock_wait):
		def db_get_value_side_effect(dt, *args, **kwargs):
			if dt == "Cadence Provider":
				return 0
			return "Authorized"

		mock_db_get_value.side_effect = db_get_value_side_effect
		mock_wait.side_effect = SuspendJob("Provider disabled")

		with self.assertRaises(SuspendJob):
			update_sequence_steps("Cadence-1", "Acc1")

		mock_wait.assert_called_once_with(
			event_key="doc:Cadence Provider:Apollo:on_update",
			condition="argument.get('enabled') == 1",
		)

	@patch("frappe_apollo.apollo.doctype.cadence.cadence.wait_for_event")
	@patch("frappe.db.get_value")
	def test_update_sequence_steps_suspends_when_account_unauthorized(self, mock_db_get_value, mock_wait):
		def db_get_value_side_effect(dt, *args, **kwargs):
			if dt == "Cadence Provider":
				return 1
			if dt == "Apollo Account":
				return "Unauthorized"
			return None

		mock_db_get_value.side_effect = db_get_value_side_effect
		mock_wait.side_effect = SuspendJob("Account unauthorized")

		with self.assertRaises(SuspendJob):
			update_sequence_steps("Cadence-1", "Acc1")

		mock_wait.assert_called_once_with(
			event_key="doc:Apollo Account:Acc1:on_update",
			condition="argument.get('status') == 'Authorized'",
		)

	@patch("frappe_apollo.apollo.doctype.cadence.cadence._update_sequence")
	@patch("frappe_apollo.apollo.doctype.cadence.cadence._create_fields")
	@patch("frappe_apollo.apollo.doctype.cadence.cadence.ApolloClient")
	@patch("frappe.get_doc")
	@patch("frappe.db.get_value")
	def test_update_sequence_steps_executes_create_fields_and_update_sequence(
		self, mock_db_get_value, mock_get_doc, mock_client_cls, mock_create_fields, mock_update_seq
	):
		def db_get_value_side_effect(dt, *args, **kwargs):
			if dt == "Cadence Provider":
				return 1
			if dt == "Apollo Account":
				fieldname = kwargs.get("fieldname") or (args[1] if len(args) > 1 else None)
				if fieldname == "status":
					return "Authorized"
				if fieldname == "apollo_sequence_id":
					return "seq_999"
			return None

		mock_db_get_value.side_effect = db_get_value_side_effect
		mock_cadence = MagicMock()
		mock_get_doc.return_value = mock_cadence

		update_sequence_steps("Cadence-1", "Acc1")

		mock_create_fields.assert_called_once_with(mock_client_cls.return_value, mock_cadence, "Acc1")
		mock_update_seq.assert_called_once_with(mock_client_cls.return_value, "seq_999", mock_cadence)

	@patch("frappe_apollo.apollo.doctype.cadence.cadence._get_supported_channels")
	def test_update_sequence_maps_zero_days_delay_immediately(self, mock_get_channels):
		mock_get_channels.return_value = ["Email"]
		mock_client = MagicMock()
		mock_client.get_sequence.return_value = {"emailer_steps": []}

		sch = {"channel": "Email", "reference_doctype": "Email Template", "send_after_days": 0}
		cadence_doc = MagicMock()
		cadence_doc.get.return_value = [sch]

		_update_sequence(mock_client, "seq_123", cadence_doc)

		mock_client.update_sequence.assert_called_once()
		pos_args, _ = mock_client.update_sequence.call_args
		steps = pos_args[1]["emailer_steps"]
		self.assertEqual(len(steps), 1)
		self.assertEqual(steps[0]["wait_time"], 0)
		self.assertEqual(steps[0]["wait_mode"], "second")

	@patch("frappe_apollo.apollo.doctype.cadence.cadence._get_supported_channels")
	def test_update_sequence_maps_positive_days_delay(self, mock_get_channels):
		mock_get_channels.return_value = ["Email"]
		mock_client = MagicMock()
		mock_client.get_sequence.return_value = {"emailer_steps": []}

		sch = {"channel": "Email", "reference_doctype": "Email Template", "send_after_days": 3}
		cadence_doc = MagicMock()
		cadence_doc.get.return_value = [sch]

		_update_sequence(mock_client, "seq_123", cadence_doc)

		mock_client.update_sequence.assert_called_once()
		pos_args, _ = mock_client.update_sequence.call_args
		steps = pos_args[1]["emailer_steps"]
		self.assertEqual(len(steps), 1)
		self.assertEqual(steps[0]["wait_time"], 3)
		self.assertEqual(steps[0]["wait_mode"], "day")

	@patch("frappe.msgprint")
	@patch("frappe.db.get_value")
	@patch("frappe_apollo.apollo.doctype.cadence.cadence.ApolloClient")
	def test_validate_for_sequence_mismatch_disables_cadence(
		self, mock_client_cls, mock_db_get_value, mock_msgprint
	):
		doc = MagicMock()
		doc.name = "Test Cadence"

		sch1 = MagicMock(channel="Email", reference_doctype="Email Template")
		sch2 = MagicMock(channel="Email", reference_doctype="Email Template")
		doc.get.side_effect = lambda k, d=[]: [sch1, sch2] if k == "cadence_schedules" else d

		mock_db_get_value.return_value = "seq_123"

		mock_client = mock_client_cls.return_value
		mock_client.get_sequence.return_value = {"emailer_steps": [{"id": 1}]}

		_validate_for_sequence(doc, "Acc1")

		mock_msgprint.assert_called_once()
		self.assertEqual(doc.enabled, 0)

	@patch("frappe.get_doc")
	@patch("frappe.get_all")
	def test_toggle_cadence_mccs_disabling(self, mock_get_all, mock_get_doc):
		mock_cadence = MagicMock(enabled=0)
		mock_mcc = MagicMock(status="In Progress", last_status=None)
		mock_get_doc.side_effect = lambda dt, name: mock_cadence if dt == "Cadence" else mock_mcc
		mock_get_all.return_value = [{"name": "MCC-1"}]

		toggle_cadence_mccs("Cadence-1")

		self.assertEqual(mock_mcc.last_status, "In Progress")
		self.assertEqual(mock_mcc.status, "Disabled")
		mock_mcc.save.assert_called_once_with(ignore_permissions=True)

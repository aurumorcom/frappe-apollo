from unittest.mock import MagicMock, call, patch

import frappe
from frappe.tests import UnitTestCase

from frappe_apollo.apollo.doctype.cadence.cadence import (
	_validate_for_sequence,
	on_update,
	toggle_cadence_mccs,
)


class TestCadenceProvisioning(UnitTestCase):
	@patch("frappe_apollo.apollo.doctype.cadence.cadence._validate_for_sequence")
	@patch("frappe.get_attr")
	def test_on_update_validates_and_enqueues_fields(self, mock_get_attr, mock_validate):
		doc = MagicMock()
		doc.name = "Test Cadence"
		doc.has_value_changed.return_value = False

		row1 = MagicMock(account="Acc1")
		row1.get.side_effect = lambda k: "Sender1" if k == "sender" else None
		row2 = MagicMock(account="Acc2")
		row2.get.side_effect = lambda k: "Sender2" if k == "sender" else None
		doc.get.return_value = [row1, row2]

		mock_enqueue_field = MagicMock()
		mock_get_attr.return_value = mock_enqueue_field

		on_update(doc)

		mock_validate.assert_has_calls([
			call(doc, "Acc1"),
			call(doc, "Acc2")
		])

		mock_enqueue_field.assert_has_calls([
			call("Test Cadence", "Acc1", "Sender1"),
			call("Test Cadence", "Acc2", "Sender2")
		])

	@patch("frappe_apollo.apollo.doctype.cadence.cadence.enqueue")
	@patch("frappe_apollo.apollo.doctype.cadence.cadence._validate_for_sequence")
	@patch("frappe.get_attr")
	def test_on_update_disabling_enqueues_toggle_mccs(self, mock_get_attr, mock_validate, mock_enqueue):
		doc = MagicMock()
		doc.name = "Test Cadence"
		doc.enabled = 0
		doc.has_value_changed.side_effect = lambda k: True if k == "enabled" else False
		doc.get.return_value = []

		on_update(doc)

		mock_enqueue.assert_called_once_with(
			"frappe_apollo.apollo.doctype.cadence.cadence.toggle_cadence_mccs",
			queue="low",
			cadence_name="Test Cadence"
		)

	@patch("frappe.msgprint")
	@patch("frappe.db.get_value")
	@patch("frappe_apollo.apollo.doctype.cadence.cadence.ApolloClient")
	def test_validate_for_sequence_mismatch_disables_cadence(self, mock_client_cls, mock_db_get_value, mock_msgprint):
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

	@patch("frappe.msgprint")
	@patch("frappe_apollo.apollo.doctype.cadence.cadence.ApolloClient")
	def test_validate_for_sequence_zero_steps_returns_early(self, mock_client_cls, mock_msgprint):
		doc = MagicMock()
		doc.get.side_effect = lambda k, d=[]: [] if k == "cadence_schedules" else d

		_validate_for_sequence(doc, "Acc1")

		mock_msgprint.assert_not_called()
		mock_client_cls.assert_not_called()

	@patch("frappe.msgprint")
	@patch("frappe.db.get_value")
	def test_validate_for_sequence_missing_sequence_id_disables(self, mock_db_get_value, mock_msgprint):
		doc = MagicMock()
		sch1 = MagicMock(channel="Email", reference_doctype="Email Template")
		doc.get.side_effect = lambda k, d=[]: [sch1] if k == "cadence_schedules" else d

		mock_db_get_value.return_value = None

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

	@patch("frappe.get_doc")
	@patch("frappe.get_all")
	def test_toggle_cadence_mccs_enabling(self, mock_get_all, mock_get_doc):
		mock_cadence = MagicMock(enabled=1)
		mock_mcc = MagicMock(status="Disabled", last_status="In Progress")
		mock_get_doc.side_effect = lambda dt, name: mock_cadence if dt == "Cadence" else mock_mcc
		mock_get_all.return_value = [{"name": "MCC-1"}]

		toggle_cadence_mccs("Cadence-1")

		self.assertEqual(mock_mcc.status, "In Progress")
		self.assertIsNone(mock_mcc.last_status)
		mock_mcc.save.assert_called_once_with(ignore_permissions=True)

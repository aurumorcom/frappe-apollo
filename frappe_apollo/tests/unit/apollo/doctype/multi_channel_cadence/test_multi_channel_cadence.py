from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase
from frappe_controller.utils.controller import SuspendJob

from frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence import (
	_assign_contact_to_sequence,
	_stop_contact_in_sequence,
	before_save,
	on_update,
)


class TestMultiChannelCadence(UnitTestCase):
	@patch("frappe.db.get_value")
	@patch("frappe.get_doc")
	@patch("frappe.get_all")
	def test_before_save_pulls_sequence_id_from_apollo_account(self, mock_get_all, mock_get_doc, mock_db_get_value):
		mcc = MagicMock()
		mcc.get.side_effect = lambda k, d=[]: [MagicMock(cadence_provider="Apollo")] if k == "provider" else d
		mcc.sender = "user@example.com"
		mcc.apollo_account = None
		mcc.apollo_sequence_id = None
		mcc.cadence_name = "Cad1"
		mcc.status = "Draft"

		mock_cadence = MagicMock()
		mock_mapping = MagicMock(sender="user@example.com", status="Active", account="Acc1", name="row1")
		mock_cadence.get.return_value = [mock_mapping]

		mock_get_doc.return_value = mock_cadence
		mock_get_all.return_value = []
		mock_db_get_value.return_value = "seq_acc_123"

		before_save(mcc)

		self.assertEqual(mcc.apollo_account, "Acc1")
		self.assertEqual(mcc.apollo_sequence_id, "seq_acc_123")

	@patch("frappe.get_doc")
	@patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event")
	def test_assign_contact_fail_fast_wrong_status(self, mock_wait, mock_get_doc):
		mcc = MagicMock()
		mcc.status = "Cancelled"
		mock_get_doc.return_value = mcc

		_assign_contact_to_sequence("mcc1")

		mock_wait.assert_not_called()

	@patch("frappe.get_doc")
	@patch("frappe.db.get_value")
	@patch("frappe.get_all")
	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event")
	def test_assign_contact_waits_for_account_sequence_id(self, mock_wait, mock_client_cls, mock_get_all, mock_get_value, mock_get_doc):
		mcc = MagicMock()
		mcc.status = "Scheduled"
		mcc.apollo_account = "Acc1"
		mcc.apollo_sequence_id = None

		mock_get_doc.return_value = mcc
		mock_get_value.side_effect = lambda dt, *args: 1 if dt == "Cadence Provider" else None
		mock_wait.side_effect = SuspendJob("wait_for_seq")

		with self.assertRaises(SuspendJob):
			_assign_contact_to_sequence("mcc1")

		mock_wait.assert_called_once_with(
			event_key="doc:Apollo Account:Acc1:on_update",
			condition="argument.get('apollo_sequence_id')"
		)

	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe.get_all")
	@patch("frappe.get_doc")
	def test_stop_contact_in_sequence(self, mock_get_doc, mock_get_all, mock_client_cls):
		mcc = MagicMock()
		mcc.apollo_account = "Acc1"
		mcc.apollo_sequence_id = "seq1"
		mcc.recipient = "Lead1"
		mock_get_doc.return_value = mcc

		mock_get_all.return_value = [MagicMock(apollo_id="contact_123")]
		mock_client = mock_client_cls.return_value

		_stop_contact_in_sequence("mcc1", mode="stop")

		mock_client.update_contact_status_sequence.assert_called_once_with(
			"contact_123", "seq1", "stop"
		)

	@patch("frappe.enqueue")
	def test_on_update_enqueues_stop_contact_on_deactivation(self, mock_enqueue):
		doc = MagicMock()
		doc.name = "MCC-1"
		doc.status = "Disabled"
		before_doc = MagicMock(status="Active")
		doc.get_doc_before_save.return_value = before_doc

		on_update(doc)

		mock_enqueue.assert_called_once_with(
			method="frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence._stop_contact_in_sequence",
			queue="short",
			mcc_name="MCC-1",
			mode="stop"
		)

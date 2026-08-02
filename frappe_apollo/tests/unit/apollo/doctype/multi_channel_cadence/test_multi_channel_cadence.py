import frappe
from frappe.tests import UnitTestCase
from frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence import before_save, _assign_contact_to_sequence
from frappe_controller.utils.controller import SuspendJob
from unittest.mock import patch, MagicMock

class TestMultiChannelCadence(UnitTestCase):
    @patch("frappe.get_doc")
    @patch("frappe.get_all")
    def test_before_save_ignores_missing_apollo_id(self, mock_get_all, mock_get_doc):
        # MCC setup
        mcc = MagicMock()
        mcc.get.side_effect = lambda k, d=[]: [MagicMock(cadence_provider="Apollo")] if k == "provider" else d
        mcc.sender = "user@example.com"
        mcc.apollo_account = None
        mcc.apollo_sequence_id = None
        mcc.cadence_name = "Cad1"
        mcc.status = "Draft"
        
        # Cadence setup
        mock_cadence = MagicMock()
        mock_mapping_active_no_id = MagicMock(sender="user@example.com", status="Active", apollo_id=None)
        mock_mapping_active_with_id = MagicMock(sender="user@example.com", status="Active", apollo_id="seq123", account="Acc1", name="row1")
        mock_cadence.get.return_value = [mock_mapping_active_no_id, mock_mapping_active_with_id]
        
        mock_get_doc.return_value = mock_cadence
        mock_get_all.return_value = [] # No other MCCs
        
        before_save(mcc)
        
        # Verify that it selected the mapping with the apollo_id, ignoring the one without
        self.assertEqual(mcc.apollo_account, "Acc1")
        self.assertEqual(mcc.apollo_sequence_id, "seq123")

    @patch("frappe.get_doc")
    @patch("frappe.get_all")
    def test_before_save_reassigns_if_draft_and_invalid(self, mock_get_all, mock_get_doc):
        # MCC setup
        mcc = MagicMock()
        mcc.get.side_effect = lambda k, d=[]: [MagicMock(cadence_provider="Apollo")] if k == "provider" else d
        mcc.sender = "user@example.com"
        mcc.apollo_account = "Acc_Old"
        mcc.apollo_sequence_id = "seq_old"
        mcc.cadence_name = "Cad1"
        mcc.status = "Draft"
        
        mock_cadence = MagicMock()
        mock_mapping = MagicMock(sender="user@example.com", status="Active", apollo_id="seq_new", account="Acc_New", name="row1")
        mock_cadence.get.return_value = [mock_mapping]
        
        mock_get_doc.return_value = mock_cadence
        mock_get_all.return_value = []
        
        before_save(mcc)
        
        self.assertEqual(mcc.apollo_account, "Acc_New")
        self.assertEqual(mcc.apollo_sequence_id, "seq_new")

    @patch("frappe.get_doc")
    @patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event")
    def test_assign_contact_fail_fast_wrong_status(self, mock_wait, mock_get_doc):
        mcc = MagicMock()
        mcc.status = "Cancelled"
        mock_get_doc.return_value = mcc
        
        _assign_contact_to_sequence("mcc1")
        
        # Should return immediately
        mock_wait.assert_not_called()

    @patch("frappe.get_doc")
    @patch("frappe.db.get_value")
    @patch("frappe.get_all")
    @patch("frappe_apollo.integrations.apollo.ApolloClient")
    @patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event")
    def test_assign_contact_suspends_and_revalidates(self, mock_wait, mock_client_cls, mock_get_all, mock_get_value, mock_get_doc):
        mcc = MagicMock()
        mcc.status = "Scheduled"
        mcc.apollo_account = None # trigger suspend
        mcc.apollo_sequence_id = None
        
        mock_get_doc.return_value = mcc
        
        # Make wait raise SuspendJob
        mock_wait.side_effect = SuspendJob("wait")
        
        with self.assertRaises(SuspendJob):
            _assign_contact_to_sequence("mcc1")
        
        mock_wait.assert_called_once()

    @patch("frappe.get_doc")
    @patch("frappe.db.get_value")
    @patch("frappe.get_all")
    @patch("frappe_apollo.integrations.apollo.ApolloClient")
    @patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event")
    def test_assign_contact_waits_when_email_account_unmapped(self, mock_wait, mock_client_cls, mock_get_all, mock_get_value, mock_get_doc):
        mcc = MagicMock()
        mcc.status = "Scheduled"
        mcc.apollo_account = "Acc1"
        mcc.apollo_sequence_id = "seq1"
        mcc.sender = "sender1"

        email_acc = MagicMock()
        email_acc.name = "EmailAcc1"
        email_acc.get.return_value = [] # Empty apollo_ids initially

        mock_get_doc.side_effect = lambda dt, name: mcc if dt == "Multi Channel Cadence" else email_acc
        mock_get_value.side_effect = lambda dt, *args: 1 if dt == "Cadence Provider" else "EmailAcc1"

        mock_wait.side_effect = SuspendJob("wait_for_mailbox")

        with self.assertRaises(SuspendJob):
            _assign_contact_to_sequence("mcc1")

        mock_wait.assert_called_once_with(
            event_key="doc:Email Account:EmailAcc1:on_update",
            condition="any(row.get('account') == 'Acc1' and row.get('apollo_id') for row in argument.get('apollo_ids', []))"
        )

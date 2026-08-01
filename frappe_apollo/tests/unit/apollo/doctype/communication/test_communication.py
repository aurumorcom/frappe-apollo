import frappe
from frappe.tests import UnitTestCase
from frappe_apollo.apollo.doctype.communication.communication import update_a_contact, on_update
from unittest.mock import patch, MagicMock

class TestCommunicationOverride(UnitTestCase):

    @patch("frappe.enqueue")
    def test_on_update_enqueues_when_status_changes_to_scheduled(self, mock_enqueue):
        mock_doc = MagicMock()
        mock_doc_before = MagicMock()
        mock_doc_before.status = "Draft"
        mock_doc.get_doc_before_save.return_value = mock_doc_before
        mock_doc.status = "Scheduled"
        mock_doc.name = "Comm-1"

        on_update(mock_doc)

        mock_enqueue.assert_called_once_with(
            method="frappe_apollo.apollo.doctype.communication.communication.update_a_contact",
            queue="medium",
            comm_name="Comm-1"
        )

    @patch("frappe.enqueue")
    def test_on_update_does_not_enqueue_when_status_not_changed_to_scheduled(self, mock_enqueue):
        mock_doc = MagicMock()
        mock_doc_before = MagicMock()
        mock_doc_before.status = "Scheduled"
        mock_doc.get_doc_before_save.return_value = mock_doc_before
        mock_doc.status = "Scheduled"
        
        on_update(mock_doc)
        mock_enqueue.assert_not_called()

        mock_doc_before.status = "Draft"
        mock_doc.status = "Sent"
        on_update(mock_doc)
        mock_enqueue.assert_not_called()

    @patch("frappe.get_doc")
    def test_idempotency(self, mock_get_doc):
        mock_comm = MagicMock()
        mock_comm.get.return_value = "Scheduled"
        mock_get_doc.return_value = mock_comm
        
        # Should return early
        update_a_contact("Comm-1")
        # Ensure it didn't call get_doc for anything else (e.g. MCC)
        self.assertEqual(mock_get_doc.call_count, 1)

    @patch("frappe_apollo.apollo.doctype.communication.communication.wait_for_event")
    @patch("frappe.get_doc")
    @patch("frappe.db.get_value")
    def test_wait_state_mcc(self, mock_get_value, mock_get_doc, mock_wait):
        from frappe_controller.utils.controller import SuspendJob
        mock_wait.side_effect = SuspendJob("Suspended")

        mock_comm = MagicMock()
        mock_comm.get.return_value = None
        mock_mcc = MagicMock()
        mock_mcc.sender = "user@example.com"
        mock_mcc.apollo_account = None

        mock_get_doc.side_effect = [mock_comm, mock_mcc]

        with self.assertRaises(SuspendJob):
            update_a_contact("Comm-1")

        mock_wait.assert_called_once_with(
            event_key=f"doc:Multi Channel Cadence:{mock_mcc.name}:on_update",
            condition="argument.get('apollo_account') and argument.get('apollo_sequence_id')"
        )

    @patch("frappe_apollo.apollo.doctype.communication.communication.wait_for_event")
    @patch("frappe.get_all")
    @patch("frappe.db.get_value")
    @patch("frappe.get_doc")
    def test_wait_state_people(self, mock_get_doc, mock_get_value, mock_get_all, mock_wait):
        from frappe_controller.utils.controller import SuspendJob
        mock_wait.side_effect = SuspendJob("Suspended")

        mock_comm = MagicMock()
        mock_comm.get.return_value = None
        
        mock_mcc = MagicMock()
        mock_mcc.sender = "user@example.com"
        mock_mcc.recipient = "Lead-1"
        mock_mcc.apollo_account = "Acc-1"
        mock_mcc.apollo_sequence_id = "Seq-1"
        
        mock_account = MagicMock()
        mock_account.status = "Authorized"
        
        mock_get_doc.side_effect = [mock_comm, mock_mcc, mock_account]
        
        def mock_get_value_side_effect(*args, **kwargs):
            if args[0] == "Cadence Provider":
                return 1
            return None
            
        mock_get_value.side_effect = mock_get_value_side_effect

        mock_get_all.side_effect = [None] # Empty CRM Lead Apollo ID

        with self.assertRaises(SuspendJob):
            update_a_contact("Comm-1")

        mock_wait.assert_called_once_with(
            event_key="doc:CRM Lead:Lead-1:on_update",
            condition="any(row.get('account') == 'Acc-1' and row.get('apollo_id') for row in argument.get('apollo_ids', []))"
        )

    @patch("frappe_apollo.integrations.apollo.ApolloClient")
    @patch("frappe.get_all")
    @patch("frappe.db.get_value")
    @patch("frappe.get_doc")
    def test_success(self, mock_get_doc, mock_get_value, mock_get_all, mock_client_cls):
        mock_comm = MagicMock()
        mock_comm.get.return_value = None
        mock_comm.content = "content"
        mock_comm.subject = "subject"
        mock_comm.cadence_schedule = "Sch-1"
        
        mock_mcc = MagicMock()
        mock_mcc.name = "MCC-1"
        mock_mcc.sender = "user@example.com"
        mock_mcc.cadence_name = "Cadence-1"
        mock_mcc.recipient = "Lead-1"
        mock_mcc.apollo_account = "Acc-1"
        mock_mcc.apollo_sequence_id = "Seq-1"
        
        mock_account = MagicMock()
        mock_account.status = "Authorized"
        
        mock_cadence = MagicMock()
        mock_sch = MagicMock()
        mock_sch.name = "Sch-1"
        mock_sch.subject_field = "sf-1"
        mock_sch.message_field = "rf-1"
        mock_cadence.cadence_schedules = [mock_sch]
        
        mock_subject_field = MagicMock()
        mock_subject_row = MagicMock()
        mock_subject_row.account = "Acc-1"
        mock_subject_row.apollo_sequence_id = "Seq-1"
        mock_subject_row.apollo_id = "apollo-sf-1"
        mock_subject_field.get.return_value = [mock_subject_row]
        
        mock_response_field = MagicMock()
        mock_response_row = MagicMock()
        mock_response_row.account = "Acc-1"
        mock_response_row.apollo_sequence_id = "Seq-1"
        mock_response_row.apollo_id = "apollo-rf-1"
        mock_response_field.get.return_value = [mock_response_row]

        mock_get_doc.side_effect = [
            mock_comm,
            mock_mcc,
            mock_account,
            mock_cadence,
            mock_subject_field,
            mock_response_field
        ]
        
        def mock_get_value_side_effect(*args, **kwargs):
            if args[0] == "Cadence Provider":
                return 1
            return None
            
        mock_get_value.side_effect = mock_get_value_side_effect
        
        mock_crm_account = MagicMock()
        mock_crm_account.apollo_id = "apollo-person-1"

        def get_all_side_effect(*args, **kwargs):
            if args[0] == "CRM Lead Apollo ID":
                return [mock_crm_account]
            return []

        mock_get_all.side_effect = get_all_side_effect

        mock_client = mock_client_cls.return_value

        update_a_contact("Comm-1")

        mock_client.update_contact.assert_called_once_with(
            "apollo-person-1",
            {"apollo-sf-1": "subject", "apollo-rf-1": "content"}
        )
        
        mock_comm.db_set.assert_any_call("apollo_id", "apollo-person-1")
        mock_comm.db_set.assert_any_call("apollo_status", "Scheduled")

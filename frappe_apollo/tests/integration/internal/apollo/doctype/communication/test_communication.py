import frappe
from frappe.tests import IntegrationTestCase
from frappe_apollo.apollo.doctype.communication.communication import update_a_contact
from frappe_controller.utils.controller import SuspendJob
from unittest.mock import patch, MagicMock

class TestCommunicationIntegration(IntegrationTestCase):
    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    def tearDown(self):
        frappe.db.rollback()
        super().tearDown()

    @patch("frappe_apollo.apollo.doctype.communication.communication.wait_for_event", side_effect=SuspendJob("wait"))
    @patch("frappe.db.get_value")
    @patch("frappe.get_doc")
    @patch("frappe.get_all")
    def test_missing_custom_fields_raises_wait(self, mock_get_all, mock_get_doc, mock_get_value, mock_wait):
        # Setup mocks
        def mock_get_value_side_effect(dt, name_or_filters=None, fieldname=None):
            if dt == "Cadence Provider": return 1
            if dt == "User Email": return "Email-Acc-1"
            return "val"
        mock_get_value.side_effect = mock_get_value_side_effect
        
        mock_comm = MagicMock()
        mock_comm.get.return_value = None
        mock_comm.reference_name = "mcc1"
        mock_comm.cadence_schedule = "sch1"
        
        mock_mcc = MagicMock()
        mock_mcc.sender = "user1"
        mock_mcc.recipient = "lead1"
        mock_mcc.cadence_name = "cad1"
        mock_mcc.apollo_account = "acc1"
        mock_mcc.apollo_sequence_id = "seq1"
        
        mock_account = MagicMock()
        mock_account.status = "Authorized"
        
        mock_cadence = MagicMock()
        mock_sch = MagicMock()
        mock_sch.name = "sch1"
        mock_sch.subject_field = None # Missing field
        mock_sch.message_field = "rf-1"
        mock_cadence.cadence_schedules = [mock_sch]
        
        def mock_get_doc_side_effect(*args, **kwargs):
            doctype = args[0] if args and isinstance(args[0], str) else (args[0].get('doctype') if args else kwargs.get('doctype'))
            if doctype == "Communication": return mock_comm
            if doctype == "Multi Channel Cadence": return mock_mcc
            if doctype == "Apollo Account": print(f"RETURNING MOCK ACCOUNT {mock_account.status}"); return mock_account
            if doctype == "Cadence": return mock_cadence
            return MagicMock()
            
        mock_get_doc.side_effect = mock_get_doc_side_effect
        
        def get_all_side_effect(*args, **kwargs):
            if args[0] == "CRM Lead Apollo ID":
                return [frappe._dict({"apollo_id": "pid1"})]
            return []
            
        mock_get_all.side_effect = get_all_side_effect
        
        with self.assertRaises(SuspendJob):
            update_a_contact("comm1")

    @patch("frappe_apollo.apollo.doctype.communication.communication.wait_for_event", side_effect=SuspendJob("wait"))
    @patch("frappe.db.get_value")
    @patch("frappe.get_doc")
    @patch("frappe.get_all")
    @patch("frappe_apollo.integrations.apollo.ApolloClient")
    def test_valid_sync(self, mock_client_class, mock_get_all, mock_get_doc, mock_get_value, mock_wait):
        # Setup mocks
        def mock_get_value_side_effect(dt, name_or_filters=None, fieldname=None):
            if dt == "Cadence Provider": return 1
            if dt == "User Email": return "Email-Acc-1"
            return "val"
        mock_get_value.side_effect = mock_get_value_side_effect
        
        mock_comm = MagicMock()
        mock_comm.get.return_value = None
        mock_comm.reference_name = "mcc1"
        mock_comm.cadence_schedule = "sch1"
        mock_comm.subject = "Test Sub"
        mock_comm.content = "Test Content"
        
        mock_mcc = MagicMock()
        mock_mcc.sender = "user1"
        mock_mcc.recipient = "lead1"
        mock_mcc.cadence_name = "cad1"
        mock_mcc.apollo_account = "acc1"
        mock_mcc.apollo_sequence_id = "seq1"
        
        mock_account = MagicMock()
        mock_account.status = "Authorized"
        
        mock_cadence = MagicMock()
        mock_sch = MagicMock()
        mock_sch.name = "sch1"
        mock_sch.subject_field = "f1"
        mock_sch.message_field = "f2"
        mock_cadence.cadence_schedules = [mock_sch]
        
        mock_field_1 = MagicMock()
        mock_row1 = MagicMock()
        mock_row1.account = "acc1"
        mock_row1.apollo_sequence_id = "seq1"
        mock_row1.apollo_id = "af1"
        mock_field_1.get.return_value = [mock_row1]
        
        mock_field_2 = MagicMock()
        mock_row2 = MagicMock()
        mock_row2.account = "acc1"
        mock_row2.apollo_sequence_id = "seq1"
        mock_row2.apollo_id = "af2"
        mock_field_2.get.return_value = [mock_row2]
        
        def mock_get_doc_side_effect(*args, **kwargs):
            doctype = args[0] if args and isinstance(args[0], str) else (args[0].get('doctype') if args else kwargs.get('doctype'))
            name = args[1] if len(args) > 1 else kwargs.get('name')
            if doctype == "Communication": return mock_comm
            if doctype == "Multi Channel Cadence": return mock_mcc
            if doctype == "Apollo Account": print(f"RETURNING MOCK ACCOUNT {mock_account.status}"); return mock_account
            if doctype == "Cadence": return mock_cadence
            if doctype == "Apollo Field":
                if name == "f1": return mock_field_1
                if name == "f2": return mock_field_2
            return MagicMock()
            
        mock_get_doc.side_effect = mock_get_doc_side_effect
        
        def get_all_side_effect(*args, **kwargs):
            if args[0] == "CRM Lead Apollo ID":
                return [frappe._dict({"apollo_id": "pid1"})]
            return []
            
        mock_get_all.side_effect = get_all_side_effect
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        update_a_contact("comm1")
        
        mock_client.update_contact.assert_called_once_with("pid1", {"af1": "Test Sub", "af2": "Test Content"})

import frappe
from frappe.tests import UnitTestCase
from frappe_apollo.apollo.doctype.crm_lead.crm_lead import _create_a_contact, create_a_contact, update_a_contact
from frappe_controller.utils.controller import SuspendJob
from unittest.mock import patch, MagicMock, call

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
        cadence.get.return_value = [{"reference_doctype": "Email Template"}] # 1 expected comm
        
        mock_get_doc.side_effect = lambda dt, name: mcc if dt == "Multi Channel Cadence" else cadence
        mock_count.return_value = 0 # 0 actual comms
        
        mock_wait.side_effect = SuspendJob("wait")
        
        with self.assertRaises(SuspendJob):
            _create_a_contact("mcc1")
            
        mock_wait.assert_called_once()

    @patch("frappe.get_doc")
    @patch("frappe.db.count")
    @patch("frappe.db.get_value")
    @patch("frappe.enqueue")
    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_create_a_contact_enqueues_create_if_no_apollo_id(self, mock_wait, mock_enqueue, mock_get_value, mock_count, mock_get_doc):
        mcc = MagicMock()
        mcc.name = "mcc1"
        mcc.status = "Scheduled"
        mcc.sender = "sender"
        mcc.recipient = "lead1"
        mcc.cadence = "cad1"
        
        cadence = MagicMock()
        cadence.get.return_value = [{"reference_doctype": "Email Template"}] # 1 expected comm
        
        email_acc = MagicMock()
        email_acc_row = MagicMock(account="Acc1")
        email_acc.apollo_ids = [email_acc_row]
        
        lead = MagicMock()
        lead.get.return_value = [MagicMock(account="Acc1", apollo_id=None)]
        
        def get_doc_side_effect(dt, name):
            if dt == "Multi Channel Cadence": return mcc
            if dt == "Cadence": return cadence
            if dt == "Email Account": return email_acc
            if dt == "Apollo Account": return MagicMock(status="Authorized")
            if dt == "CRM Lead": return lead
            return MagicMock()
            
        mock_get_doc.side_effect = get_doc_side_effect
        mock_count.return_value = 1
        
        def get_value_side_effect(dt, *args):
            if dt == "Cadence Provider": return 1
            if dt == "User Email": return "EmailAccount1"
            return None
        mock_get_value.side_effect = get_value_side_effect
        
        mock_wait.side_effect = SuspendJob("wait")
        
        with self.assertRaises(SuspendJob):
            _create_a_contact("mcc1")
            
        mock_enqueue.assert_called_once_with(
            method="frappe_apollo.apollo.doctype.crm_lead.crm_lead.create_a_contact",
            queue="short",
            lead_name="lead1",
            account_name="Acc1"
        )
        mock_wait.assert_called_once()

    @patch("frappe.get_doc")
    @patch("frappe.db.count")
    @patch("frappe.db.get_value")
    @patch("frappe.enqueue")
    def test_create_a_contact_enqueues_update_if_apollo_id_exists(self, mock_enqueue, mock_get_value, mock_count, mock_get_doc):
        mcc = MagicMock()
        mcc.name = "mcc1"
        mcc.status = "Scheduled"
        mcc.sender = "sender"
        mcc.recipient = "lead1"
        mcc.cadence = "cad1"
        
        cadence = MagicMock()
        cadence.get.return_value = [{"reference_doctype": "Email Template"}]
        
        email_acc = MagicMock()
        email_acc.apollo_ids = [MagicMock(account="Acc1")]
        
        lead = MagicMock()
        lead.get.return_value = [MagicMock(account="Acc1", apollo_id="contact123")]
        
        def get_doc_side_effect(dt, name):
            if dt == "Multi Channel Cadence": return mcc
            if dt == "Cadence": return cadence
            if dt == "Email Account": return email_acc
            if dt == "Apollo Account": return MagicMock(status="Authorized")
            if dt == "CRM Lead": return lead
            return MagicMock()
            
        mock_get_doc.side_effect = get_doc_side_effect
        mock_count.return_value = 1
        
        def get_value_side_effect(dt, *args):
            if dt == "Cadence Provider": return 1
            if dt == "User Email": return "EmailAccount1"
            return None
        mock_get_value.side_effect = get_value_side_effect
        
        _create_a_contact("mcc1")
        
        mock_enqueue.assert_called_once_with(
            method="frappe_apollo.apollo.doctype.crm_lead.crm_lead.update_a_contact",
            queue="short",
            lead_name="lead1",
            account_name="Acc1"
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
        
        mock_client.update_contact.assert_called_once_with("contact123", {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "organization_name": "Acme"
        })

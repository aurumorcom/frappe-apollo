import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch, MagicMock
from frappe_apollo.webhook import handle, process_webhook
from frappe.exceptions import AuthenticationError

class TestWebhookIntegration(IntegrationTestCase):
    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    def setUp(self):
        super().setUp()

        # Create base records
        frappe.get_doc({
            "doctype": "Apollo Account",
            "account_name": "Webhook Account",
            "webhook_bearer_token": "valid_token"
        }).insert(ignore_permissions=True)

        lead = frappe.get_doc({
            "doctype": "CRM Lead",
            "first_name": "Webhook",
            "email": "webhook@example.com"
        }).insert(ignore_permissions=True)

        lead.append("apollo_ids", {
            "account": "Webhook Account",
            "apollo_id": "contact_123"
        })
        lead.save(ignore_permissions=True)

        cadence = frappe.get_doc({
            "doctype": "Cadence",
            "cadence_name": "Webhook Cadence"
        }).insert(ignore_permissions=True)

        mcc = frappe.get_doc({
            "doctype": "Multi Channel Cadence",
            "name": "MCC-Webhook",
            "recipient": lead.name,
            "sender": "sender@example.com",
            "cadence_name": cadence.name,
            "start_date": "2024-01-01"
        }).insert(ignore_permissions=True, ignore_links=True)
        
        self.lead_name = lead.name
        self.mcc_name = mcc.name
        self.cadence_name = cadence.name

    def tearDown(self):
        frappe.db.rollback()
        super().tearDown()

    @patch("frappe.get_request_header")
    def test_security_unauthorized_no_token(self, mock_header):
        mock_header.return_value = None
        with self.assertRaises(AuthenticationError):
            handle()

    @patch("frappe.get_request_header")
    def test_security_unauthorized_wrong_token(self, mock_header):
        mock_header.return_value = "Bearer invalid_token"
        with self.assertRaises(AuthenticationError):
            handle()

    @patch("frappe.enqueue")
    @patch("frappe.get_request_header")
    def test_security_authorized(self, mock_header, mock_enqueue):
        # We need to access get_password, so the doc needs it
        mock_header.return_value = "Bearer valid_token"
        frappe.request = MagicMock()
        frappe.request.get_json.return_value = {"event": "test"}

        res = handle()
        self.assertEqual(res.get("status"), "ok")
        mock_enqueue.assert_called_once_with(
            method="frappe_apollo.webhook.process_webhook",
            queue="low",
            payload={"event": "test"}
        )

    @patch("frappe_apollo.apollo.doctype.cadence_provider.cadence_provider.ApolloCadenceProvider.report_event")
    def test_process_webhook_message_sent(self, mock_report_event):
        # Create Communication
        comm = frappe.get_doc({
            "doctype": "Communication",
            "communication_type": "Communication",
            "reference_doctype": "Multi Channel Cadence",
            "reference_name": self.mcc_name,
            "delivery_status": "Scheduled",
            "subject": "Test",
            "content": "Test body"
        }).insert(ignore_permissions=True, ignore_links=True)

        payload = {
            "event": "message_sent",
            "contact_id": "contact_123",
            "emailer_campaign_id": "seq_123"
        }

        # Mock get_all to return our Sequence for the specific call
        original_get_all = frappe.get_all
        def mock_get_all_side_effect(doctype, *args, **kwargs):
            if doctype == "Sequence":
                return [frappe._dict({"campaign": self.cadence_name})]
            if doctype == "Communication":
                return [frappe._dict({"name": comm.name})]
            if doctype == "Multi Channel Cadence":
                return [frappe._dict({"name": self.mcc_name})]
            if doctype == "CRM Lead Apollo ID":
                return [frappe._dict({"lead": self.lead_name, "account": "Webhook Account"})]
            return original_get_all(doctype, *args, **kwargs)

        with patch("frappe.get_all", side_effect=mock_get_all_side_effect):
            process_webhook(payload)

        mock_report_event.assert_called_once_with(
            "message_sent",
            {"mcc_name": self.mcc_name, "communication_name": comm.name},
            payload
        )

    @patch("frappe_apollo.apollo.doctype.cadence_provider.cadence_provider.ApolloCadenceProvider.report_event")
    def test_process_webhook_message_opened(self, mock_report_event):
        comm = frappe.get_doc({
            "doctype": "Communication",
            "communication_type": "Communication",
            "reference_doctype": "Multi Channel Cadence",
            "reference_name": self.mcc_name,
            "delivery_status": "Sent",
            "subject": "Test",
            "content": "Test body"
        }).insert(ignore_permissions=True, ignore_links=True)

        payload = {
            "event": "message_opened",
            "contact_id": "contact_123",
            "emailer_campaign_id": "seq_123"
        }

        original_get_all = frappe.get_all
        def mock_get_all_side_effect(doctype, *args, **kwargs):
            if doctype == "Communication":
                return [frappe._dict({"name": comm.name})]
            if doctype == "Multi Channel Cadence":
                return [frappe._dict({"name": self.mcc_name})]
            if doctype == "CRM Lead Apollo ID":
                return [frappe._dict({"lead": self.lead_name, "account": "Webhook Account"})]
            return original_get_all(doctype, *args, **kwargs)

        with patch("frappe.get_all", side_effect=mock_get_all_side_effect):
            process_webhook(payload)

        mock_report_event.assert_called_once_with(
            "message_opened",
            {"mcc_name": self.mcc_name, "communication_name": comm.name},
            payload
        )

    @patch("frappe_apollo.apollo.doctype.cadence_provider.cadence_provider.ApolloCadenceProvider.report_event")
    def test_process_webhook_message_replied(self, mock_report_event):
        payload = {
            "event": "message_replied",
            "contact_id": "contact_123",
            "emailer_campaign_id": "seq_123"
        }

        original_get_all = frappe.get_all
        def mock_get_all_side_effect(doctype, *args, **kwargs):
            if doctype == "Multi Channel Cadence":
                return [frappe._dict({"name": self.mcc_name})]
            if doctype == "CRM Lead Apollo ID":
                return [frappe._dict({"lead": self.lead_name, "account": "Webhook Account"})]
            return original_get_all(doctype, *args, **kwargs)

        with patch("frappe.get_all", side_effect=mock_get_all_side_effect):
            process_webhook(payload)

        mock_report_event.assert_called_once_with(
            "message_replied",
            {"mcc_name": self.mcc_name},
            payload
        )

    @patch("frappe_apollo.apollo.doctype.cadence_provider.cadence_provider.ApolloCadenceProvider.report_event")
    def test_process_webhook_unmapped(self, mock_report_event):
        payload = {
            "event": "message_sent",
            "contact_id": "unknown",
            "emailer_campaign_id": "seq_123"
        }
        
        # Mock get_all to return empty for CRM Lead Apollo ID
        def mock_get_all_side_effect(doctype, *args, **kwargs):
            if doctype == "CRM Lead Apollo ID":
                return []
            return []

        with patch("frappe.get_all", side_effect=mock_get_all_side_effect):
            process_webhook(payload)
            
        mock_report_event.assert_not_called()

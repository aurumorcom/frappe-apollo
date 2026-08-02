import frappe
from frappe.tests import UnitTestCase
from unittest.mock import patch, MagicMock
from frappe_apollo.apollo.doctype.email_account.email_account import queue_get_email_accounts

class TestEmailAccount(UnitTestCase):

    @patch("frappe.enqueue")
    @patch("frappe.get_doc")
    @patch("frappe.get_all")
    def test_queue_get_email_accounts_enqueues_for_api_key_password_field(self, mock_get_all, mock_get_doc, mock_enqueue):
        mock_get_all.return_value = [frappe._dict({"name": "Acc1"})]
        mock_doc = MagicMock()
        mock_doc.get_password.side_effect = lambda field, raise_exception=False: "secret_api_key" if field == "api_key" else None
        mock_doc.access_token = None
        mock_get_doc.return_value = mock_doc

        queue_get_email_accounts()

        mock_enqueue.assert_called_once_with(
            method="frappe_apollo.apollo.doctype.email_account.email_account.get_email_accounts",
            queue="low",
            account_name="Acc1"
        )

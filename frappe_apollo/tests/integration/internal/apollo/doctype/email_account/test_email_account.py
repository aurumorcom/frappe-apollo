from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from frappe_apollo.apollo.doctype.email_account.email_account import (
    get_email_accounts,
    queue_get_email_accounts,
)


class TestEmailAccountIntegration(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        frappe.db.rollback()

        self.acc1 = f"Mailbox Test Acc {frappe.generate_hash(length=6)}"
        self.acc2 = f"Another Test Acc {frappe.generate_hash(length=6)}"
        self.email1 = f"test1_{frappe.generate_hash(length=6)}@example.com"

        frappe.get_doc({
            "doctype": "Apollo Account",
            "account_name": self.acc1,
            "api_key": "some_key"
        }).insert(ignore_permissions=True)

        frappe.get_doc({
            "doctype": "Apollo Account",
            "account_name": self.acc2,
            "api_key": "some_key"
        }).insert(ignore_permissions=True)

        self.addCleanup(frappe.db.rollback)

    def tearDown(self):
        super().tearDown()

    @patch("frappe.enqueue")
    def test_queue_get_email_accounts(self, mock_enqueue):
        queue_get_email_accounts()
        found = False
        for call in mock_enqueue.call_args_list:
            if call[1].get("account_name") == self.acc1:
                found = True
                break
        self.assertTrue(found, f"get_email_accounts was not queued for {self.acc1}")

    @patch("frappe_apollo.integrations.apollo.ApolloClient")
    def test_get_email_accounts_creation(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.get_email_accounts.return_value = {
            "email_accounts": [
                {
                    "id": "mailbox_id_1",
                    "email": self.email1,
                    "active": True
                }
            ]
        }

        get_email_accounts(self.acc1)

        mock_client.get_email_accounts.assert_called_once()

        mailboxes = frappe.get_all("Email Account", filters={"email_id": self.email1})
        self.assertEqual(len(mailboxes), 1)

        mb_doc = frappe.get_doc("Email Account", mailboxes[0].name)
        self.assertEqual(mb_doc.email_id, self.email1)
        self.assertEqual(mb_doc.service, "Apollo")
        self.assertEqual(len(mb_doc.get("apollo_ids")), 1)
        self.assertEqual(mb_doc.apollo_ids[0].account, self.acc1)
        self.assertEqual(mb_doc.apollo_ids[0].apollo_id, "mailbox_id_1")

    @patch("frappe_apollo.integrations.apollo.ApolloClient")
    def test_get_email_accounts_append(self, mock_client_cls):
        frappe.get_doc({
            "doctype": "Email Account",
            "email_id": self.email1,
            "service": "Apollo",
            "enable_outgoing": 0,
            "enable_incoming": 0,
            "apollo_ids": [
                {
                    "account": self.acc1,
                    "apollo_id": "mailbox_id_1"
                }
            ]
        }).insert(ignore_permissions=True)

        mock_client = mock_client_cls.return_value
        mock_client.get_email_accounts.return_value = {
            "email_accounts": [
                {
                    "id": "mailbox_id_1_alt",
                    "email": self.email1,
                    "active": True
                }
            ]
        }

        get_email_accounts(self.acc2)

        mailboxes = frappe.get_all("Email Account", filters={"email_id": self.email1})
        self.assertEqual(len(mailboxes), 1)

        mb_doc = frappe.get_doc("Email Account", mailboxes[0].name)

        # It should now have 2 apollo accounts
        self.assertEqual(len(mb_doc.get("apollo_ids")), 2)
        accounts = [acc.account for acc in mb_doc.get("apollo_ids")]
        self.assertIn(self.acc1, accounts)
        self.assertIn(self.acc2, accounts)

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from frappe_apollo.apollo.doctype.email_account.email_account import (
	get_email_accounts,
	queue_get_email_accounts,
)


class TestEmailAccount(UnitTestCase):
	@patch("frappe.enqueue")
	@patch("frappe.get_doc")
	@patch("frappe.get_all")
	def test_queue_get_email_accounts_enqueues_for_api_key_password_field(
		self, mock_get_all, mock_get_doc, mock_enqueue
	):
		mock_get_all.return_value = [frappe._dict({"name": "Acc1"})]
		mock_doc = MagicMock()
		mock_doc.get_password.side_effect = lambda field, raise_exception=False: (
			"secret_api_key" if field == "api_key" else None
		)
		mock_doc.access_token = None
		mock_get_doc.return_value = mock_doc

		queue_get_email_accounts()

		mock_enqueue.assert_called_once_with(
			method="frappe_apollo.apollo.doctype.email_account.email_account.get_email_accounts",
			queue="low",
			account_name="Acc1",
		)

	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	def test_get_email_accounts_handles_null_email_accounts(self, mock_client_cls):
		mock_client = mock_client_cls.return_value
		mock_client.get_email_accounts.return_value = {"email_accounts": None}

		# Should not raise TypeError: 'NoneType' object is not iterable
		get_email_accounts("Abhishek's Apollo")
		mock_client.get_email_accounts.assert_called_once()

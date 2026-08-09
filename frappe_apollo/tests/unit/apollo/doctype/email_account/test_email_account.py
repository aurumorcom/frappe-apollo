from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from frappe_apollo.apollo.doctype.email_account.email_account import (
	enqueue_get_email_accounts,
	get_email_accounts,
	on_update,
	queue_get_email_accounts,
)


class TestEmailAccount(UnitTestCase):
	@patch("frappe_apollo.apollo.doctype.email_account.email_account.enqueue_get_email_accounts")
	def test_on_update_enqueues_sync(self, mock_enqueue):
		doc = MagicMock()
		frappe.flags.is_apollo_email_account_update = False

		on_update(doc)

		mock_enqueue.assert_called_once()

	@patch("frappe_apollo.apollo.doctype.email_account.email_account.enqueue_get_email_accounts")
	def test_on_update_skips_when_flag_set(self, mock_enqueue):
		doc = MagicMock()
		frappe.flags.is_apollo_email_account_update = True

		try:
			on_update(doc)
			mock_enqueue.assert_not_called()
		finally:
			frappe.flags.is_apollo_email_account_update = False

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

		enqueue_get_email_accounts()

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

	@patch("frappe.db.exists")
	@patch("frappe.db.get_value")
	@patch("frappe.get_doc")
	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	def test_get_email_accounts_maps_aliases_to_existing_email_accounts(
		self, mock_client_cls, mock_get_doc, mock_db_get_value, mock_db_exists
	):
		mock_client = mock_client_cls.return_value
		mock_client.get_email_accounts.return_value = {
			"email_accounts": [
				{
					"id": "mb_primary_123",
					"email": "primary@aurumor.com",
					"active": True,
					"aliases": ["primary@aurumor.com", "alias@capybaara.com"],
				}
			]
		}

		doc_primary = MagicMock()
		doc_primary.get.return_value = []

		doc_alias = MagicMock()
		doc_alias.get.return_value = []

		def get_value_side_effect(dt, filters, field, *args, **kwargs):
			if isinstance(filters, dict):
				email = filters.get("email_id")
				if email == "primary@aurumor.com":
					return "Primary Account Doc"
				elif email == "alias@capybaara.com":
					return "Alias Account Doc"
			return None

		mock_db_get_value.side_effect = get_value_side_effect

		def get_doc_side_effect(dt, name=None):
			if name == "Primary Account Doc":
				return doc_primary
			elif name == "Alias Account Doc":
				return doc_alias
			return MagicMock()

		mock_get_doc.side_effect = get_doc_side_effect

		get_email_accounts("Acc1")

		doc_primary.append.assert_called_once_with("apollo_ids", {"account": "Acc1", "apollo_id": "mb_primary_123"})
		doc_alias.append.assert_called_once_with("apollo_ids", {"account": "Acc1", "apollo_id": "mb_primary_123"})


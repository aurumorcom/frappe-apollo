from unittest.mock import MagicMock, patch

import frappe
import requests
from frappe.tests import UnitTestCase

from frappe_apollo.integrations.apollo import ApolloClient, ApolloRateLimitError


class TestApolloClient(UnitTestCase):
	@patch("frappe.get_doc")
	def test_get_headers_api_key(self, mock_get_doc):
		mock_account = MagicMock()
		mock_account.get_password.side_effect = lambda field, raise_exception=False: (
			"test_key" if field == "api_key" else None
		)
		mock_account.access_token = None
		mock_account.refresh_token = None
		mock_get_doc.return_value = mock_account

		client = ApolloClient("Test Account")
		headers = client._get_headers()

		self.assertEqual(headers.get("X-Api-Key"), "test_key")
		self.assertNotIn("Authorization", headers)

	@patch("frappe.get_doc")
	def test_get_headers_oauth(self, mock_get_doc):
		mock_account = MagicMock()
		mock_account.get_password.side_effect = lambda field, raise_exception=False: (
			"actual_token_value" if field == "access_token" else None
		)
		mock_account.access_token = "some_token"
		mock_get_doc.return_value = mock_account

		client = ApolloClient("Test Account")
		headers = client._get_headers()

		self.assertEqual(headers.get("Authorization"), "Bearer actual_token_value")
		self.assertNotIn("X-Api-Key", headers)

	@patch("frappe.get_doc")
	@patch("frappe_apollo.integrations.apollo.requests.request")
	def test_rate_limit_error(self, mock_request, mock_get_doc):
		mock_account = MagicMock()
		mock_account.get_password.side_effect = lambda field, raise_exception=False: (
			"key" if field == "api_key" else None
		)
		mock_account.refresh_token = None
		mock_account.get.return_value = None
		mock_get_doc.return_value = mock_account

		mock_response = MagicMock()
		mock_response.status_code = 429
		mock_request.return_value = mock_response

		client = ApolloClient("Test Account")

		with self.assertRaises(ApolloRateLimitError):
			client.search_sequences()

	@patch("frappe.get_doc")
	@patch("frappe_apollo.integrations.apollo.requests.request")
	def test_oauth_refresh(self, mock_request, mock_get_doc):
		mock_account = MagicMock()
		mock_account.api_key = None
		mock_account.access_token = "old"
		mock_account.refresh_token = "refresh"
		mock_account.get_password.return_value = "old"
		mock_account.get.return_value = None
		mock_get_doc.return_value = mock_account

		response_401 = MagicMock()
		response_401.status_code = 401

		response_200 = MagicMock()
		response_200.status_code = 200
		response_200.json.return_value = {"success": True}

		mock_request.side_effect = [response_401, response_200]

		client = ApolloClient("Test Account")

		with patch.object(client, "_refresh_oauth_token") as mock_refresh:
			res = client._request("GET", "/test")
			self.assertEqual(res, {"success": True})
			mock_refresh.assert_called_once()
			self.assertEqual(mock_request.call_count, 2)

	@patch("frappe.get_doc")
	@patch("frappe_apollo.integrations.apollo.requests.request")
	def test_fallback_logic_add_contacts(self, mock_request, mock_get_doc):
		mock_account = MagicMock()
		mock_account.refresh_token = None
		mock_account.get.return_value = None
		mock_get_doc.return_value = mock_account

		def mock_request_side_effect(*args, **kwargs):
			if "json" in kwargs and isinstance(kwargs["json"].get("contact_ids"), list):
				response_400 = MagicMock()
				response_400.status_code = 400
				error = requests.exceptions.HTTPError("400")
				error.response = response_400
				raise error

			response_200 = MagicMock()
			response_200.status_code = 200
			response_200.json.return_value = {"success": True}
			return response_200

		mock_request.side_effect = mock_request_side_effect

		client = ApolloClient("Test Account")
		res = client.add_contacts_to_sequence("person-1", "seq-1", "mb-1")

		self.assertEqual(res, {"success": True})
		self.assertEqual(mock_request.call_count, 2)

	@patch("frappe.get_doc")
	@patch("frappe_apollo.integrations.apollo.requests.request")
	def test_add_contacts_to_sequence_with_alias(self, mock_request, mock_get_doc):
		mock_account = MagicMock()
		mock_account.refresh_token = None
		mock_account.get.return_value = None
		mock_get_doc.return_value = mock_account

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {"success": True}
		mock_request.return_value = mock_response

		client = ApolloClient("Test Account")
		res = client.add_contacts_to_sequence("person-1", "seq-1", "mb-1", email_address="alias@example.com")

		self.assertEqual(res, {"success": True})
		mock_request.assert_called_once()
		call_kwargs = mock_request.call_args[1]
		self.assertEqual(call_kwargs["json"]["send_email_from_email_address"], "alias@example.com")

	@patch("frappe.log_error")
	@patch("frappe.db.commit")
	@patch("frappe.get_doc")
	@patch("frappe_apollo.integrations.apollo.requests.post")
	def test_refresh_oauth_token_failure_marks_unauthorized(
		self, mock_post, mock_get_doc, mock_commit, mock_log_error
	):
		mock_account = MagicMock()
		mock_account.get_password.return_value = "token"
		mock_get_doc.return_value = mock_account

		mock_response = MagicMock()
		mock_response.status_code = 401
		http_error = requests.exceptions.HTTPError("401 Client Error")
		mock_response.raise_for_status.side_effect = http_error
		mock_post.return_value = mock_response

		client = ApolloClient("Test Account")

		with self.assertRaises(requests.exceptions.HTTPError):
			client._refresh_oauth_token()

		self.assertEqual(mock_account.status, "Unauthorized")
		self.assertIsNone(mock_account.access_token)
		self.assertIsNone(mock_account.refresh_token)
		mock_account.save.assert_called_once_with(ignore_permissions=True)
		mock_commit.assert_called_once()

	@patch("frappe.get_doc")
	@patch("frappe_apollo.integrations.apollo.requests.request")
	def test_get_email_accounts(self, mock_request, mock_get_doc):
		mock_account = MagicMock()
		mock_account.refresh_token = None
		mock_account.get.return_value = None
		mock_get_doc.return_value = mock_account

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {"email_accounts": [{"id": "mb1", "email": "test@example.com"}]}
		mock_request.return_value = mock_response

		client = ApolloClient("Test Account")
		res = client.get_email_accounts()

		self.assertIn("email_accounts", res)
		self.assertEqual(len(res["email_accounts"]), 1)
		mock_request.assert_called_once_with(
			"GET", "https://api.apollo.io/api/v1/email_accounts", headers=client._get_headers()
		)

	@patch("frappe.get_doc")
	def test_get_sequence_success(self, mock_get_doc):
		mock_account = MagicMock()
		mock_get_doc.return_value = mock_account

		client = ApolloClient("Test Account")
		target_seq = {"id": "seq_123", "name": "Target", "emailer_steps": [{"id": "step_1"}]}
		with patch.object(client, "search_sequences") as mock_search:
			mock_search.return_value = {"pagination": {"total_pages": 1}, "emailer_campaigns": [target_seq]}
			res = client.get_sequence("seq_123")

			self.assertEqual(res["emailer_campaign"], target_seq)
			self.assertEqual(res["emailer_steps"], [{"id": "step_1"}])
			mock_search.assert_called_once_with(page=1, per_page=100)

	@patch("frappe.get_doc")
	def test_get_sequence_not_found(self, mock_get_doc):
		mock_account = MagicMock()
		mock_get_doc.return_value = mock_account

		client = ApolloClient("Test Account")
		with patch.object(client, "search_sequences") as mock_search:
			mock_search.return_value = {
				"pagination": {"total_pages": 1},
				"emailer_campaigns": [{"id": "seq_other", "name": "Other"}],
			}
			res = client.get_sequence("seq_missing")

			self.assertEqual(res["emailer_campaign"], {})
			self.assertEqual(res["emailer_steps"], [])
			mock_search.assert_called_once_with(page=1, per_page=100)

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase


class TestOAuth(IntegrationTestCase):
	def setUp(self):
		super().setUp()

		if not frappe.db.exists("Apollo Account", "Test Account OAuth"):
			# Create Account
			frappe.get_doc(
				{
					"doctype": "Apollo Account",
					"account_name": "Test Account OAuth",
					"webhook_bearer_token": "secret123",
					"client_id": "client_id",
					"client_secret": "client_secret",
				}
			).insert()

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		frappe.delete_doc_if_exists("Apollo Account", "Test Account OAuth", force=True)
		frappe.db.commit()
		frappe.local.conf.pop("encryption_key", None)
		super().tearDownClass()

	def tearDown(self):
		frappe.db.rollback()
		frappe.delete_doc_if_exists("Apollo Account", "Test Account OAuth", force=True)
		frappe.db.commit()
		super().tearDown()

	@patch("frappe_apollo.oauth.requests.post")
	def test_oauth_callback(self, mock_post):
		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {"access_token": "new_access", "refresh_token": "new_refresh"}
		mock_post.return_value = mock_response

		frappe.local.response = {}

		from frappe_apollo.oauth import callback

		callback("auth_code_123", "Test Account OAuth")

		account = frappe.get_doc("Apollo Account", "Test Account OAuth")
		self.assertEqual(account.get_password("access_token"), "new_access")
		self.assertEqual(account.get_password("refresh_token"), "new_refresh")

		self.assertEqual(frappe.local.response["type"], "redirect")
		self.assertEqual(frappe.local.response["location"], "/app/apollo-account/Test Account OAuth")

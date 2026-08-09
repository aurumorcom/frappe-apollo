import unittest

import frappe
from frappe.tests import IntegrationTestCase

from frappe_apollo.integrations.apollo import ApolloClient
from frappe_apollo.tests.integration.external.conftest import my_vcr


class TestApolloExternalAPI(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		import os
		# Use the account provided by the user via site_config or environment variable
		cls.account_name = frappe.conf.get("apollo_test_account") or os.environ.get("APOLLO_TEST_ACCOUNT")
		cls.sequence_id = frappe.conf.get("apollo_test_sequence_id") or os.environ.get("APOLLO_TEST_SEQUENCE_ID")

		if cls.account_name and frappe.db.exists("Apollo Account", cls.account_name):
			doc = frappe.get_doc("Apollo Account", cls.account_name)
			try:
				if not doc.get_password("api_key") and not doc.access_token:
					cls.account_name = None
			except Exception:
				cls.account_name = None

		# If no real credentials are provided, use dummy ones for VCR replay
		if not cls.account_name:
			cls.account_name = "Dummy VCR Account"

		if not cls.sequence_id:
			cls.sequence_id = "6a0cdfe8da382d001cc8423e" # Default sequence ID from cassettes

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		if getattr(cls, "account_name", None):
			frappe.delete_doc_if_exists("Apollo Account", cls.account_name, force=True)
		frappe.db.commit()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		if not frappe.db.exists("Apollo Account", self.account_name):
			doc = frappe.new_doc("Apollo Account")
			doc.account_name = self.account_name
			doc.status = "Authorized"
			if self.account_name == "Dummy VCR Account":
				doc.api_key = "dummy_api_key_for_vcr"
				doc.refresh_token = None
				doc.access_token = None
				doc.expired = None
			doc.insert(ignore_permissions=True)
		elif self.account_name == "Dummy VCR Account":
			doc = frappe.get_doc("Apollo Account", self.account_name)
			doc.api_key = "dummy_api_key_for_vcr"
			doc.refresh_token = None
			doc.access_token = None
			doc.expired = None
			doc.status = "Authorized"
			doc.save(ignore_permissions=True)
		self.client = ApolloClient(self.account_name)

	def tearDown(self):
		frappe.db.rollback()
		if getattr(self, "account_name", None) == "Dummy VCR Account":
			frappe.delete_doc_if_exists("Apollo Account", self.account_name, force=True)
			frappe.db.commit()
		super().tearDown()

	@my_vcr.use_cassette('test_get_email_accounts.yaml')
	def test_get_email_accounts_live(self):
		response = self.client.get_email_accounts()
		self.assertIn("email_accounts", response)
		self.assertIsInstance(response["email_accounts"], list)

	@my_vcr.use_cassette('test_search_sequences.yaml')
	def test_search_sequences_live(self):
		response = self.client.search_sequences()
		self.assertIn("emailer_campaigns", response)
		self.assertIsInstance(response["emailer_campaigns"], list)

	@my_vcr.use_cassette('test_create_contact.yaml')
	def test_create_contact_live(self):
		lead_data = {
			"first_name": "Test",
			"last_name": "External API",
			"email": "test_external_api_create@example.com"
		}
		contact_res = self.client.create_contact(lead_data)
		contact_id = contact_res.get("contact", {}).get("id") if isinstance(contact_res, dict) else contact_res
		self.assertIsNotNone(contact_id)

	@my_vcr.use_cassette('test_create_custom_field.yaml')
	def test_create_custom_field_live(self):
		field_name = "Test External Field VCR"
		response = self.client.create_custom_field(field_name, "string")
		self.assertIn("typed_custom_field", response)
		self.assertEqual(response["typed_custom_field"]["name"], field_name)

	@my_vcr.use_cassette('test_update_contact.yaml')
	def test_update_contact_live(self):
		# Setup: Create a contact to update
		lead_data = {
			"first_name": "Test",
			"last_name": "External API Update",
			"email": "test_external_api_update@example.com"
		}
		contact_res = self.client.create_contact(lead_data)
		contact_id = contact_res.get("contact", {}).get("id") if isinstance(contact_res, dict) else contact_res
		self.assertIsNotNone(contact_id)

		# Act: Update the contact
		custom_fields = {
			"test_external_field": "Test Value"
		}
		response = self.client.update_contact(contact_id, custom_fields)

		# Assert
		self.assertIn("contact", response)

	@my_vcr.use_cassette('test_add_contacts_to_sequence.yaml')
	def test_add_contacts_to_sequence_live(self):
		# Setup: Get a mailbox ID
		accounts_response = self.client.get_email_accounts()
		if not accounts_response.get("email_accounts"):
			self.skipTest("No email accounts available to send from")
		mailbox_id = accounts_response["email_accounts"][0].get("id")

		# Setup: Create a contact to add to the sequence
		lead_data = {
			"first_name": "Test",
			"last_name": "External API Sequence",
			"email": "test_external_api_sequence@example.com"
		}
		contact_res = self.client.create_contact(lead_data)
		contact_id = contact_res.get("contact", {}).get("id") if isinstance(contact_res, dict) else contact_res
		self.assertIsNotNone(contact_id)

		# Act: Add to sequence
		response = self.client.add_contacts_to_sequence(contact_id, self.sequence_id, mailbox_id)

		# Assert
		self.assertIn("contacts", response)

	@my_vcr.use_cassette('test_create_sequence.yaml')
	def test_create_sequence_live(self):
		import os
		if not frappe.conf.get("apollo_test_account") and not os.environ.get("APOLLO_TEST_ACCOUNT"):
			if not os.path.exists(os.path.join(os.path.dirname(__file__), 'cassettes', 'test_create_sequence.yaml')):
				self.skipTest("No credentials and no cassette found for this test.")

		# Ensure fields exist before creating sequence
		for field in ["subject", "message"]:
			try:
				self.client.create_custom_field(field, "string")
			except Exception:
				pass

		sequence_name = "Test External Sequence VCR"
		emailer_steps = [{
			"type": "auto_email",
			"wait_time": 1,
			"wait_mode": "day",
			"emailer_touches": [{
				"type": "new_thread",
				"status": "approved",
				"include_signature": True,
				"emailer_template": {
					"subject": "{{subject}}",
					"body_html": "{{message}}"
				}
			}]
		}]
		sequence_id = self.client.create_sequence(sequence_name, emailer_steps=emailer_steps)
		self.assertIsNotNone(sequence_id)
		self.assertEqual(isinstance(sequence_id, str), True)

	@my_vcr.use_cassette('test_update_sequence.yaml')
	def test_update_sequence_live(self):
		import os
		if not frappe.conf.get("apollo_test_account") and not os.environ.get("APOLLO_TEST_ACCOUNT"):
			if not os.path.exists(os.path.join(os.path.dirname(__file__), 'cassettes', 'test_update_sequence.yaml')):
				self.skipTest("No credentials and no cassette found for this test.")

		# Ensure fields exist before creating sequence
		for field in ["subject_update", "message_update"]:
			try:
				self.client.create_custom_field(field, "string")
			except Exception:
				pass

		# Setup: Create a sequence to update
		sequence_id = self.client.create_sequence("Test External Sequence Update VCR")
		self.assertIsNotNone(sequence_id)

		# Act: Update the sequence
		emailer_steps = [{
			"position": 1,
			"type": "auto_email",
			"wait_time": 1,
			"wait_mode": "day",
			"emailer_touches": [{
				"type": "new_thread",
				"status": "approved",
				"include_signature": True,
				"emailer_template": {
					"subject": "{{subject_update}}",
					"body_html": "{{message_update}}"
				}
			}]
		}]
		payload = {"emailer_steps": emailer_steps}
		response = self.client.update_sequence(sequence_id, payload)

		# Assert
		self.assertIn("emailer_campaign", response)
		updated_steps = response.get("emailer_campaign", {}).get("emailer_steps", [])
		self.assertEqual(len(updated_steps), 1, "Steps should be updated in the sequence")

		# Check touches
		touches = response.get("emailer_touches", [])
		self.assertEqual(len(touches), 1, "Email touches should be present in the response")
		self.assertEqual(touches[0].get("status"), "approved", "Touch status should be approved")
		self.assertEqual(touches[0].get("type"), "new_thread", "Touch type should be new_thread")

	@my_vcr.use_cassette("test_apollo_refresh.yaml")
	def test_proactive_token_refresh(self):
		import os

		if not frappe.conf.get("apollo_test_account") and not os.environ.get("APOLLO_TEST_ACCOUNT"):
			if not os.path.exists(
				os.path.join(os.path.dirname(__file__), "cassettes", "test_apollo_refresh.yaml")
			):
				self.skipTest("No credentials and no cassette found for this test.")

		account = frappe.get_doc("Apollo Account", self.account_name)
		original_expired = frappe.utils.add_to_date(frappe.utils.now_datetime(), days=-1)
		account.db_set("expired", original_expired)
		account.db_set("refresh_token", "dummy_refresh")
		account.db_set("status", "Authorized")

		self.client.account.reload()

		from unittest.mock import MagicMock, patch

		# Proactive refresh should trigger before making the request
		with patch("frappe_apollo.integrations.apollo.requests.post") as mock_post:
			mock_response = MagicMock()
			mock_response.status_code = 200
			mock_response.json.return_value = {
				"access_token": "new_access",
				"refresh_token": "new_refresh",
				"expires_in": 3600,
			}
			mock_post.return_value = mock_response

			response = self.client.get_email_accounts()
			mock_post.assert_called_once()

		account.reload()
		self.assertIn("email_accounts", response)
		self.assertGreater(account.expired, original_expired)
		self.assertEqual(account.status, "Authorized")

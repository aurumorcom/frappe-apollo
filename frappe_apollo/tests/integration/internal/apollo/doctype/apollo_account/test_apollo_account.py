from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from frappe_apollo.apollo.doctype.apollo_account.apollo_account import provision_sequence


class TestApolloAccountIntegration(IntegrationTestCase):
	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		if not frappe.db.exists("Apollo Account", "TestProvisionAccount"):
			frappe.get_doc(
				{
					"doctype": "Apollo Account",
					"account_name": "TestProvisionAccount",
					"status": "Unauthorized",
					"api_key": "dummy_key",
				}
			).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Apollo Account", "TestProvisionAccount", "status", "Unauthorized")
			frappe.db.set_value("Apollo Account", "TestProvisionAccount", "apollo_sequence_id", None)

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	@patch("frappe.wait_for_event")
	def test_provision_sequence_suspends_when_unauthorized(self, mock_wait):
		frappe.db.set_value("Apollo Account", "TestProvisionAccount", "status", "Unauthorized")
		mock_wait.side_effect = SuspendJob("wait_authorized")

		with self.assertRaises(SuspendJob):
			provision_sequence("TestProvisionAccount")

		mock_wait.assert_called_once_with(
			event_key="doc:Apollo Account:TestProvisionAccount:on_update",
			condition="argument.get('status') == 'Authorized'",
		)

	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	def test_provision_sequence_creates_sequence_and_updates_account(self, mock_client_cls):
		frappe.db.set_value("Apollo Account", "TestProvisionAccount", "status", "Authorized")
		frappe.db.set_value("Apollo Account", "TestProvisionAccount", "apollo_sequence_id", None)

		mock_client = mock_client_cls.return_value
		mock_client.search_sequences.return_value = {"emailer_campaigns": []}
		mock_client.create_sequence.return_value = "seq_prov_999"

		provision_sequence("TestProvisionAccount")

		mock_client.create_sequence.assert_called_once_with(
			name="Cadence from Frappe", active=True, emailer_steps=[]
		)

		seq_id = frappe.db.get_value("Apollo Account", "TestProvisionAccount", "apollo_sequence_id")
		self.assertEqual(seq_id, "seq_prov_999")

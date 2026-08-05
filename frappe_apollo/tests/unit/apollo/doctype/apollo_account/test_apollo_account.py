from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase
from frappe_controller.utils.controller import SuspendJob

from frappe_apollo.apollo.doctype.apollo_account.apollo_account import (
	ApolloAccount,
	provision_sequence,
)


class TestApolloAccount(UnitTestCase):
	@patch("frappe_controller.utils.background_jobs.enqueue")
	def test_on_update_enqueues_provision_sequence_when_status_changes_to_authorized(self, mock_enqueue):
		doc = ApolloAccount({"doctype": "Apollo Account", "name": "Acc1", "status": "Authorized"})
		doc.has_value_changed = MagicMock(side_effect=lambda field: True if field == "status" else False)

		doc.on_update()

		mock_enqueue.assert_called_once_with(
			"frappe_apollo.apollo.doctype.apollo_account.apollo_account.provision_sequence",
			queue="low",
			account_name="Acc1",
		)

	@patch("frappe.db.get_value")
	@patch("frappe_controller.utils.controller.wait_for_event")
	def test_provision_sequence_suspends_if_not_authorized(self, mock_wait, mock_db_get_value):
		mock_db_get_value.return_value = "Unauthorized"
		mock_wait.side_effect = SuspendJob("wait")

		with self.assertRaises(SuspendJob):
			provision_sequence("Acc1")

		mock_wait.assert_called_once_with(
			event_key="doc:Apollo Account:Acc1:on_update",
			condition="argument.get('status') == 'Authorized'",
		)

	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe.db.get_value")
	def test_provision_sequence_returns_early_if_sequence_id_exists(self, mock_db_get_value, mock_client_cls):
		def db_get_value_side_effect(dt, name, field=None):
			if field == "status":
				return "Authorized"
			if field == "apollo_sequence_id":
				return "existing_seq_123"
			return None

		mock_db_get_value.side_effect = db_get_value_side_effect

		provision_sequence("Acc1")

		mock_client_cls.assert_not_called()

	@patch("frappe.get_doc")
	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe.db.get_value")
	def test_provision_sequence_uses_existing_apollo_sequence_if_found(
		self, mock_db_get_value, mock_client_cls, mock_get_doc
	):
		def db_get_value_side_effect(dt, name, field=None):
			if field == "status":
				return "Authorized"
			if field == "apollo_sequence_id":
				return None
			return None

		mock_db_get_value.side_effect = db_get_value_side_effect

		mock_client = mock_client_cls.return_value
		mock_client.search_sequences.return_value = {
			"emailer_campaigns": [{"id": "found_seq_999", "name": "Cadence from Frappe"}]
		}

		mock_account_doc = MagicMock()
		mock_get_doc.return_value = mock_account_doc

		provision_sequence("Acc1")

		mock_client.search_sequences.assert_called_once_with(q_name="Cadence from Frappe")
		mock_client.create_sequence.assert_not_called()
		mock_account_doc.db_set.assert_called_once_with("apollo_sequence_id", "found_seq_999")
		mock_account_doc.notify_update.assert_called_once()

	@patch("frappe.get_doc")
	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe.db.get_value")
	def test_provision_sequence_creates_sequence_if_not_found(
		self, mock_db_get_value, mock_client_cls, mock_get_doc
	):
		def db_get_value_side_effect(dt, name, field=None):
			if field == "status":
				return "Authorized"
			if field == "apollo_sequence_id":
				return None
			return None

		mock_db_get_value.side_effect = db_get_value_side_effect

		mock_client = mock_client_cls.return_value
		mock_client.search_sequences.return_value = {"emailer_campaigns": []}
		mock_client.create_sequence.return_value = "new_seq_001"

		mock_account_doc = MagicMock()
		mock_get_doc.return_value = mock_account_doc

		provision_sequence("Acc1")

		mock_client.create_sequence.assert_called_once_with(
			name="Cadence from Frappe", active=True, emailer_steps=[]
		)
		mock_account_doc.db_set.assert_called_once_with("apollo_sequence_id", "new_seq_001")
		mock_account_doc.notify_update.assert_called_once()

	@patch("frappe.log_error")
	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe.db.get_value")
	def test_provision_sequence_handles_403_forbidden(self, mock_db_get_value, mock_client_cls, mock_log_error):
		import requests

		def db_get_value_side_effect(dt, name, field=None):
			if field == "status":
				return "Authorized"
			if field == "apollo_sequence_id":
				return None
			return None

		mock_db_get_value.side_effect = db_get_value_side_effect

		mock_client = mock_client_cls.return_value
		response_403 = MagicMock()
		response_403.status_code = 403
		error = requests.exceptions.HTTPError("403 Forbidden")
		error.response = response_403
		mock_client.search_sequences.side_effect = error

		# Should not raise exception
		provision_sequence("Acc1")

		mock_log_error.assert_called_once()


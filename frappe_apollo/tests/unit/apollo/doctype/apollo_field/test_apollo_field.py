from unittest.mock import MagicMock, call, patch

import frappe
from frappe.exceptions import DoesNotExistError
from frappe.tests import UnitTestCase

from frappe_apollo.apollo.doctype.apollo_field.apollo_field import (
	enqueue_provision_cadence_fields,
	provision_a_field,
)


class TestField(UnitTestCase):

	@patch("frappe_controller.utils.background_jobs.enqueue")
	@patch("frappe.get_doc")
	def test_enqueue_provision_cadence_fields(self, mock_get_doc, mock_enqueue):
		mock_cadence = MagicMock()
		mock_cadence.name = "Cad1"

		mock_step1 = MagicMock(reference_doctype="Email Template", channel="Email")
		mock_cadence.get.return_value = [mock_step1]

		mock_provider = MagicMock()
		mock_chan = MagicMock(channel="Email")
		mock_provider.get.return_value = [mock_chan]

		mock_get_doc.side_effect = [mock_cadence, mock_provider]

		enqueue_provision_cadence_fields("Cad1", "Acc1", "Sender1")

		mock_enqueue.assert_has_calls([
			call(
				"frappe_apollo.apollo.doctype.apollo_field.apollo_field.provision_a_field",
				queue="low",
				label="subject_1",
				apollo_type="string",
				account_name="Acc1"
			),
			call(
				"frappe_apollo.apollo.doctype.apollo_field.apollo_field.provision_a_field",
				queue="low",
				label="body_1",
				apollo_type="textarea",
				account_name="Acc1"
			)
		])

	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe.db.get_value")
	@patch("frappe.get_doc")
	def test_provision_a_field_creates_field_doc_and_custom_field(self, mock_get_doc, mock_get_value, mock_client_cls):
		mock_client = mock_client_cls.return_value
		mock_client.create_custom_field.return_value = {"typed_custom_fields": [{"id": "apollo_123"}]}

		mock_field_doc = MagicMock()
		mock_field_doc.label = "subject_1"
		mock_field_doc.field_type = "string"
		mock_field_doc.get.return_value = [] # no apollo_ids

		def mock_get_doc_side_effect(doctype, *args, **kwargs):
			if doctype == "Apollo Field":
				return mock_field_doc
			return MagicMock()

		mock_get_doc.side_effect = mock_get_doc_side_effect
		mock_get_value.side_effect = lambda dt, name, field: 1 if dt == "Cadence Provider" else "Authorized"

		provision_a_field("subject_1", "string", "Acc1")

		mock_client.create_custom_field.assert_called_once_with("subject_1", "string")
		mock_field_doc.append.assert_called_once_with("apollo_ids", {
			"account": "Acc1",
			"apollo_id": "apollo_123"
		})
		mock_field_doc.save.assert_called_once_with(ignore_permissions=True)

	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe.db.get_value")
	@patch("frappe.get_doc")
	@patch("frappe.log_error")
	def test_provision_a_field_re_raises_exception(self, mock_log_error, mock_get_doc, mock_get_value, mock_client_cls):
		mock_client = mock_client_cls.return_value
		mock_client.create_custom_field.side_effect = Exception("API custom field error")

		mock_field_doc = MagicMock()
		mock_field_doc.label = "body_1"
		mock_field_doc.field_type = "textarea"
		mock_field_doc.get.return_value = []

		mock_get_doc.side_effect = lambda dt, *args, **kwargs: mock_field_doc if dt == "Apollo Field" else MagicMock()
		mock_get_value.side_effect = lambda dt, name, field: 1 if dt == "Cadence Provider" else "Authorized"

		with self.assertRaises(Exception):
			provision_a_field("body_1", "textarea", "Acc1")

		mock_log_error.assert_called_once_with(title="Apollo Field Creation Failed", message="API custom field error")

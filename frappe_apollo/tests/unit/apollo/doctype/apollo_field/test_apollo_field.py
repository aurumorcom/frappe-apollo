from unittest.mock import MagicMock, call, patch

import frappe
from frappe.exceptions import DoesNotExistError
from frappe.tests import UnitTestCase
from frappe_controller.utils.controller import SuspendJob

from frappe_apollo.apollo.doctype.apollo_field.apollo_field import (
	_update_sequence,
	enqueue_provision_cadence_fields,
	provision_a_field,
)


class TestField(UnitTestCase):
	@patch("frappe_controller.utils.background_jobs.enqueue")
	@patch("frappe.get_doc")
	def test_enqueue_provision_cadence_fields(self, mock_get_doc, mock_enqueue):
		mock_cadence = MagicMock()
		mock_cadence.name = "Cad1"

		mock_step1 = MagicMock()
		mock_step1.get.side_effect = lambda k, d=None: (
			"Email" if k == "channel" else ("Email Template" if k == "reference_doctype" else d)
		)
		mock_cadence.get.side_effect = lambda k, d=None: [mock_step1] if k == "cadence_schedules" else d

		mock_provider = MagicMock()
		mock_chan = MagicMock()
		mock_chan.channel = "Email"
		mock_provider.get.side_effect = lambda k, d=None: [mock_chan] if k == "channels" else d

		mock_get_doc.side_effect = [mock_cadence, mock_provider]

		enqueue_provision_cadence_fields("Cad1", "Acc1", "Sender1")

		mock_enqueue.assert_has_calls(
			[
				call(
					"frappe_apollo.apollo.doctype.apollo_field.apollo_field.provision_a_field",
					queue="low",
					label="subject_1",
					apollo_type="string",
					account_name="Acc1",
				),
				call(
					"frappe_apollo.apollo.doctype.apollo_field.apollo_field.provision_a_field",
					queue="low",
					label="body_1",
					apollo_type="textarea",
					account_name="Acc1",
				),
			]
		)

	@patch("frappe_apollo.apollo.doctype.apollo_field.apollo_field._update_sequence")
	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe.db.get_value")
	@patch("frappe.get_doc")
	def test_provision_a_field_creates_field_doc_and_custom_field(
		self, mock_get_doc, mock_get_value, mock_client_cls, mock_update_seq
	):
		mock_client = mock_client_cls.return_value
		mock_client.create_custom_field.return_value = {"typed_custom_fields": [{"id": "apollo_123"}]}

		mock_field_doc = MagicMock()
		mock_field_doc.label = "subject_1"
		mock_field_doc.field_type = "string"
		mock_field_doc.get.return_value = []  # no apollo_ids

		def mock_get_doc_side_effect(doctype, *args, **kwargs):
			if doctype == "Apollo Field":
				return mock_field_doc
			return MagicMock()

		mock_get_doc.side_effect = mock_get_doc_side_effect
		mock_get_value.side_effect = lambda dt, name, field: (
			1 if dt == "Cadence Provider" else ("Authorized" if field == "status" else "seq_123")
		)

		provision_a_field("subject_1", "string", "Acc1")

		mock_client.create_custom_field.assert_called_once_with("subject_1", "string")
		mock_field_doc.append.assert_called_once_with(
			"apollo_ids", {"account": "Acc1", "apollo_id": "apollo_123"}
		)
		mock_field_doc.save.assert_called_once_with(ignore_permissions=True)
		mock_update_seq.assert_called_once_with(mock_client, "seq_123", "subject_1")

	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe.db.get_value")
	@patch("frappe.get_doc")
	@patch("frappe.log_error")
	def test_provision_a_field_re_raises_exception(
		self, mock_log_error, mock_get_doc, mock_get_value, mock_client_cls
	):
		mock_client = mock_client_cls.return_value
		mock_client.create_custom_field.side_effect = Exception("API custom field error")

		mock_field_doc = MagicMock()
		mock_field_doc.label = "body_1"
		mock_field_doc.field_type = "textarea"
		mock_field_doc.get.return_value = []

		mock_get_doc.side_effect = lambda dt, *args, **kwargs: (
			mock_field_doc if dt == "Apollo Field" else MagicMock()
		)
		mock_get_value.side_effect = lambda dt, name, field: (
			1 if dt == "Cadence Provider" else ("Authorized" if field == "status" else "seq_123")
		)

		with self.assertRaises(Exception):
			provision_a_field("body_1", "textarea", "Acc1")

		mock_log_error.assert_called_once_with(
			title="Apollo Field Creation Failed", message="API custom field error"
		)

	@patch("frappe_controller.utils.controller.wait_for_event")
	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe.db.get_value")
	@patch("frappe.get_doc")
	def test_provision_a_field_waits_for_apollo_sequence_id(
		self, mock_get_doc, mock_get_value, mock_client_cls, mock_wait
	):
		mock_field_doc = MagicMock()
		mock_field_doc.label = "subject_1"
		mock_field_doc.field_type = "string"
		mock_field_doc.get.return_value = [MagicMock(account="Acc1")]  # already mapped

		mock_get_doc.side_effect = lambda dt, *args, **kwargs: (
			mock_field_doc if dt == "Apollo Field" else MagicMock()
		)

		def get_value_side_effect(dt, name, field):
			if dt == "Cadence Provider":
				return 1
			if dt == "Apollo Account":
				if field == "status":
					return "Authorized"
				if field == "apollo_sequence_id":
					return None
			return None

		mock_get_value.side_effect = get_value_side_effect
		mock_wait.side_effect = SuspendJob("wait_for_seq")

		with self.assertRaises(SuspendJob):
			provision_a_field("subject_1", "string", "Acc1")

		mock_wait.assert_called_once_with(
			event_key="doc:Apollo Account:Acc1:on_update",
			condition="argument.get('apollo_sequence_id')",
		)

	def test_update_sequence_appends_steps_when_needed(self):
		mock_client = MagicMock()
		mock_client.get_sequence.return_value = {"emailer_steps": []}

		_update_sequence(mock_client, "seq_123", "subject_2")

		mock_client.get_sequence.assert_called_once_with("seq_123")
		mock_client.update_sequence.assert_called_once()
		args, _ = mock_client.update_sequence.call_args
		self.assertEqual(args[0], "seq_123")
		new_steps = args[1].get("emailer_steps", [])
		self.assertEqual(len(new_steps), 2)
		self.assertEqual(new_steps[0]["position"], 1)
		self.assertEqual(new_steps[1]["position"], 2)
		self.assertIn(
			"custom_field_subject_2", new_steps[1]["emailer_touches"][0]["emailer_template"]["subject"]
		)

	def test_update_sequence_noop_when_capacity_sufficient(self):
		mock_client = MagicMock()
		mock_client.get_sequence.return_value = {"emailer_steps": [{"id": 1}, {"id": 2}]}

		_update_sequence(mock_client, "seq_123", "subject_2")

		mock_client.get_sequence.assert_called_once_with("seq_123")
		mock_client.update_sequence.assert_not_called()

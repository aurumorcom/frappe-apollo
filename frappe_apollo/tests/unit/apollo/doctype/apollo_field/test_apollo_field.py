from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from frappe_apollo.apollo.doctype.apollo_field.apollo_field import (
	enqueue_provision_cadence_fields,
	provision_a_field,
)


class TestField(UnitTestCase):
	@patch("frappe_apollo.apollo.doctype.cadence.cadence.update_sequence_steps")
	def test_enqueue_provision_cadence_fields_delegates_to_update_sequence_steps(
		self, mock_update_seq
	):
		enqueue_provision_cadence_fields("Cad1", "Acc1", "Sender1")
		mock_update_seq.assert_called_once_with("Cad1", "Acc1", sender="Sender1")

	@patch("frappe.get_all")
	@patch("frappe_apollo.apollo.doctype.cadence.cadence.update_sequence_steps")
	def test_provision_a_field_delegates_to_update_sequence_steps(
		self, mock_update_seq, mock_get_all
	):
		mock_get_all.return_value = ["Cad1"]

		provision_a_field("subject_1", "string", "Acc1")

		mock_get_all.assert_called_once_with("Cadence Apollo ID", filters={"account": "Acc1"}, pluck="parent")
		mock_update_seq.assert_called_once_with("Cad1", "Acc1")

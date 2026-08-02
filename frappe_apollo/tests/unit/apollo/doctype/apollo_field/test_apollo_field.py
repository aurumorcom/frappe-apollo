import frappe
from frappe.tests import UnitTestCase
from frappe_apollo.apollo.doctype.apollo_field.apollo_field import enqueue_provision_cadence_fields, provision_a_field
from frappe.exceptions import DoesNotExistError
from unittest.mock import patch, MagicMock, call
from frappe_controller.utils.controller import SuspendJob
import hashlib

class TestField(UnitTestCase):

    @patch("frappe_controller.utils.background_jobs.enqueue")
    @patch("frappe.get_doc")
    def test_enqueue_provision_cadence_fields(self, mock_get_doc, mock_enqueue):
        mock_cadence = MagicMock()
        mock_cadence.name = "Cad1"
        mock_step1 = MagicMock()
        mock_step1.reference_doctype = "Email Template"
        mock_step1.name = "step1"
        mock_cadence.get.return_value = [mock_step1]
        mock_get_doc.return_value = mock_cadence
        
        enqueue_provision_cadence_fields("Cad1", "Acc1", "Sender1")
        
        mock_enqueue.assert_has_calls([
            call(
                "frappe_apollo.apollo.doctype.apollo_field.apollo_field.provision_a_field",
                queue="low",
                cadence_name="Cad1",
                step_name="step1",
                field_type="subject",
                account_name="Acc1",
                sender="Sender1"
            ),
            call(
                "frappe_apollo.apollo.doctype.apollo_field.apollo_field.provision_a_field",
                queue="low",
                cadence_name="Cad1",
                step_name="step1",
                field_type="message",
                account_name="Acc1",
                sender="Sender1"
            )
        ])

    @patch("frappe_apollo.integrations.apollo.ApolloClient")
    @patch("frappe.db.get_value")
    @patch("frappe.get_doc")
    def test_provision_a_field_hash(self, mock_get_doc, mock_get_value, mock_client_cls):
        # Setup mocks
        mock_client = mock_client_cls.return_value
        mock_client.create_custom_field.return_value = {"typed_custom_fields": [{"id": "apollo_123"}]}

        mock_cadence = MagicMock()
        mock_cadence.name = "Cad1"
        
        mock_apollo_id_row = MagicMock()
        mock_apollo_id_row.status = "Active"
        mock_apollo_id_row.account = "Acc1"
        mock_apollo_id_row.sender = "Sender1"
        mock_apollo_id_row.apollo_id = "seq123"
        
        mock_step = MagicMock()
        mock_step.name = "step1"
        mock_step.subject_field = "old"

        def mock_get_side_effect(k, d=[]):
            if k == "apollo_ids": return [mock_apollo_id_row]
            if k == "cadence_schedules": return [mock_step]
            return d
            
        mock_cadence.get.side_effect = mock_get_side_effect

        def mock_get_doc_side_effect(doctype, *args, **kwargs):
            if doctype == "Cadence":
                return mock_cadence
            if doctype == "Apollo Field" and args and isinstance(args[0], str):
                raise DoesNotExistError()
            elif isinstance(doctype, dict) and doctype.get("doctype") == "Apollo Field":
                doc = MagicMock()
                doc.name = "new_field"
                doc.get.return_value = [] # apollo_ids
                doc.insert.return_value = doc
                doc.label = "lbl1"
                doc.field_type = "string"
                return doc
            return MagicMock()
            
        mock_get_doc.side_effect = mock_get_doc_side_effect
        mock_get_value.side_effect = lambda dt, name, field: 1 if dt == "Cadence Provider" else "Authorized"
        
        provision_a_field("Cad1", "step1", "subject", "Acc1", "Sender1")
        
        expected_hash = hashlib.md5("Cad1_step1_subject".encode()).hexdigest()[:10]
        
        # Verify db_set was called with the new field name
        self.assertEqual(mock_step.subject_field, "new_field")
        mock_cadence.save.assert_called_once()

    @patch("frappe_apollo.integrations.apollo.ApolloClient")
    @patch("frappe.db.get_value")
    @patch("frappe.get_doc")
    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_provision_a_field_suspends(self, mock_wait, mock_get_doc, mock_get_value, mock_client_cls):
        mock_cadence = MagicMock()
        mock_cadence.name = "Cad1"
        
        mock_apollo_id_row = MagicMock()
        mock_apollo_id_row.status = "Active"
        mock_apollo_id_row.account = "Acc1"
        mock_apollo_id_row.sender = "Sender1"
        mock_apollo_id_row.apollo_id = None
        
        mock_step = MagicMock()
        mock_step.name = "step1"

        def mock_get_side_effect(k, d=[]):
            if k == "apollo_ids": return [mock_apollo_id_row]
            if k == "cadence_schedules": return [mock_step]
            return d
            
        mock_cadence.get.side_effect = mock_get_side_effect
        mock_get_doc.return_value = mock_cadence
        
        mock_get_value.side_effect = lambda dt, name, field: 1 if dt == "Cadence Provider" else "Authorized"
        
        # Make wait_for_event raise SuspendJob
        mock_wait.side_effect = SuspendJob("some_key")
        
        with self.assertRaises(SuspendJob):
            provision_a_field("Cad1", "step1", "subject", "Acc1", "Sender1")
            
        mock_wait.assert_called_once()

    @patch("frappe_apollo.integrations.apollo.ApolloClient")
    @patch("frappe.db.get_value")
    @patch("frappe.get_doc")
    @patch("frappe.log_error")
    def test_provision_a_field_re_raises_exception(self, mock_log_error, mock_get_doc, mock_get_value, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.create_custom_field.side_effect = Exception("API custom field error")

        mock_cadence = MagicMock()
        mock_cadence.name = "Cad1"

        mock_apollo_id_row = MagicMock()
        mock_apollo_id_row.status = "Active"
        mock_apollo_id_row.account = "Acc1"
        mock_apollo_id_row.sender = "Sender1"
        mock_apollo_id_row.apollo_id = "seq123"

        mock_step = MagicMock()
        mock_step.name = "step1"
        mock_step.subject_field = "old"

        def mock_get_side_effect(k, d=[]):
            if k == "apollo_ids": return [mock_apollo_id_row]
            if k == "cadence_schedules": return [mock_step]
            return d
        mock_cadence.get.side_effect = mock_get_side_effect

        def mock_get_doc_side_effect(doctype, *args, **kwargs):
            if doctype == "Cadence":
                return mock_cadence
            if doctype == "Apollo Field" and args and isinstance(args[0], str):
                raise DoesNotExistError()
            elif isinstance(doctype, dict) and doctype.get("doctype") == "Apollo Field":
                doc = MagicMock()
                doc.name = "new_field"
                doc.get.return_value = []
                doc.insert.return_value = doc
                doc.label = "lbl1"
                doc.field_type = "string"
                return doc
            return MagicMock()

        mock_get_doc.side_effect = mock_get_doc_side_effect
        mock_get_value.side_effect = lambda dt, name, field: 1 if dt == "Cadence Provider" else "Authorized"

        with self.assertRaises(Exception):
            provision_a_field("Cad1", "step1", "subject", "Acc1", "Sender1")

        mock_log_error.assert_called_once_with(title="Apollo Field Creation Failed", message="API custom field error")

import frappe
from frappe.tests import IntegrationTestCase
from frappe_controller.utils.controller import SuspendJob
from unittest.mock import patch, MagicMock

from frappe_apollo.apollo.doctype.apollo_field.apollo_field import provision_a_field
from frappe_apollo.apollo.doctype.crm_lead.crm_lead import create_a_contact, update_a_contact
from frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence import _assign_contact_to_sequence
from frappe_apollo.apollo.doctype.cadence_provider.cadence_provider import on_update as cadence_provider_on_update

class TestProviderEnablementDefects(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not frappe.db.exists("Cadence Provider", "Apollo"):
            frappe.get_doc({
                "doctype": "Cadence Provider",
                "provider_name": "Apollo",
                "enabled": 0
            }).insert(ignore_permissions=True)
        else:
            frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 0)

        if not frappe.db.exists("Apollo Account", "TestDefectAccount"):
            frappe.get_doc({
                "doctype": "Apollo Account",
                "account_name": "TestDefectAccount",
                "status": "Authorized",
                "api_key": "test_key"
            }).insert(ignore_permissions=True)

        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    @patch("frappe.get_doc")
    @patch("frappe.db.get_value")
    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_field_provisioning_listens_to_provider_enablement_event(self, mock_wait, mock_get_value, mock_get_doc):
        # Setup mocks: Provider disabled
        mock_get_value.side_effect = lambda dt, name_or_filters=None, fieldname=None, *args, **kwargs: (
            0 if dt == "Cadence Provider" else "Authorized"
        )
        mock_cadence = MagicMock()
        mock_cadence.name = "TestCadence"
        mock_cadence.modified = "2024-01-01"
        mock_row = MagicMock()
        mock_row.account = "TestDefectAccount"
        mock_row.sender = "sender@example.com"
        mock_row.apollo_id = "seq_123"
        mock_step = MagicMock()
        mock_step.name = "Step1"

        def cadence_get(key, default=[]):
            if key == "apollo_ids": return [mock_row]
            if key == "cadence_schedules": return [mock_step]
            return default

        mock_cadence.get.side_effect = cadence_get
        mock_get_doc.return_value = mock_cadence

        # Execute
        provision_a_field("TestCadence", "Step1", "subject", "TestDefectAccount", "sender@example.com")

        # Verify event key: Must listen to Cadence Provider event when disabled
        mock_wait.assert_called()
        event_key = mock_wait.call_args[0][0] if mock_wait.call_args[0] else mock_wait.call_args[1].get("event_key")
        self.assertEqual(event_key, "doc:Cadence Provider:Apollo:on_update")
        self.assertEqual(mock_wait.call_args[1].get("condition"), "argument.get('enabled') == 1")

    @patch("frappe.db.get_value")
    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_contact_creation_registers_provider_event_listener(self, mock_wait, mock_get_value):
        # Setup mocks: Provider disabled
        mock_get_value.side_effect = lambda dt, name_or_filters=None, fieldname=None, *args, **kwargs: (
            0 if dt == "Cadence Provider" else "Authorized"
        )
        mock_wait.side_effect = SuspendJob("suspended")

        # Execute
        with self.assertRaises(SuspendJob):
            create_a_contact("Lead1", "TestDefectAccount")

        # Assert: wait_for_event must be called instead of bare SuspendJob exception
        mock_wait.assert_called_once_with(
            event_key="doc:Cadence Provider:Apollo:on_update",
            condition="argument.get('enabled') == 1"
        )

    @patch("frappe.db.get_value")
    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_contact_update_registers_provider_event_listener(self, mock_wait, mock_get_value):
        # Setup mocks: Provider disabled
        mock_get_value.side_effect = lambda dt, name_or_filters=None, fieldname=None, *args, **kwargs: (
            0 if dt == "Cadence Provider" else "Authorized"
        )
        mock_wait.side_effect = SuspendJob("suspended")

        # Execute
        with self.assertRaises(SuspendJob):
            update_a_contact("Lead1", "TestDefectAccount")

        # Assert: wait_for_event must be called instead of bare SuspendJob exception
        mock_wait.assert_called_once_with(
            event_key="doc:Cadence Provider:Apollo:on_update",
            condition="argument.get('enabled') == 1"
        )

    @patch("frappe.get_doc")
    @patch("frappe.db.get_value")
    @patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event")
    def test_mcc_sequence_assignment_suspends_when_provider_disabled(self, mock_wait, mock_get_value, mock_get_doc):
        # Setup mocks: Provider disabled
        mock_get_value.side_effect = lambda dt, name_or_filters=None, fieldname=None, *args, **kwargs: (
            0 if dt == "Cadence Provider" else "Authorized"
        )
        mock_wait.side_effect = SuspendJob("suspended")

        mock_mcc = MagicMock()
        mock_mcc.name = "MCC-1"
        mock_mcc.status = "Scheduled"
        mock_mcc.apollo_account = "TestDefectAccount"
        mock_mcc.apollo_sequence_id = "seq_123"
        mock_get_doc.return_value = mock_mcc

        # Execute
        with self.assertRaises(SuspendJob):
            _assign_contact_to_sequence("MCC-1")

        # Assert: wait_for_event must be registered for Cadence Provider enablement
        mock_wait.assert_called_once_with(
            event_key="doc:Cadence Provider:Apollo:on_update",
            condition="argument.get('enabled') == 1"
        )

    @patch("frappe.get_all")
    @patch("frappe_controller.utils.background_jobs.enqueue")
    def test_cadence_provider_on_update_enqueues_valid_method_path(self, mock_enqueue, mock_get_all):
        mock_get_all.return_value = ["Cadence1"]
        mock_provider = MagicMock()
        mock_provider.name = "Apollo"

        # Execute hook
        cadence_provider_on_update(mock_provider)

        # Assert: method path must match actual function path
        mock_enqueue.assert_called_once()
        method_path = mock_enqueue.call_args[1].get("method") if mock_enqueue.call_args[1].get("method") else mock_enqueue.call_args[0][0]
        self.assertEqual(
            method_path,
            "frappe_apollo.apollo.doctype.apollo_field.apollo_field.enqueue_provision_cadence_fields"
        )

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe_controller.utils.controller import SuspendJob

from frappe_apollo.apollo.doctype.apollo_field.apollo_field import provision_a_field
from frappe_apollo.apollo.doctype.cadence_provider.cadence_provider import (
    on_update as cadence_provider_on_update,
)
from frappe_apollo.apollo.doctype.crm_lead.crm_lead import create_a_contact, update_a_contact
from frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence import (
    add_contact_to_sequence,
)


class TestCadenceProvider(IntegrationTestCase):
    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
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

    def tearDown(self):
        frappe.db.rollback()
        super().tearDown()

    @patch("frappe.get_doc")
    @patch("frappe.db.get_value")
    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_field_provisioning_listens_to_provider_enablement_event(self, mock_wait, mock_get_value, mock_get_doc):
        mock_get_value.side_effect = lambda dt, name_or_filters=None, fieldname=None, *args, **kwargs: (
            0 if dt == "Cadence Provider" else "Authorized"
        )
        mock_wait.side_effect = SuspendJob("wait")
        mock_field_doc = MagicMock()
        mock_field_doc.label = "subject_1"
        mock_field_doc.field_type = "string"
        mock_get_doc.return_value = mock_field_doc

        with self.assertRaises(SuspendJob):
            provision_a_field("subject_1", "string", "TestDefectAccount")

        mock_wait.assert_called()
        event_key = mock_wait.call_args[0][0] if mock_wait.call_args[0] else mock_wait.call_args[1].get("event_key")
        self.assertEqual(event_key, "doc:Cadence Provider:Apollo:on_update")
        self.assertEqual(mock_wait.call_args[1].get("condition"), "argument.get('enabled') == 1")

    @patch("frappe.db.get_value")
    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_contact_creation_registers_provider_event_listener(self, mock_wait, mock_get_value):
        mock_get_value.side_effect = lambda dt, name_or_filters=None, fieldname=None, *args, **kwargs: (
            0 if dt == "Cadence Provider" else "Authorized"
        )
        mock_wait.side_effect = SuspendJob("suspended")

        with self.assertRaises(SuspendJob):
            create_a_contact("Lead1", "TestDefectAccount")

        mock_wait.assert_called_once_with(
            event_key="doc:Cadence Provider:Apollo:on_update",
            condition="argument.get('enabled') == 1"
        )

    @patch("frappe.db.get_value")
    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_contact_update_registers_provider_event_listener(self, mock_wait, mock_get_value):
        mock_get_value.side_effect = lambda dt, name_or_filters=None, fieldname=None, *args, **kwargs: (
            0 if dt == "Cadence Provider" else "Authorized"
        )
        mock_wait.side_effect = SuspendJob("suspended")

        with self.assertRaises(SuspendJob):
            update_a_contact("Lead1", "TestDefectAccount")

        mock_wait.assert_called_once_with(
            event_key="doc:Cadence Provider:Apollo:on_update",
            condition="argument.get('enabled') == 1"
        )

    @patch("frappe.get_doc")
    @patch("frappe.db.get_value")
    @patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event")
    def test_mcc_sequence_assignment_suspends_when_provider_disabled(self, mock_wait, mock_get_value, mock_get_doc):
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

        with self.assertRaises(SuspendJob):
            add_contact_to_sequence("MCC-1")

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

        cadence_provider_on_update(mock_provider)

        mock_enqueue.assert_called_once()
        method_path = mock_enqueue.call_args[1].get("method") if mock_enqueue.call_args[1].get("method") else mock_enqueue.call_args[0][0]
        self.assertEqual(
            method_path,
            "frappe_apollo.apollo.doctype.apollo_field.apollo_field.enqueue_provision_cadence_fields"
        )

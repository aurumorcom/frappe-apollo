from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe_controller.utils.controller import SuspendJob

from frappe_apollo.apollo.doctype.communication.communication import update_a_contact


class TestCommunicationIntegration(IntegrationTestCase):
    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    def tearDown(self):
        frappe.db.rollback()
        super().tearDown()

    @patch("frappe_apollo.apollo.doctype.communication.communication.wait_for_event", side_effect=SuspendJob("wait"))
    @patch("frappe.db.get_value")
    @patch("frappe.get_doc")
    @patch("frappe.get_all")
    def test_missing_custom_fields_raises_wait(self, mock_get_all, mock_get_doc, mock_get_value, mock_wait):
        def mock_get_value_side_effect(dt, name_or_filters=None, fieldname=None):
            if dt == "Cadence Provider": return 1
            if dt == "User Email": return "Email-Acc-1"
            return "val"
        mock_get_value.side_effect = mock_get_value_side_effect

        mock_comm = MagicMock()
        mock_comm.get.return_value = None
        mock_comm.reference_name = "mcc1"
        mock_comm.cadence_schedule = "sch1"

        mock_mcc = MagicMock()
        mock_mcc.sender = "user1"
        mock_mcc.recipient = "lead1"
        mock_mcc.cadence_name = "cad1"
        mock_mcc.apollo_account = "acc1"
        mock_mcc.apollo_sequence_id = "seq1"

        mock_account = MagicMock(status="Authorized")
        mock_provider = MagicMock()
        mock_provider.get.return_value = [MagicMock(channel="Email")]

        mock_cadence = MagicMock()
        mock_sch = MagicMock(reference_doctype="Email Template", channel="Email")
        mock_sch.name = "sch1"
        mock_cadence.get.side_effect = lambda k, d=[]: [mock_sch] if k == "cadence_schedules" else d

        def mock_get_doc_side_effect(*args, **kwargs):
            doctype = args[0] if args and isinstance(args[0], str) else (args[0].get('doctype') if args else kwargs.get('doctype'))
            if doctype == "Communication": return mock_comm
            if doctype == "Multi Channel Cadence": return mock_mcc
            if doctype == "Apollo Account": return mock_account
            if doctype == "Cadence Provider": return mock_provider
            if doctype == "Cadence": return mock_cadence
            if doctype == "Apollo Field": raise frappe.DoesNotExistError
            return MagicMock()

        mock_get_doc.side_effect = mock_get_doc_side_effect
        mock_get_all.side_effect = lambda *args, **kwargs: [frappe._dict({"apollo_id": "pid1"})] if args[0] == "CRM Lead Apollo ID" else []

        with self.assertRaises(SuspendJob):
            update_a_contact("comm1")

    @patch("frappe_apollo.apollo.doctype.communication.communication.wait_for_event", side_effect=SuspendJob("wait"))
    @patch("frappe.db.get_value")
    @patch("frappe.get_doc")
    @patch("frappe.get_all")
    @patch("frappe_apollo.integrations.apollo.ApolloClient")
    def test_valid_sync(self, mock_client_class, mock_get_all, mock_get_doc, mock_get_value, mock_wait):
        def mock_get_value_side_effect(dt, name_or_filters=None, fieldname=None):
            if dt == "Cadence Provider": return 1
            if dt == "User Email": return "Email-Acc-1"
            return "val"
        mock_get_value.side_effect = mock_get_value_side_effect

        mock_comm = MagicMock()
        mock_comm.get.return_value = None
        mock_comm.reference_name = "mcc1"
        mock_comm.cadence_schedule = "sch1"
        mock_comm.subject = "Test Sub"
        mock_comm.content = "Test Content"

        mock_mcc = MagicMock()
        mock_mcc.sender = "user1"
        mock_mcc.recipient = "lead1"
        mock_mcc.cadence_name = "cad1"
        mock_mcc.apollo_account = "acc1"
        mock_mcc.apollo_sequence_id = "seq1"

        mock_account = MagicMock(status="Authorized")
        mock_provider = MagicMock()
        mock_provider.get.return_value = [MagicMock(channel="Email")]

        mock_cadence = MagicMock()
        mock_sch = MagicMock(reference_doctype="Email Template", channel="Email")
        mock_sch.name = "sch1"
        mock_cadence.get.side_effect = lambda k, d=[]: [mock_sch] if k == "cadence_schedules" else d

        mock_field_1 = MagicMock()
        mock_row1 = MagicMock(account="acc1", apollo_id="af1")
        mock_field_1.get.return_value = [mock_row1]

        mock_field_2 = MagicMock()
        mock_row2 = MagicMock(account="acc1", apollo_id="af2")
        mock_field_2.get.return_value = [mock_row2]

        def mock_get_doc_side_effect(*args, **kwargs):
            doctype = args[0] if args and isinstance(args[0], str) else (args[0].get('doctype') if args else kwargs.get('doctype'))
            name = args[1] if len(args) > 1 else kwargs.get('name')
            if doctype == "Communication": return mock_comm
            if doctype == "Multi Channel Cadence": return mock_mcc
            if doctype == "Apollo Account": return mock_account
            if doctype == "Cadence Provider": return mock_provider
            if doctype == "Cadence": return mock_cadence
            if doctype == "Apollo Field":
                if name == "subject_1": return mock_field_1
                if name == "body_1": return mock_field_2
            return MagicMock()

        mock_get_doc.side_effect = mock_get_doc_side_effect
        mock_get_all.side_effect = lambda *args, **kwargs: [frappe._dict({"apollo_id": "pid1"})] if args[0] == "CRM Lead Apollo ID" else []

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        update_a_contact("comm1")

        mock_client.update_contact.assert_called_once_with("pid1", {"af1": "Test Sub", "af2": "Test Content"})
        mock_comm.db_set.assert_any_call("apollo_status", "Scheduled")

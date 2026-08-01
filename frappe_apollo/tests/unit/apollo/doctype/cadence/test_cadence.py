import frappe
from frappe.tests import UnitTestCase
from frappe_apollo.apollo.doctype.cadence.cadence import _provision_sequence, _get_sequence_steps, on_update
from unittest.mock import patch, MagicMock, call
from frappe_controller.utils.controller import SuspendJob

class TestCadenceProvisioning(UnitTestCase):
    @patch("frappe_apollo.apollo.doctype.cadence.cadence.enqueue")
    @patch("frappe_apollo.apollo.doctype.cadence.cadence._get_sequence_steps")
    @patch("frappe.get_attr")
    def test_on_update_enqueues_granular_jobs(self, mock_get_attr, mock_get_steps, mock_enqueue):
        mock_get_steps.return_value = [{"step": 1}]
        
        doc = MagicMock()
        doc.name = "Test Cadence"
        doc.has_value_changed.return_value = False
        
        row1 = MagicMock()
        row1.account = "Acc1"
        row1.sender = "Sender1"
        row2 = MagicMock()
        row2.account = "Acc2"
        row2.sender = "Sender2"
        
        doc.get.return_value = [row1, row2]
        
        mock_enqueue_field = MagicMock()
        mock_get_attr.return_value = mock_enqueue_field
        
        on_update(doc)
        
        # Verify granular jobs were queued for each apollo_id
        mock_enqueue.assert_has_calls([
            call(
                "frappe_apollo.apollo.doctype.cadence.cadence._provision_sequence",
                queue="low",
                cadence_name="Test Cadence",
                account_name="Acc1",
                sender="Sender1",
                emailer_steps=[{"step": 1}]
            ),
            call(
                "frappe_apollo.apollo.doctype.cadence.cadence._provision_sequence",
                queue="low",
                cadence_name="Test Cadence",
                account_name="Acc2",
                sender="Sender2",
                emailer_steps=[{"step": 1}]
            )
        ])
        
        mock_enqueue_field.assert_has_calls([
            call("Test Cadence", "Acc1", "Sender1"),
            call("Test Cadence", "Acc2", "Sender2")
        ])

    @patch("frappe_apollo.apollo.doctype.cadence.cadence.ApolloClient")
    @patch("frappe.get_doc")
    @patch("frappe.db.get_value")
    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_provision_sequence_waits_for_provider_enablement(self, mock_wait_for_event, mock_db_get_value, mock_get_doc, mock_client_cls):
        mock_cadence = MagicMock()
        mock_cadence.cadence_name = "Test Cadence"
        mock_cadence.modified = "2024-01-01"
        
        row1 = MagicMock()
        row1.account = "Acc1"
        row1.sender = "Sender1"
        row1.apollo_id = None
        
        mock_cadence.get.return_value = [row1]
        mock_get_doc.return_value = mock_cadence
        
        # Provider disabled
        mock_db_get_value.side_effect = lambda dt, name, field: 0 if dt == "Cadence Provider" else "Authorized"
        
        def side_effect_reload():
            mock_cadence.get.return_value = []
        mock_cadence.reload.side_effect = side_effect_reload
        
        _provision_sequence("Cad1", "Acc1", "Sender1", emailer_steps=[])
        
        mock_wait_for_event.assert_called_once_with(
            "doc:Cadence Provider:Apollo:on_update",
            condition="argument.get('enabled') == 1",
            consider_events_since="2024-01-01"
        )
        mock_cadence.reload.assert_called_once()
        mock_client_cls.assert_not_called()

    @patch("frappe_apollo.apollo.doctype.cadence.cadence.ApolloClient")
    @patch("frappe.get_doc")
    @patch("frappe.db.get_value")
    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_provision_sequence_waits_for_account_authorization(self, mock_wait_for_event, mock_db_get_value, mock_get_doc, mock_client_cls):
        mock_cadence = MagicMock()
        mock_cadence.cadence_name = "Test Cadence"
        mock_cadence.modified = "2024-01-01"
        
        row1 = MagicMock()
        row1.account = "Acc1"
        row1.sender = "Sender1"
        row1.apollo_id = None
        
        mock_cadence.get.return_value = [row1]
        mock_get_doc.return_value = mock_cadence
        
        # Provider enabled, Account unauthorized
        mock_db_get_value.side_effect = lambda dt, name, field: 1 if dt == "Cadence Provider" else "Unauthorized"
        
        def side_effect_reload():
            mock_cadence.get.return_value = []
        mock_cadence.reload.side_effect = side_effect_reload
        
        _provision_sequence("Cad1", "Acc1", "Sender1", emailer_steps=[])
        
        mock_wait_for_event.assert_called_once_with(
            "doc:Apollo Account:Acc1:on_update",
            condition="doc.status == 'Authorized'",
            consider_events_since="2024-01-01"
        )
        mock_cadence.reload.assert_called_once()
        mock_client_cls.assert_not_called()

    @patch("frappe_apollo.apollo.doctype.cadence.cadence.ApolloClient")
    @patch("frappe.get_doc")
    @patch("frappe.db.get_value")
    def test_provision_sequence_creates_new(self, mock_db_get_value, mock_get_doc, mock_client_cls):
        mock_cadence = MagicMock()
        mock_cadence.cadence_name = "Test Cadence"
        
        row1 = MagicMock()
        row1.account = "Acc1"
        row1.sender = "Sender1"
        row1.apollo_id = None
        row1.doctype = "Cadence Apollo ID"
        row1.name = "row1"
        
        mock_cadence.get.return_value = [row1]
        mock_get_doc.return_value = mock_cadence
        
        # Authorized
        mock_db_get_value.side_effect = lambda dt, name, field: 1 if dt == "Cadence Provider" else "Authorized"
        
        mock_client = mock_client_cls.return_value
        mock_client.create_sequence.return_value = "seq_123"
        
        _provision_sequence("Cad1", "Acc1", "Sender1", emailer_steps=[])
        
        mock_client.create_sequence.assert_called_once_with(
            name="Test Cadence - Sender1",
            permissions="team_can_use",
            active=True,
            emailer_steps=[]
        )
        self.assertEqual(row1.apollo_id, "seq_123")
        mock_cadence.save.assert_called_once()

    @patch("frappe.get_doc")
    def test_get_sequence_steps(self, mock_get_doc):
        mock_cadence = MagicMock()
        mock_cadence.name = "Cad1"
        
        mock_sch1 = MagicMock()
        mock_sch1.send_after_days = 2
        mock_sch1.reference_doctype = "Email Template"
        mock_sch1.name = "step1"
        mock_sch1.get.side_effect = lambda k: "lbl_subject_step1" if k == "subject_field" else "lbl_message_step1"
        
        mock_sch2 = MagicMock()
        mock_sch2.send_after_days = 3
        mock_sch2.reference_doctype = "Other Channel"
        mock_sch2.name = "step2"
        
        mock_sch3 = MagicMock()
        mock_sch3.send_after_days = 1
        mock_sch3.reference_doctype = "Email Template"
        mock_sch3.name = "step3"
        mock_sch3.get.side_effect = lambda k: "lbl_subject_step3" if k == "subject_field" else "lbl_message_step3"
        
        mock_cadence.cadence_schedules = [mock_sch1, mock_sch2, mock_sch3]
        mock_cadence.get.side_effect = lambda k: mock_cadence.cadence_schedules if k == "cadence_schedules" else []
        
        mock_get_doc.return_value = mock_cadence
        
        emailer_steps = _get_sequence_steps("Cad1")
        
        expected_emailer_steps = [
            {
                "type": "auto_email",
                "wait_time": 2,
                "wait_mode": "day",
                "emailer_touches": [{
                    "type": "new_thread",
                    "status": "approved",
                    "include_signature": True,
                    "emailer_template": {
                        "subject": "{{lbl_subject_step1}}",
                        "body_html": "{{lbl_message_step1}}"
                    }
                }]
            },
            {
                "type": "auto_email",
                "wait_time": 4, # 3 from Other Channel + 1 from Email Template
                "wait_mode": "day",
                "emailer_touches": [{
                    "type": "new_thread",
                    "status": "approved",
                    "include_signature": True,
                    "emailer_template": {
                        "subject": "{{lbl_subject_step3}}",
                        "body_html": "{{lbl_message_step3}}"
                    }
                }]
            }
        ]
        
        self.assertEqual(emailer_steps, expected_emailer_steps)

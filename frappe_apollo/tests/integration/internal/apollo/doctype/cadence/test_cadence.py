import frappe
from frappe.tests import IntegrationTestCase
from frappe_controller.utils.controller import SuspendJob
from unittest.mock import patch, MagicMock

from frappe_apollo.apollo.doctype.cadence.cadence import on_update, _provision_sequence, update_sequence, archive_sequence, _get_sequence_steps
from frappe_apollo.apollo.doctype.apollo_field.apollo_field import provision_a_field
from frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence import before_save, on_update as mcc_on_update, _assign_contact_to_sequence
from frappe_apollo.apollo.doctype.crm_lead.crm_lead import _create_a_contact, create_a_contact, update_a_contact

class TestApolloLifecycleE2E(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Setup provider
        if not frappe.db.exists("Cadence Provider", "Apollo"):
            frappe.get_doc({
                "doctype": "Cadence Provider",
                "provider_name": "Apollo",
                "enabled": 0
            }).insert(ignore_permissions=True)
        else:
            frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 0)
            
        # Setup accounts
        if not frappe.db.exists("Apollo Account", "TestAccount1"):
            frappe.get_doc({
                "doctype": "Apollo Account",
                "account_name": "TestAccount1",
                "status": "Unauthorized",
                "api_key": "test_key_1"
            }).insert(ignore_permissions=True)
        else:
            frappe.db.set_value("Apollo Account", "TestAccount1", "status", "Unauthorized")

        if not frappe.db.exists("Apollo Account", "TestAccount2"):
            frappe.get_doc({
                "doctype": "Apollo Account",
                "account_name": "TestAccount2",
                "status": "Authorized",
                "api_key": "test_key_2"
            }).insert(ignore_permissions=True)
        else:
            frappe.db.set_value("Apollo Account", "TestAccount2", "status", "Authorized")
            
        # Setup user and sender
        if not frappe.db.exists("User", "test_sender@example.com"):
            frappe.get_doc({
                "doctype": "User",
                "email": "test_sender@example.com",
                "first_name": "Test",
                "send_welcome_email": 0
            }).insert(ignore_permissions=True)
            
        # Setup email account
        if not frappe.db.exists("Email Account", "TestEmailAccount1"):
            frappe.get_doc({
                "doctype": "Email Account",
                "email_account_name": "TestEmailAccount1",
                "email_id": "test_sender@example.com",
                "apollo_ids": [{"account": "TestAccount1", "apollo_id": "mailbox_1"}],
                "append_to": "Communication"
            }).insert(ignore_permissions=True)

        if not frappe.db.exists("User Email", {"parent": "test_sender@example.com", "email_account": "TestEmailAccount1"}):
            user = frappe.get_doc("User", "test_sender@example.com")
            user.append("user_emails", {"email_account": "TestEmailAccount1", "email_id": "test_sender@example.com"})
            user.save(ignore_permissions=True)

        # Setup CRM Lead
        lead_id = frappe.db.get_value("CRM Lead", {"email": "lead1@example.com"}, "name")
        if not lead_id:
            lead = frappe.get_doc({
                "doctype": "CRM Lead",
                "first_name": "Lead",
                "last_name": "1",
                "email": "lead1@example.com",
                "apollo_ids": [{"account": "TestAccount1", "apollo_id": ""}]
            }).insert(ignore_permissions=True, ignore_mandatory=True)
            cls.lead_id = lead.name
        else:
            cls.lead_id = lead_id

        if not frappe.db.exists("Email Template", "Test Template"):
            frappe.get_doc({
                "doctype": "Email Template",
                "name": "Test Template",
                "subject": "Test Subject",
                "response": "Test Response"
            }).insert(ignore_permissions=True)

        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        frappe.db.delete("Multi Channel Cadence")
        frappe.db.delete("Cadence")
        frappe.db.delete("Apollo Field")
        frappe.db.delete("Communication", {"reference_doctype": "Multi Channel Cadence"})
        frappe.db.commit()
        frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 0)
        frappe.db.set_value("Apollo Account", "TestAccount1", "status", "Unauthorized")
        frappe.db.set_value("Apollo Account", "TestAccount2", "status", "Authorized")

    def tearDown(self):
        frappe.db.delete("Multi Channel Cadence")
        frappe.db.delete("Cadence")
        frappe.db.delete("Apollo Field")
        frappe.db.delete("Communication", {"reference_doctype": "Multi Channel Cadence"})
        frappe.db.commit()
        super().tearDown()

    def _create_test_cadence(self):
        cadence = frappe.get_doc({
            "doctype": "Cadence",
            "cadence_name": frappe.generate_hash(length=10),
            "enabled": 1,
            "cadence_schedules": [{
                "reference_doctype": "Email Template",
                "reference_name": "Test Template",
                "send_after_days": 1
            }],
            "users": [{"user": "test_sender@example.com"}]
        }).insert(ignore_permissions=True, ignore_mandatory=True)
        return cadence

    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_provision_sequence_suspension_provider_disabled(self, mock_wait):
        cadence = self._create_test_cadence()
        cadence.append("apollo_ids", {"account": "TestAccount1", "sender": "test_sender@example.com", "status": "Active"})
        cadence.save(ignore_permissions=True)

        frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 0)
        mock_wait.side_effect = SuspendJob("wait")

        with self.assertRaises(SuspendJob):
            _provision_sequence(cadence.name, "TestAccount1", "test_sender@example.com", emailer_steps=[])

        mock_wait.assert_called_once()
        self.assertEqual(mock_wait.call_args[0][0], "doc:Cadence Provider:Apollo:on_update")
        self.assertEqual(mock_wait.call_args[1]["condition"], "argument.get('enabled') == 1")

    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_provision_sequence_suspension_account_unauthorized(self, mock_wait):
        cadence = self._create_test_cadence()
        cadence.append("apollo_ids", {"account": "TestAccount1", "sender": "test_sender@example.com", "status": "Active"})
        cadence.save(ignore_permissions=True)

        frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 1)
        frappe.db.set_value("Apollo Account", "TestAccount1", "status", "Unauthorized")
        mock_wait.side_effect = SuspendJob("wait")

        with self.assertRaises(SuspendJob):
            _provision_sequence(cadence.name, "TestAccount1", "test_sender@example.com", emailer_steps=[])

        mock_wait.assert_called_once()
        self.assertEqual(mock_wait.call_args[0][0], "doc:Apollo Account:TestAccount1:on_update")
        self.assertEqual(mock_wait.call_args[1]["condition"], "argument.get('status') == 'Authorized'")

    @patch("frappe_apollo.apollo.doctype.cadence.cadence.ApolloClient")
    def test_provision_sequence_creates_sequence_and_saves_doc(self, mock_client_cls):
        cadence = self._create_test_cadence()
        cadence.append("apollo_ids", {"account": "TestAccount1", "sender": "test_sender@example.com", "status": "Active"})
        cadence.save(ignore_permissions=True)

        frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 1)
        frappe.db.set_value("Apollo Account", "TestAccount1", "status", "Authorized")

        mock_client = mock_client_cls.return_value
        mock_client.create_sequence.return_value = "seq_apollo_999"

        _provision_sequence(cadence.name, "TestAccount1", "test_sender@example.com", emailer_steps=[])

        mock_client.create_sequence.assert_called_once_with(
            name=f"{cadence.cadence_name} - test_sender@example.com",
            permissions="team_can_use",
            active=True,
            emailer_steps=[]
        )

        cadence.reload()
        row = next(r for r in cadence.apollo_ids if r.account == "TestAccount1" and r.sender == "test_sender@example.com")
        self.assertEqual(row.apollo_id, "seq_apollo_999")

    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_provision_fields_suspends_until_sequence_id_available(self, mock_wait):
        cadence = self._create_test_cadence()
        cadence.append("apollo_ids", {"account": "TestAccount1", "sender": "test_sender@example.com", "status": "Active", "apollo_id": ""})
        cadence.save(ignore_permissions=True)

        frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 1)
        frappe.db.set_value("Apollo Account", "TestAccount1", "status", "Authorized")

        step_name = cadence.cadence_schedules[0].name
        mock_wait.side_effect = SuspendJob("wait")

        with self.assertRaises(SuspendJob):
            provision_a_field(cadence.name, step_name, "subject", "TestAccount1", "test_sender@example.com")

        mock_wait.assert_called_once()
        self.assertEqual(mock_wait.call_args[0][0], f"doc:Cadence:{cadence.name}:on_update")
        self.assertEqual(mock_wait.call_args[1]["condition"], f"any(r.get('account') == 'TestAccount1' and r.get('sender') == 'test_sender@example.com' and r.get('apollo_id') for r in argument.get('apollo_ids', []))")

    @patch("frappe_apollo.integrations.apollo.ApolloClient")
    def test_provision_fields_creates_apollo_fields_and_attaches_to_steps(self, mock_client_cls):
        cadence = self._create_test_cadence()
        cadence.append("apollo_ids", {"account": "TestAccount1", "sender": "test_sender@example.com", "status": "Active", "apollo_id": "seq_apollo_999"})
        cadence.save(ignore_permissions=True)

        frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 1)
        frappe.db.set_value("Apollo Account", "TestAccount1", "status", "Authorized")

        mock_client = mock_client_cls.return_value
        mock_client.create_custom_field.return_value = {"typed_custom_fields": [{"id": "custom_field_555"}]}

        step_name = cadence.cadence_schedules[0].name
        provision_a_field(cadence.name, step_name, "subject", "TestAccount1", "test_sender@example.com")
        provision_a_field(cadence.name, step_name, "message", "TestAccount1", "test_sender@example.com")

        cadence.reload()
        step = cadence.cadence_schedules[0]
        self.assertTrue(step.subject_field)
        self.assertTrue(step.message_field)

        field_doc = frappe.get_doc("Apollo Field", step.subject_field)
        self.assertTrue(any(r.account == "TestAccount1" and r.apollo_id == "custom_field_555" for r in field_doc.apollo_ids))

    @patch("frappe_apollo.apollo.doctype.cadence.cadence.ApolloClient")
    def test_provision_sequence_updates_steps_after_fields_attached(self, mock_client_cls):
        cadence = self._create_test_cadence()
        cadence.append("apollo_ids", {"account": "TestAccount1", "sender": "test_sender@example.com", "status": "Active", "apollo_id": "seq_apollo_999"})
        cadence.save(ignore_permissions=True)

        frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 1)
        frappe.db.set_value("Apollo Account", "TestAccount1", "status", "Authorized")

        mock_client = mock_client_cls.return_value
        mock_client.create_custom_field.return_value = {"typed_custom_fields": [{"id": "custom_field_555"}]}

        step_name = cadence.cadence_schedules[0].name
        with patch("frappe_apollo.integrations.apollo.ApolloClient") as inner_client_cls:
            inner_client = inner_client_cls.return_value
            inner_client.create_custom_field.return_value = {"typed_custom_fields": [{"id": "custom_field_555"}]}
            provision_a_field(cadence.name, step_name, "subject", "TestAccount1", "test_sender@example.com")
            provision_a_field(cadence.name, step_name, "message", "TestAccount1", "test_sender@example.com")

        steps = _get_sequence_steps(cadence.name)
        self.assertEqual(len(steps), 1)

        _provision_sequence(cadence.name, "TestAccount1", "test_sender@example.com", emailer_steps=steps)

        mock_client.update_sequence.assert_called_once_with(
            "seq_apollo_999",
            {"emailer_steps": [{
                "type": "auto_email",
                "wait_time": 1,
                "wait_mode": "day",
                "emailer_touches": [{
                    "type": "new_thread",
                    "status": "approved",
                    "include_signature": True,
                    "emailer_template": {
                        "subject": f"{{{{{steps[0]['emailer_touches'][0]['emailer_template']['subject'][2:-2]}}}}}",
                        "body_html": f"{{{{{steps[0]['emailer_touches'][0]['emailer_template']['body_html'][2:-2]}}}}}"
                    }
                }],
                "position": 1
            }]}
        )

    @patch("frappe_apollo.apollo.doctype.cadence.cadence.ApolloClient")
    def test_sequence_enable_disable_and_archive_lifecycle(self, mock_client_cls):
        cadence = self._create_test_cadence()
        cadence.append("apollo_ids", {"account": "TestAccount1", "sender": "test_sender@example.com", "status": "Active", "apollo_id": "seq_apollo_999"})
        cadence.save(ignore_permissions=True)

        mock_client = mock_client_cls.return_value

        # Test disable
        update_sequence(cadence.name, "TestAccount1", is_enabled=False)
        mock_client.abort_sequence.assert_called_once_with("seq_apollo_999")

        # Test enable
        update_sequence(cadence.name, "TestAccount1", is_enabled=True)
        mock_client.approve_sequence.assert_called_once_with("seq_apollo_999")

        # Test archive
        archive_sequence("TestAccount1", "seq_apollo_999")
        mock_client.archive_sequence.assert_called_once_with("seq_apollo_999")

    def test_mcc_draft_reassignment(self):
        cadence = self._create_test_cadence()
        cadence.append("apollo_ids", {"account": "TestAccount1", "sender": "test_sender@example.com", "status": "Active", "apollo_id": "seq_test_1"})
        cadence.append("apollo_ids", {"account": "TestAccount2", "sender": "test_sender@example.com", "status": "Active", "apollo_id": "seq_test_2"})
        cadence.save(ignore_permissions=True)

        mcc = frappe.get_doc({
            "doctype": "Multi Channel Cadence",
            "provider": [{"cadence_provider": "Apollo"}],
            "sender": "test_sender@example.com",
            "recipient": self.lead_id,
            "cadence_name": cadence.name,
            "cadence": cadence.name,
            "status": "Draft"
        })
        
        before_save(mcc)
        mcc.apollo_account = "TestAccount1"
        mcc.apollo_sequence_id = "seq_test_1"
        
        cadence.apollo_ids = [row for row in cadence.apollo_ids if row.account != "TestAccount1"]
        cadence.save(ignore_permissions=True)
        
        before_save(mcc)
        self.assertEqual(mcc.apollo_account, "TestAccount2")

    @patch("frappe_controller.utils.controller.wait_for_event")
    @patch("frappe.enqueue")
    def test_mcc_contact_creation(self, mock_enqueue, mock_lead_wait):
        cadence = self._create_test_cadence()
        mcc = frappe.get_doc({
            "doctype": "Multi Channel Cadence",
            "provider": [{"cadence_provider": "Apollo"}],
            "sender": "test_sender@example.com",
            "recipient": self.lead_id,
            "cadence_name": cadence.name,
            "cadence": cadence.name,
            "status": "Scheduled",
            "apollo_account": "TestAccount1"
        }).insert(ignore_permissions=True, ignore_mandatory=True)
        
        mock_lead_wait.side_effect = SuspendJob("wait")
        with self.assertRaises(SuspendJob):
            _create_a_contact(mcc.name)
            
        frappe.get_doc({
            "doctype": "Communication",
            "reference_doctype": "Multi Channel Cadence",
            "reference_name": mcc.name,
            "communication_medium": "Email",
            "subject": "Test",
            "status": "Draft"
        }).insert(ignore_permissions=True)
            
        mock_lead_wait.side_effect = None
        _create_a_contact(mcc.name)
        mock_enqueue.assert_called()

        lead = frappe.get_doc("CRM Lead", self.lead_id)
        if not lead.apollo_ids:
            lead.append("apollo_ids", {"account": "TestAccount1", "apollo_id": "apollo_contact_1"})
        else:
            found = False
            for row in lead.apollo_ids:
                if row.account == "TestAccount1":
                    row.apollo_id = "apollo_contact_1"
                    found = True
                    break
            if not found:
                lead.append("apollo_ids", {"account": "TestAccount1", "apollo_id": "apollo_contact_1"})
        lead.save(ignore_permissions=True)
        
        mock_enqueue.reset_mock()
        _create_a_contact(mcc.name)
        mock_enqueue.assert_called_with(
            method="frappe_apollo.apollo.doctype.crm_lead.crm_lead.update_a_contact",
            queue="short",
            lead_name=self.lead_id,
            account_name="TestAccount1"
        )

    @patch("frappe_apollo.integrations.apollo.ApolloClient")
    @patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event")
    def test_mcc_sequence_assignment(self, mock_mcc_wait, mock_client_cls):
        cadence = self._create_test_cadence()
        mcc = frappe.get_doc({
            "doctype": "Multi Channel Cadence",
            "provider": [{"cadence_provider": "Apollo"}],
            "sender": "test_sender@example.com",
            "recipient": self.lead_id,
            "cadence_name": cadence.name,
            "cadence": cadence.name,
            "status": "Scheduled",
            "apollo_account": "TestAccount1",
            "apollo_sequence_id": "seq_test_1"
        }).insert(ignore_permissions=True, ignore_mandatory=True)

        lead = frappe.get_doc("CRM Lead", self.lead_id)
        if not lead.apollo_ids:
            lead.append("apollo_ids", {"account": "TestAccount1", "apollo_id": ""})
            lead.flags.ignore_mandatory = True
            lead.save(ignore_permissions=True)
        else:
            found = False
            for row in lead.apollo_ids:
                if row.account == "TestAccount1":
                    row.apollo_id = ""
                    found = True
                    break
            if not found:
                lead.append("apollo_ids", {"account": "TestAccount1", "apollo_id": ""})
            lead.flags.ignore_mandatory = True
            lead.save(ignore_permissions=True)

        frappe.db.set_value("CRM Lead Apollo ID",
                            {"parent": lead.name, "account": "TestAccount1"},
                            "apollo_id",
                            "")
        
        mock_mcc_wait.side_effect = SuspendJob("wait")
        with self.assertRaises(SuspendJob):
            _assign_contact_to_sequence(mcc.name)
            
        frappe.db.set_value("CRM Lead Apollo ID",
                            {"parent": lead.name, "account": "TestAccount1"},
                            "apollo_id",
                            "apollo_contact_1")
        
        mock_mcc_wait.side_effect = None
        mock_client = mock_client_cls.return_value
        _assign_contact_to_sequence(mcc.name)
        mock_client.add_contacts_to_sequence.assert_called_once_with("apollo_contact_1", "seq_test_1", "mailbox_1")

    @patch("frappe.enqueue")
    def test_mcc_scheduling(self, mock_enqueue):
        cadence = self._create_test_cadence()
        mcc = frappe.get_doc({
            "doctype": "Multi Channel Cadence",
            "provider": [{"cadence_provider": "Apollo"}],
            "sender": "test_sender@example.com",
            "recipient": self.lead_id,
            "cadence_name": cadence.name,
            "cadence": cadence.name,
            "status": "Draft",
            "apollo_account": "TestAccount1",
            "apollo_sequence_id": "seq_test_1"
        }).insert(ignore_permissions=True, ignore_mandatory=True)
        
        mcc.status = "Scheduled"
        mcc.save(ignore_permissions=True)
        
        mock_enqueue.reset_mock()
        mcc_on_update(mcc)
        self.assertTrue(mock_enqueue.call_count >= 1)
 

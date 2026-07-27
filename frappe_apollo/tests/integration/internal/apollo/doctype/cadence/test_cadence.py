import frappe
from frappe.tests import IntegrationTestCase
from frappe_controller.utils.controller import SuspendJob
from unittest.mock import patch

from frappe_apollo.apollo.doctype.cadence.cadence import on_update, _provision_sequence
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
                "status": "Unauthorized"
            }).insert(ignore_permissions=True)
        else:
            frappe.db.set_value("Apollo Account", "TestAccount1", "status", "Unauthorized")

        if not frappe.db.exists("Apollo Account", "TestAccount2"):
            frappe.get_doc({
                "doctype": "Apollo Account",
                "account_name": "TestAccount2",
                "status": "Authorized"
            }).insert(ignore_permissions=True)
            
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
                "subject": "Test",
                "response": "Test"
            }).insert(ignore_permissions=True)

        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 0)
        frappe.db.set_value("Apollo Account", "TestAccount1", "status", "Unauthorized")
        frappe.db.set_value("Apollo Account", "TestAccount2", "status", "Authorized")

    def tearDown(self):
        frappe.db.rollback()
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

    @patch("frappe_apollo.apollo.doctype.cadence.cadence.enqueue")
    @patch("frappe_apollo.integrations.apollo.ApolloClient")
    @patch("frappe_apollo.apollo.doctype.cadence.cadence.ApolloClient")
    @patch("frappe_controller.utils.controller.wait_for_event")
    def test_cadence_provisioning(self, mock_wait, mock_client_cls, mock_client_cls_integration, mock_enqueue):
        cadence = self._create_test_cadence()

        on_update(cadence)
        mock_enqueue.assert_not_called()
        
        cadence.append("apollo_ids", {"account": "TestAccount1", "sender": "test_sender@example.com", "status": "Active"})
        cadence.append("apollo_ids", {"account": "TestAccount2", "sender": "test_sender@example.com", "status": "Active", "apollo_id": "seq_test_2"})
        cadence.save(ignore_permissions=True)
        on_update(cadence)
        
        self.assertEqual(mock_enqueue.call_count, 4) # 2 for Account1 (provision sequence, provision fields), 2 for Account2
        mock_enqueue.reset_mock()
        
        # Run job for Account1. Provider disabled + Account Unauthorized.
        with self.assertRaises(SuspendJob):
            mock_wait.side_effect = SuspendJob("wait")
            _provision_sequence(cadence.name, "TestAccount1", "test_sender@example.com", emailer_steps=[])
            
        # Authorize and Enable
        frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 1)
        frappe.db.set_value("Apollo Account", "TestAccount1", "status", "Authorized")
        
        # Remove Account_1 from apollo_ids to test Fail Fast
        cadence.apollo_ids = [row for row in cadence.apollo_ids if row.account != "TestAccount1"]
        cadence.save(ignore_permissions=True)
        
        # Job resumes -> should return early
        mock_client = mock_client_cls.return_value
        mock_wait.side_effect = None # Job resumed
        _provision_sequence(cadence.name, "TestAccount1", "test_sender@example.com", emailer_steps=[])
        mock_client.create_sequence.assert_not_called()
        
        # Add Account_1 back
        cadence.append("apollo_ids", {"account": "TestAccount1", "sender": "test_sender@example.com", "status": "Active"})
        cadence.save(ignore_permissions=True)
        
        # Run provisioning job
        mock_client.create_sequence.return_value = "seq_test_1"
        _provision_sequence(cadence.name, "TestAccount1", "test_sender@example.com", emailer_steps=[])
            
        mock_client.create_sequence.assert_called_once()

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
        # It should pick one of them, depending on implementation it might be Account1 or Account2
        # Let's explicitly set it to TestAccount1
        mcc.apollo_account = "TestAccount1"
        mcc.apollo_sequence_id = "seq_test_1"
        
        # Remove Account_1 from Cadence
        cadence.apollo_ids = [row for row in cadence.apollo_ids if row.account != "TestAccount1"]
        cadence.save(ignore_permissions=True)
        
        before_save(mcc)
        # Should reassign to TestAccount2 because TestAccount1 is no longer in cadence
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
        
        # Phase 3: CRM Lead (Contact) Creation/Update
        mock_lead_wait.side_effect = SuspendJob("wait")
        with self.assertRaises(SuspendJob):
            _create_a_contact(mcc.name)
            
        # Create Communications to satisfy
        frappe.get_doc({
            "doctype": "Communication",
            "reference_doctype": "Multi Channel Cadence",
            "reference_name": mcc.name,
            "communication_medium": "Email",
            "subject": "Test",
            "status": "Draft"
        }).insert(ignore_permissions=True)
            
        # Re-run after communications created
        mock_lead_wait.side_effect = None
        _create_a_contact(mcc.name)
        mock_enqueue.assert_called()

        # Add apollo_id manually
        lead = frappe.get_doc("CRM Lead", self.lead_id)
        if not lead.apollo_ids:
            lead.append("apollo_ids", {"account": "TestAccount1", "apollo_id": "apollo_contact_1"})
        else:
            # Need to find the correct row
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

        # First, clean it up to simulate waiting
        frappe.db.set_value("CRM Lead Apollo ID",
                            {"parent": lead.name, "account": "TestAccount1"},
                            "apollo_id",
                            "")
        
        mock_mcc_wait.side_effect = SuspendJob("wait")
        with self.assertRaises(SuspendJob):
            _assign_contact_to_sequence(mcc.name)
            
        # Now satisfy it by putting it back
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
        
        # We can simulate Draft -> Scheduled transition
        mcc.status = "Scheduled"
        mcc.save(ignore_permissions=True)
        
        mock_enqueue.reset_mock()
        mcc_on_update(mcc)
        self.assertTrue(mock_enqueue.call_count >= 1) 

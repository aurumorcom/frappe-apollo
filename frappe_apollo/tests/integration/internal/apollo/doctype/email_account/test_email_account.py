from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from frappe_apollo.apollo.doctype.email_account.email_account import (
	get_email_accounts,
	queue_get_email_accounts,
)


class TestEmailAccountIntegration(IntegrationTestCase):
	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def setUp(self):
		super().setUp()

		if frappe.db.table_exists("FS Job"):
			frappe.db.delete("FS Job")

		self.acc1 = f"Mailbox Test Acc {frappe.generate_hash(length=6)}"
		self.acc2 = f"Another Test Acc {frappe.generate_hash(length=6)}"
		self.email1 = f"test1_{frappe.generate_hash(length=6)}@example.com"

		doc1 = frappe.get_doc(
			{"doctype": "Apollo Account", "account_name": self.acc1, "api_key": "some_key"}
		).insert(ignore_permissions=True)

		doc2 = frappe.get_doc(
			{"doctype": "Apollo Account", "account_name": self.acc2, "api_key": "some_key"}
		).insert(ignore_permissions=True)

		if frappe.db.table_exists("FS Job"):
			frappe.db.delete("FS Job")

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()

	@patch("frappe.enqueue")
	def test_queue_get_email_accounts(self, mock_enqueue):
		queue_get_email_accounts()
		found = False
		for call in mock_enqueue.call_args_list:
			if call[1].get("account_name") == self.acc1:
				found = True
				break
		self.assertTrue(found, f"get_email_accounts was not queued for {self.acc1}")

	@patch("frappe.enqueue")
	def test_queue_get_email_accounts_deduplication_when_queued(self, mock_enqueue):
		if frappe.db.table_exists("FS Job"):
			method_name = "frappe_apollo.apollo.doctype.email_account.email_account.get_email_accounts"

			job_type_name = frappe.db.exists("Controller Job Type", {"method": method_name})
			if not job_type_name:
				job_type_name = (
					frappe.get_doc(
						{
							"doctype": "Controller Job Type",
							"method": method_name,
						}
					)
					.insert(ignore_permissions=True)
					.name
				)

			job = frappe.get_doc(
				{
					"doctype": "FS Job",
					"job_type": job_type_name,
					"job_name": method_name,
					"status": "queued",
					"arguments": f'{{"account_name": "{self.acc1}"}}',
				}
			).insert(ignore_permissions=True)

		queue_get_email_accounts()

		queued_accounts = [call[1].get("account_name") for call in mock_enqueue.call_args_list]
		self.assertNotIn(
			self.acc1,
			queued_accounts,
			f"get_email_accounts was queued for {self.acc1} despite existing queued FS Job",
		)
		self.assertIn(self.acc2, queued_accounts, f"get_email_accounts was not queued for {self.acc2}")

	@patch("frappe.enqueue")
	def test_queue_get_email_accounts_no_deduplication_when_finished(self, mock_enqueue):
		if frappe.db.table_exists("FS Job"):
			method_name = "frappe_apollo.apollo.doctype.email_account.email_account.get_email_accounts"

			job_type_name = frappe.db.exists("Controller Job Type", {"method": method_name})
			if not job_type_name:
				job_type_name = (
					frappe.get_doc(
						{
							"doctype": "Controller Job Type",
							"method": method_name,
						}
					)
					.insert(ignore_permissions=True)
					.name
				)

			job = frappe.get_doc(
				{
					"doctype": "FS Job",
					"job_type": job_type_name,
					"job_name": method_name,
					"status": "finished",
					"arguments": f'{{"account_name": "{self.acc1}"}}',
				}
			).insert(ignore_permissions=True)

		queue_get_email_accounts()

		queued_accounts = [call[1].get("account_name") for call in mock_enqueue.call_args_list]
		self.assertIn(
			self.acc1, queued_accounts, f"get_email_accounts should have been queued for {self.acc1}"
		)

	def test_scheduler_hook_registered_as_daily(self):
		scheduler_events = frappe.get_hooks("scheduler_events")
		daily_events = scheduler_events.get("daily", [])
		all_events = scheduler_events.get("all", [])

		target_method = "frappe_apollo.apollo.doctype.email_account.email_account.enqueue_get_email_accounts"
		self.assertIn(
			target_method,
			daily_events,
			"enqueue_get_email_accounts should be registered in scheduler_events['daily']",
		)
		self.assertNotIn(
			target_method,
			all_events,
			"enqueue_get_email_accounts should not be registered in scheduler_events['all']",
		)

	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	def test_get_email_accounts_creation(self, mock_client_cls):
		mock_client = mock_client_cls.return_value
		mock_client.get_email_accounts.return_value = {
			"email_accounts": [{"id": "mailbox_id_1", "email": self.email1, "active": True}]
		}

		get_email_accounts(self.acc1)

		mock_client.get_email_accounts.assert_called_once()

		mailboxes = frappe.get_all("Email Account", filters={"email_id": self.email1})
		self.assertEqual(len(mailboxes), 1)

		mb_doc = frappe.get_doc("Email Account", mailboxes[0].name)
		self.assertEqual(mb_doc.email_id, self.email1)
		self.assertEqual(mb_doc.email_account_name, self.email1)
		self.assertEqual(mb_doc.name, self.email1)
		self.assertEqual(mb_doc.service, "Apollo")
		self.assertEqual(len(mb_doc.get("apollo_ids")), 1)
		self.assertEqual(mb_doc.apollo_ids[0].account, self.acc1)
		self.assertEqual(mb_doc.apollo_ids[0].apollo_id, "mailbox_id_1")

	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	def test_get_email_accounts_append(self, mock_client_cls):
		emb = frappe.get_doc(
			{
				"doctype": "Email Account",
				"email_id": self.email1,
				"service": "Apollo",
				"enable_outgoing": 0,
				"enable_incoming": 0,
				"apollo_ids": [{"account": self.acc1, "apollo_id": "mailbox_id_1"}],
			}
		).insert(ignore_permissions=True)

		mock_client = mock_client_cls.return_value
		mock_client.get_email_accounts.return_value = {
			"email_accounts": [{"id": "mailbox_id_1_alt", "email": self.email1, "active": True}]
		}

		get_email_accounts(self.acc2)

		mailboxes = frappe.get_all("Email Account", filters={"email_id": self.email1})
		self.assertEqual(len(mailboxes), 1)

		mb_doc = frappe.get_doc("Email Account", mailboxes[0].name)

		# It should now have 2 apollo accounts
		self.assertEqual(len(mb_doc.get("apollo_ids")), 2)
		accounts = [acc.account for acc in mb_doc.get("apollo_ids")]
		self.assertIn(self.acc1, accounts)
		self.assertIn(self.acc2, accounts)

	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	def test_get_email_accounts_prevents_name_collision(self, mock_client_cls):
		# Pre-create an Email Account whose title-cased prefix matches "Aryan Singh"
		if not frappe.db.exists("Email Account", "Aryan Singh"):
			frappe.get_doc(
				{
					"doctype": "Email Account",
					"email_account_name": "Aryan Singh",
					"email_id": "aryan.singh@otherdomain.com",
					"service": "Apollo",
				}
			).insert(ignore_permissions=True)

		collision_email = "aryan.singh@newdomain.com"
		mock_client = mock_client_cls.return_value
		mock_client.get_email_accounts.return_value = {
			"email_accounts": [{"id": "mailbox_collision_id", "email": collision_email, "active": True}]
		}

		# Creating mailbox for collision_email should name it collision_email, avoiding IntegrityError
		get_email_accounts(self.acc1)

		doc = frappe.get_doc("Email Account", collision_email)
		self.assertEqual(doc.email_id, collision_email)
		self.assertEqual(doc.email_account_name, collision_email)

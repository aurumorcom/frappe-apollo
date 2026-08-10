import frappe
from frappe.tests import IntegrationTestCase

from frappe_apollo.install import after_install


class TestInstallIntegration(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		if frappe.db.exists("Cadence Provider", "Apollo"):
			frappe.delete_doc("Cadence Provider", "Apollo", ignore_permissions=True, force=True)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		frappe.delete_doc_if_exists("Cadence Provider", "Apollo", force=True)
		frappe.db.commit()
		super().tearDownClass()

	def tearDown(self):
		frappe.db.rollback()
		frappe.delete_doc_if_exists("Cadence Provider", "Apollo", force=True)
		frappe.db.commit()
		super().tearDown()

	def test_after_install_integration(self):
		after_install()

		self.assertTrue(frappe.db.exists("Cadence Provider", "Apollo"))
		doc = frappe.get_doc("Cadence Provider", "Apollo")
		self.assertEqual(doc.enabled, 1)
		channels = [row.channel for row in doc.channels]
		self.assertIn("Email", channels)

	def test_custom_fields_and_tabs(self):
		after_install()
		frappe.clear_cache()
		crm_meta = frappe.get_meta("CRM Lead")
		crm_field = crm_meta.get_field("apollo_ids")
		if crm_field and crm_field.insert_after:
			self.assertEqual(crm_field.insert_after, "integrations_tab")

		email_meta = frappe.get_meta("Email Account")
		email_tab = email_meta.get_field("integrations_tab")
		email_field = email_meta.get_field("apollo_ids")
		if email_tab and email_field:
			self.assertEqual(email_field.insert_after, "integrations_tab")

		cadence_meta = frappe.get_meta("Cadence")
		cadence_tab = cadence_meta.get_field("integrations_tab")
		cadence_field = cadence_meta.get_field("apollo_ids")
		if cadence_tab and cadence_field:
			self.assertEqual(cadence_field.insert_after, "integrations_tab")

		apollo_field_meta = frappe.get_meta("Apollo Field")
		apollo_field_tab = apollo_field_meta.get_field("integrations_tab")
		apollo_field_ids = apollo_field_meta.get_field("apollo_ids")
		if apollo_field_tab and apollo_field_ids:
			self.assertEqual(apollo_field_tab.fieldtype, "Tab Break")

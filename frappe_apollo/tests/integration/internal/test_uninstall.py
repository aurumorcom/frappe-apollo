import frappe
from frappe.tests import IntegrationTestCase

from frappe_apollo.install import after_install
from frappe_apollo.uninstall import before_uninstall


class TestUninstallIntegration(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		after_install()

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

	def test_before_uninstall_integration(self):
		self.assertTrue(frappe.db.exists("Cadence Provider", "Apollo"))

		before_uninstall()

		self.assertFalse(frappe.db.exists("Cadence Provider", "Apollo"))

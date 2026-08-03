import frappe
from frappe.tests import IntegrationTestCase

from frappe_apollo.install import after_install
from frappe_apollo.uninstall import before_uninstall


class TestUninstallIntegration(IntegrationTestCase):

	def setUp(self):
		super().setUp()
		after_install()

	def tearDown(self):
		if frappe.db.exists("Cadence Provider", "Apollo"):
			frappe.delete_doc("Cadence Provider", "Apollo", ignore_permissions=True, force=True)
		super().tearDown()

	def test_before_uninstall_integration(self):
		self.assertTrue(frappe.db.exists("Cadence Provider", "Apollo"))

		before_uninstall()

		self.assertFalse(frappe.db.exists("Cadence Provider", "Apollo"))

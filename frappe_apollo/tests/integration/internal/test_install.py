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

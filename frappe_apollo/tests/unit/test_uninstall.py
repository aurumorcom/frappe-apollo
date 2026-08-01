import unittest
from unittest.mock import patch
from frappe_apollo.uninstall import before_uninstall


class TestUninstall(unittest.TestCase):

	@patch("frappe_apollo.uninstall.frappe")
	def test_before_uninstall_removes_apollo_provider(self, mock_frappe):
		def exists_side_effect(dt, name=None):
			if dt == "DocType" and name == "Cadence Provider":
				return True
			if dt == "Cadence Provider" and name == "Apollo":
				return True
			return False

		mock_frappe.db.exists.side_effect = exists_side_effect

		before_uninstall()

		mock_frappe.delete_doc.assert_called_once_with("Cadence Provider", "Apollo", ignore_permissions=True, force=True)
		mock_frappe.db.commit.assert_called_once()

	@patch("frappe_apollo.uninstall.frappe")
	def test_before_uninstall_handles_non_existent_provider(self, mock_frappe):
		def exists_side_effect(dt, name=None):
			if dt == "DocType" and name == "Cadence Provider":
				return True
			if dt == "Cadence Provider" and name == "Apollo":
				return False
			return False

		mock_frappe.db.exists.side_effect = exists_side_effect

		before_uninstall()

		mock_frappe.delete_doc.assert_not_called()
		mock_frappe.db.commit.assert_called_once()

	@patch("frappe_apollo.uninstall.frappe")
	def test_before_uninstall_handles_missing_doctype(self, mock_frappe):
		mock_frappe.db.exists.return_value = False

		before_uninstall()

		mock_frappe.delete_doc.assert_not_called()
		mock_frappe.db.commit.assert_not_called()

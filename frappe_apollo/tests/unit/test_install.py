from unittest.mock import MagicMock, patch

from frappe.tests import UnitTestCase

from frappe_apollo.install import after_install


class TestInstall(UnitTestCase):
	@patch("frappe_apollo.install.frappe")
	def test_after_install_creates_apollo_provider_when_missing(self, mock_frappe):
		def exists_side_effect(dt, name=None):
			if dt == "DocType" and name == "Cadence Provider":
				return True
			if dt == "Cadence Provider" and name == "Apollo":
				return False
			return False

		mock_frappe.db.exists.side_effect = exists_side_effect
		mock_doc = MagicMock()
		mock_frappe.get_doc.return_value = mock_doc

		after_install()

		mock_frappe.get_doc.assert_called_once_with(
			{
				"doctype": "Cadence Provider",
				"provider_name": "Apollo",
				"enabled": 1,
				"channels": [
					{
						"channel": "Email",
						"priority": 1,
					}
				],
			}
		)
		mock_doc.insert.assert_called_once_with(ignore_permissions=True)
		mock_frappe.db.commit.assert_called_once()

	@patch("frappe_apollo.install.frappe")
	def test_after_install_idempotent_when_provider_exists(self, mock_frappe):
		def exists_side_effect(dt, name=None):
			if dt == "DocType" and name == "Cadence Provider":
				return True
			if dt == "Cadence Provider" and name == "Apollo":
				return True
			return False

		mock_frappe.db.exists.side_effect = exists_side_effect
		mock_doc = MagicMock()
		mock_doc.channels = [MagicMock(channel="Email")]
		mock_frappe.get_doc.return_value = mock_doc

		after_install()

		mock_frappe.get_doc.assert_called_once_with("Cadence Provider", "Apollo")
		mock_doc.insert.assert_not_called()
		mock_doc.save.assert_not_called()
		mock_frappe.db.commit.assert_called_once()

	@patch("frappe_apollo.install.frappe")
	def test_after_install_appends_email_channel_if_missing(self, mock_frappe):
		def exists_side_effect(dt, name=None):
			if dt == "DocType" and name == "Cadence Provider":
				return True
			if dt == "Cadence Provider" and name == "Apollo":
				return True
			return False

		mock_frappe.db.exists.side_effect = exists_side_effect
		mock_doc = MagicMock()
		mock_doc.channels = []
		mock_frappe.get_doc.return_value = mock_doc

		after_install()

		mock_doc.append.assert_called_once_with(
			"channels",
			{
				"channel": "Email",
				"priority": 1,
			},
		)
		mock_doc.save.assert_called_once_with(ignore_permissions=True)
		mock_frappe.db.commit.assert_called_once()

	@patch("frappe_apollo.install.frappe")
	def test_after_install_handles_missing_doctype(self, mock_frappe):
		mock_frappe.db.exists.return_value = False

		after_install()

		mock_frappe.get_doc.assert_not_called()
		mock_frappe.db.commit.assert_not_called()

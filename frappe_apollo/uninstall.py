# Copyright (c) 2026, Aurumor and contributors
# For license information, please see license.txt

import frappe


def before_uninstall() -> None:
	"""Remove Apollo Cadence Provider upon uninstallation."""
	if not frappe.db.exists("DocType", "Cadence Provider"):
		return

	if frappe.db.exists("Cadence Provider", "Apollo"):
		frappe.delete_doc("Cadence Provider", "Apollo", ignore_permissions=True, force=True)

	frappe.db.commit()

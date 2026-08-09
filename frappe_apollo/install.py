# Copyright (c) 2026, Aurumor and contributors
# For license information, please see license.txt

import frappe


def after_install() -> None:
	"""Add Apollo as a Cadence Provider upon installation."""
	if not frappe.db.exists("DocType", "Cadence Provider"):
		return

	if not frappe.db.exists("Cadence Provider", "Apollo"):
		doc = frappe.get_doc(
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
		doc.insert(ignore_permissions=True)
	else:
		doc = frappe.get_doc("Cadence Provider", "Apollo")
		email_channel_exists = any(row.channel == "Email" for row in getattr(doc, "channels", []))
		if not email_channel_exists:
			doc.append(
				"channels",
				{
					"channel": "Email",
					"priority": 1,
				},
			)
			doc.save(ignore_permissions=True)

	frappe.db.commit()

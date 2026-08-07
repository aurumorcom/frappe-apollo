import frappe
from frappe_controller.utils.background_jobs import enqueue


def on_update(doc, method=None):
	if doc.name == "Apollo" and doc.enabled:
		records = frappe.get_all("Cadence Apollo ID", fields=["parent", "account"])
		seen = set()
		for r in records:
			cadence_name = r.get("parent")
			account_name = r.get("account")
			if cadence_name and account_name and (cadence_name, account_name) not in seen:
				seen.add((cadence_name, account_name))
				enqueue(
					method="frappe_apollo.apollo.doctype.cadence.cadence.update_sequence_steps",
					queue="low",
					cadence_name=cadence_name,
					account_name=account_name,
				)

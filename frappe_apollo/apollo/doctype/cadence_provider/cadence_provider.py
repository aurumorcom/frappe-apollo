import frappe

def on_update(doc, method=None):
	if doc.name == "Apollo":
		# Only enqueue for cadences linked to Apollo
		cadences = frappe.get_all("Cadence Apollo ID", pluck="parent")
		unique_cadences = list(set(cadences))
		from frappe_controller.utils.background_jobs import enqueue
		for cadence_name in unique_cadences:
			enqueue(
				method="frappe_apollo.apollo.doctype.apollo_field.apollo_field.enqueue_provision_cadence_fields",
				queue="low",
				cadence_name=cadence_name
			)

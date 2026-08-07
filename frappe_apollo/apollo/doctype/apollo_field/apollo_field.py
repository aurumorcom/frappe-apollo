import frappe
from frappe.model.document import Document


class ApolloField(Document):
	pass


def enqueue_provision_cadence_fields(cadence_name, account_name, sender=None):
	from frappe_apollo.apollo.doctype.cadence.cadence import update_sequence_steps

	return update_sequence_steps(cadence_name, account_name, sender=sender)


def provision_a_field(label, apollo_type, account_name):
	from frappe_apollo.apollo.doctype.cadence.cadence import update_sequence_steps

	# Forward to consolidated job
	cadences = frappe.get_all("Cadence Apollo ID", filters={"account": account_name}, pluck="parent")
	for cadence_name in set(cadences):
		update_sequence_steps(cadence_name, account_name)

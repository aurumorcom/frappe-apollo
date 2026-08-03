import frappe
from frappe.model.document import Document


class ApolloField(Document):
	pass

def enqueue_provision_cadence_fields(cadence_name, account_name, sender=None):
	cadence = frappe.get_doc("Cadence", cadence_name)

	supported_channels = []
	try:
		provider = frappe.get_doc("Cadence Provider", "Apollo")
		supported_channels = [c.channel for c in (provider.get("channels") or []) if c.channel]
	except Exception:
		supported_channels = []

	index = 0
	for sch in (cadence.get("cadence_schedules") or []):
		channel = sch.get("channel")
		ref_dt = sch.get("reference_doctype")
		if channel in supported_channels or ref_dt == "Email Template":
			index += 1
			if ref_dt == "Email Template":
				labels = [(f"subject_{index}", "string"), (f"body_{index}", "textarea")]
			else:
				labels = [(f"message_{index}", "textarea")]

			for label, apollo_type in labels:
				from frappe_controller.utils.background_jobs import enqueue
				enqueue(
					"frappe_apollo.apollo.doctype.apollo_field.apollo_field.provision_a_field",
					queue="low",
					label=label,
					apollo_type=apollo_type,
					account_name=account_name
				)

def provision_a_field(label, apollo_type, account_name):
	from frappe_controller.utils.controller import wait_for_event

	from frappe_apollo.integrations.apollo import ApolloClient

	is_enabled = frappe.db.get_value("Cadence Provider", "Apollo", "enabled")
	if not is_enabled:
		wait_for_event(
			event_key="doc:Cadence Provider:Apollo:on_update",
			condition="argument.get('enabled') == 1"
		)

	account_status = frappe.db.get_value("Apollo Account", account_name, "status")
	if account_status != "Authorized":
		wait_for_event(
			event_key=f"doc:Apollo Account:{account_name}:on_update",
			condition="argument.get('status') == 'Authorized'"
		)

	try:
		field_doc = frappe.get_doc("Apollo Field", label)
	except frappe.DoesNotExistError:
		field_doc = frappe.get_doc({
			"doctype": "Apollo Field",
			"label": label,
			"field_type": apollo_type
		})
		field_doc.insert(ignore_permissions=True)

	mapping_exists = any(
		r.account == account_name for r in field_doc.get("apollo_ids", [])
	)

	if not mapping_exists:
		client = ApolloClient(account_name)
		try:
			res = client.create_custom_field(field_doc.label, field_doc.field_type)
			fields = res.get("typed_custom_fields", []) or res.get("custom_fields", [])
			if fields:
				apollo_id = fields[0].get("id")
				field_doc.append("apollo_ids", {
					"account": account_name,
					"apollo_id": apollo_id
				})
				field_doc.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(title="Apollo Field Creation Failed", message=str(e))
			raise

import frappe
from frappe.model.document import Document
import hashlib

class ApolloField(Document):
	pass

def enqueue_provision_cadence_fields(cadence_name, account_name, sender):
	cadence = frappe.get_doc("Cadence", cadence_name)
	schedules = [s for s in (cadence.get("cadence_schedules") or []) if s.reference_doctype == "Email Template"]
	
	for step in schedules:
		for field_type in ["subject", "message"]:
			from frappe_controller.utils.background_jobs import enqueue
			enqueue(
				"frappe_apollo.apollo.doctype.apollo_field.apollo_field.provision_a_field",
				queue="low",
				cadence_name=cadence_name,
				step_name=step.name,
				field_type=field_type,
				account_name=account_name,
				sender=sender
			)

def provision_a_field(cadence_name, step_name, field_type, account_name, sender):
	cadence = frappe.get_doc("Cadence", cadence_name)
	
	row = next((r for r in cadence.get("apollo_ids", []) if r.account == account_name and r.sender == sender), None)
	if not row:
		return
		
	step = next((s for s in cadence.get("cadence_schedules", []) if s.name == step_name), None)
	if not step:
		return

	from frappe_apollo.integrations.apollo import ApolloClient
	from frappe_controller.utils.controller import wait_for_event
	
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

	if not row.apollo_id:
		wait_for_event(
			f"doc:Cadence:{cadence.name}:on_update",
			condition=f"any(r.get('account') == '{account_name}' and r.get('sender') == '{sender}' and r.get('apollo_id') for r in argument.get('apollo_ids', []))",
			consider_events_since=cadence.modified
		)
		
		cadence.reload()
		row = next((r for r in cadence.get("apollo_ids", []) if r.account == account_name and r.sender == sender), None)
		if not row or not row.apollo_id:
			return
			
	hash_input = f"{cadence.name}_{step.name}_{field_type}"
	label = f"{hashlib.md5(hash_input.encode()).hexdigest()[:10]}"
	apollo_type = "string" if field_type == "subject" else "textarea"
	
	field_name = None
	try:
		field_doc = frappe.get_doc("Apollo Field", label)
		field_name = field_doc.name
	except frappe.DoesNotExistError:
		field_doc = frappe.get_doc({
			"doctype": "Apollo Field",
			"label": label,
			"field_type": apollo_type
		})
		field_doc.insert(ignore_permissions=True)
		field_name = field_doc.name
		
	modified = False
	if field_type == "subject" and step.subject_field != field_name:
		step.subject_field = field_name
		modified = True
	elif field_type == "message" and step.message_field != field_name:
		step.message_field = field_name
		modified = True
		
	if modified:
		cadence.save(ignore_permissions=True)

	if row.status != "Active":
		return
		
	apollo_sequence_id = row.apollo_id
	
	# Check if mapping exists
	mapping_exists = any(
		r.account == account_name and r.apollo_sequence_id == apollo_sequence_id
		for r in field_doc.get("apollo_ids", [])
	)
	
	if not mapping_exists:
		client = ApolloClient(account_name)
		try:
			res = client.create_custom_field(field_doc.label, field_doc.field_type)
			fields = res.get("typed_custom_fields", [])
			if fields:
				apollo_id = fields[0].get("id")
				field_doc.append("apollo_ids", {
					"account": account_name,
					"apollo_sequence_id": apollo_sequence_id,
					"apollo_id": apollo_id
				})
				field_doc.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(title="Apollo Field Creation Failed", message=str(e))
			raise


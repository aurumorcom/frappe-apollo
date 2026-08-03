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
	for sch in cadence.get("cadence_schedules") or []:
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
					account_name=account_name,
				)


def provision_a_field(label, apollo_type, account_name):
	from frappe_controller.utils.controller import wait_for_event

	from frappe_apollo.integrations.apollo import ApolloClient

	is_enabled = frappe.db.get_value("Cadence Provider", "Apollo", "enabled")
	if not is_enabled:
		wait_for_event(
			event_key="doc:Cadence Provider:Apollo:on_update",
			condition="argument.get('enabled') == 1",
		)

	account_status = frappe.db.get_value("Apollo Account", account_name, "status")
	if account_status != "Authorized":
		wait_for_event(
			event_key=f"doc:Apollo Account:{account_name}:on_update",
			condition="argument.get('status') == 'Authorized'",
		)

	try:
		field_doc = frappe.get_doc("Apollo Field", label)
	except frappe.DoesNotExistError:
		field_doc = frappe.get_doc(
			{
				"doctype": "Apollo Field",
				"label": label,
				"field_type": apollo_type,
			}
		)
		field_doc.insert(ignore_permissions=True)

	mapping_exists = any(r.account == account_name for r in field_doc.get("apollo_ids", []))

	client = ApolloClient(account_name)
	if not mapping_exists:
		try:
			res = client.create_custom_field(field_doc.label, field_doc.field_type)
			fields = res.get("typed_custom_fields", []) or res.get("custom_fields", [])
			if fields:
				apollo_id = fields[0].get("id")
				field_doc.append(
					"apollo_ids",
					{
						"account": account_name,
						"apollo_id": apollo_id,
					},
				)
				field_doc.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(title="Apollo Field Creation Failed", message=str(e))
			raise

	apollo_sequence_id = frappe.db.get_value("Apollo Account", account_name, "apollo_sequence_id")
	if not apollo_sequence_id:
		wait_for_event(
			event_key=f"doc:Apollo Account:{account_name}:on_update",
			condition="argument.get('apollo_sequence_id')",
		)
		apollo_sequence_id = frappe.db.get_value("Apollo Account", account_name, "apollo_sequence_id")

	if apollo_sequence_id:
		_update_sequence(client, apollo_sequence_id, label)


def _update_sequence(client, sequence_id, label):
	try:
		field_index = int(label.split("_")[-1])
	except ValueError, IndexError:
		field_index = 1

	sequence_info = client.get_sequence(sequence_id)
	emailer_steps = (
		sequence_info.get("emailer_steps", [])
		if isinstance(sequence_info, dict) and "emailer_steps" in sequence_info
		else (
			sequence_info.get("sequence", {}).get("emailer_steps", [])
			if isinstance(sequence_info, dict)
			else []
		)
	)

	if len(emailer_steps) >= field_index:
		return

	new_steps = list(emailer_steps)
	is_email = label.startswith("subject") or label.startswith("body")

	for step_num in range(len(emailer_steps) + 1, field_index + 1):
		subj = (
			f"{{{{custom_field_subject_{step_num}}}}}"
			if is_email
			else f"{{{{custom_field_message_{step_num}}}}}"
		)
		body = (
			f"{{{{custom_field_body_{step_num}}}}}"
			if is_email
			else f"{{{{custom_field_message_{step_num}}}}}"
		)
		new_step = {
			"position": step_num,
			"type": "auto_email",
			"wait_time": 1,
			"wait_mode": "day",
			"emailer_touches": [
				{
					"type": "new_thread",
					"status": "approved",
					"include_signature": True,
					"emailer_template": {
						"subject": subj,
						"body_html": body,
					},
				}
			],
		}
		new_steps.append(new_step)

	client.update_sequence(sequence_id, {"emailer_steps": new_steps})

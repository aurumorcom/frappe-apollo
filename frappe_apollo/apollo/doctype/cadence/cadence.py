import frappe
from frappe_controller.utils.background_jobs import enqueue
from frappe_controller.utils.controller import wait_for_event

from frappe_apollo.integrations.apollo import ApolloClient


def on_update(doc, method=None):
	required_field_labels = _ensure_local_apollo_fields(doc)

	for row in doc.get("apollo_ids", []):
		account_name = row.get("account") if isinstance(row, dict) else getattr(row, "account", None)
		if not account_name:
			continue

		if _check_account_requires_update(doc, account_name, required_field_labels):
			enqueue(
				"frappe_apollo.apollo.doctype.cadence.cadence.update_sequence_steps",
				queue="low",
				cadence_name=doc.name,
				account_name=account_name,
			)

	if doc.has_value_changed("enabled"):
		enqueue(
			"frappe_apollo.apollo.doctype.cadence.cadence.toggle_cadence_mccs",
			queue="low",
			cadence_name=doc.name,
		)


def _get_supported_channels():
	try:
		provider = frappe.get_doc("Cadence Provider", "Apollo")
		return [c.channel for c in (provider.get("channels") or []) if c.channel]
	except Exception:
		return ["Email"]


def _ensure_local_apollo_fields(doc):
	supported_channels = _get_supported_channels()
	required_labels = []
	index = 0

	for sch in doc.get("cadence_schedules") or []:
		channel = getattr(sch, "channel", None) or sch.get("channel")
		ref_dt = getattr(sch, "reference_doctype", None) or sch.get("reference_doctype")

		if channel in supported_channels or ref_dt == "Email Template" or channel == "Email":
			index += 1
			if ref_dt == "Email Template":
				labels = [(f"subject_{index}", "string"), (f"body_{index}", "textarea")]
			else:
				labels = [(f"message_{index}", "textarea")]

			for label, apollo_type in labels:
				required_labels.append((label, apollo_type, sch))
				try:
					frappe.get_doc("Apollo Field", label)
				except frappe.DoesNotExistError:
					field_doc = frappe.get_doc(
						{
							"doctype": "Apollo Field",
							"label": label,
							"field_type": apollo_type,
						}
					)
					field_doc.insert(ignore_permissions=True)

	return required_labels


def _check_account_requires_update(doc, account_name, required_field_labels):
	if not required_field_labels:
		return False

	for label, _, _ in required_field_labels:
		try:
			field_doc = frappe.get_doc("Apollo Field", label)
			mapping_exists = any(r.account == account_name for r in field_doc.get("apollo_ids", []))
			if not mapping_exists:
				return True
		except Exception:
			return True

	return True


def update_sequence_steps(cadence_name, account_name, sender=None):
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

	apollo_sequence_id = frappe.db.get_value("Apollo Account", account_name, "apollo_sequence_id")
	if not apollo_sequence_id:
		wait_for_event(
			event_key=f"doc:Apollo Account:{account_name}:on_update",
			condition="argument.get('apollo_sequence_id')",
		)
		apollo_sequence_id = frappe.db.get_value("Apollo Account", account_name, "apollo_sequence_id")

	cadence_doc = frappe.get_doc("Cadence", cadence_name)
	client = ApolloClient(account_name)

	_create_fields(client, cadence_doc, account_name)

	if apollo_sequence_id:
		_update_sequence(client, apollo_sequence_id, cadence_doc)


def _create_fields(client, cadence_doc, account_name):
	supported_channels = _get_supported_channels()
	index = 0

	for sch in cadence_doc.get("cadence_schedules") or []:
		channel = getattr(sch, "channel", None) or sch.get("channel")
		ref_dt = getattr(sch, "reference_doctype", None) or sch.get("reference_doctype")

		if channel in supported_channels or ref_dt == "Email Template" or channel == "Email":
			index += 1
			if ref_dt == "Email Template":
				labels = [(f"subject_{index}", "string"), (f"body_{index}", "textarea")]
			else:
				labels = [(f"message_{index}", "textarea")]

			for label, apollo_type in labels:
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
						if hasattr(e, "response") and getattr(e.response, "status_code", None) in (
							400,
							422,
							401,
							403,
						):
							frappe.log_error(title="Apollo Field Creation Skipped", message=str(e))
						else:
							frappe.log_error(title="Apollo Field Creation Failed", message=str(e))
							raise


def _update_sequence(client, sequence_id, cadence_doc):
	supported_channels = _get_supported_channels()
	schedules = []
	for sch in cadence_doc.get("cadence_schedules") or []:
		channel = getattr(sch, "channel", None) or sch.get("channel")
		ref_dt = getattr(sch, "reference_doctype", None) or sch.get("reference_doctype")
		if channel in supported_channels or ref_dt == "Email Template" or channel == "Email":
			schedules.append(sch)

	if not schedules:
		return

	max_index = len(schedules)

	try:
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
	except Exception:
		emailer_steps = []

	new_steps = list(emailer_steps)

	for step_num in range(len(emailer_steps) + 1, max_index + 1):
		sch = schedules[step_num - 1]
		send_after_days = getattr(sch, "send_after_days", None)
		if send_after_days is None and isinstance(sch, dict):
			send_after_days = sch.get("send_after_days", 0)
		elif send_after_days is None:
			send_after_days = 0

		wait_time = int(send_after_days)
		wait_mode = "second" if wait_time == 0 else "day"

		ref_dt = getattr(sch, "reference_doctype", None) or sch.get("reference_doctype")
		is_email = ref_dt == "Email Template"

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
			"wait_time": wait_time,
			"wait_mode": wait_mode,
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

	if len(new_steps) > len(emailer_steps):
		client.update_sequence(sequence_id, {"emailer_steps": new_steps})


def _validate_for_sequence(doc, account_name):
	supported_channels = _get_supported_channels()
	required_steps = 0
	for sch in doc.get("cadence_schedules") or []:
		channel = getattr(sch, "channel", None) or sch.get("channel")
		ref_dt = getattr(sch, "reference_doctype", None) or sch.get("reference_doctype")
		if channel in supported_channels or ref_dt == "Email Template" or channel == "Email":
			required_steps += 1

	if required_steps == 0:
		return

	apollo_sequence_id = frappe.db.get_value("Apollo Account", account_name, "apollo_sequence_id")
	if not apollo_sequence_id:
		frappe.msgprint(
			f"Apollo Account {account_name} does not have a configured Apollo Sequence ID. Disabling cadence.",
			alert=True,
		)
		doc.enabled = 0
		if hasattr(doc, "db_set"):
			doc.db_set("enabled", 0)
		return

	client = ApolloClient(account_name)
	try:
		sequence_info = client.get_sequence(apollo_sequence_id)
		if (
			isinstance(sequence_info, dict)
			and not sequence_info.get("emailer_campaign")
			and "emailer_steps" in sequence_info
			and not sequence_info.get("emailer_steps")
		):
			frappe.msgprint(
				f"Apollo Sequence ID {apollo_sequence_id} not found in Apollo Account {account_name}. Disabling cadence.",
				alert=True,
			)
			doc.enabled = 0
			if hasattr(doc, "db_set"):
				doc.db_set("enabled", 0)
			return

		emailer_steps = (
			sequence_info.get("emailer_steps", [])
			if isinstance(sequence_info, dict) and "emailer_steps" in sequence_info
			else (
				sequence_info.get("sequence", {}).get("emailer_steps", [])
				if isinstance(sequence_info, dict)
				else []
			)
		)
		current_steps = len(emailer_steps)
	except Exception as e:
		frappe.msgprint(
			f"Failed to fetch sequence details for Apollo Account {account_name}: {e!s}. Disabling cadence.",
			alert=True,
		)
		doc.enabled = 0
		if hasattr(doc, "db_set"):
			doc.db_set("enabled", 0)
		return

	if required_steps > current_steps:
		frappe.msgprint(
			f"Cadence required steps ({required_steps}) exceed Apollo sequence capacity ({current_steps}). Disabling cadence.",
			alert=True,
		)
		doc.enabled = 0
		if hasattr(doc, "db_set"):
			doc.db_set("enabled", 0)


def toggle_cadence_mccs(cadence_name):
	cadence_doc = frappe.get_doc("Cadence", cadence_name)

	if not cadence_doc.enabled:
		active_mccs = frappe.get_all(
			"Multi Channel Cadence",
			filters={
				"cadence_name": cadence_name,
				"status": ["in", ["Scheduled", "In Progress", "Active", "Draft"]],
			},
			fields=["name"],
		)
		for mcc in active_mccs:
			mcc_name = mcc.get("name") if isinstance(mcc, dict) else getattr(mcc, "name", None)
			if not mcc_name:
				continue
			mcc_doc = frappe.get_doc("Multi Channel Cadence", mcc_name)
			mcc_doc.last_status = mcc_doc.status
			mcc_doc.status = "Disabled"
			mcc_doc.save(ignore_permissions=True)
	else:
		disabled_mccs = frappe.get_all(
			"Multi Channel Cadence",
			filters={"cadence_name": cadence_name, "status": "Disabled"},
			fields=["name"],
		)
		for mcc in disabled_mccs:
			mcc_name = mcc.get("name") if isinstance(mcc, dict) else getattr(mcc, "name", None)
			if not mcc_name:
				continue
			mcc_doc = frappe.get_doc("Multi Channel Cadence", mcc_name)
			if mcc_doc.last_status:
				mcc_doc.status = mcc_doc.last_status
				mcc_doc.last_status = None
				mcc_doc.save(ignore_permissions=True)


_disable_cadence_mccs = toggle_cadence_mccs

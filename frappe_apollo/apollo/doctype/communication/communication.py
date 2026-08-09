import frappe
from frappe_controller.utils.controller import SuspendJob, wait_for_event


def on_update(doc, method=None):
	if doc.get_doc_before_save() and doc.get_doc_before_save().status != "Scheduled" and doc.status == "Scheduled":
		frappe.enqueue(
			method="frappe_apollo.apollo.doctype.communication.communication.update_a_contact",
			queue="medium",
			comm_name=doc.name
		)

def update_a_contact(comm_name):
	from frappe_apollo.integrations.apollo import ApolloClient

	comm = frappe.get_doc("Communication", comm_name)

	if comm.get("apollo_status") == "Scheduled":
		return

	mcc = frappe.get_doc("Multi Channel Cadence", comm.reference_name)
	if not mcc.apollo_account or not mcc.apollo_sequence_id:
		wait_for_event(
			event_key=f"doc:Multi Channel Cadence:{mcc.name}:on_update",
			condition="argument.get('apollo_account') and argument.get('apollo_sequence_id')"
		)
		mcc.reload()

	account_name = mcc.apollo_account

	is_enabled = frappe.db.get_value("Cadence Provider", "Apollo", "enabled")
	if not is_enabled:
		wait_for_event(
			event_key="doc:Cadence Provider:Apollo:on_update",
			condition="argument.get('enabled') == 1"
		)

	account = frappe.get_doc("Apollo Account", account_name)
	if account.status != "Authorized":
		wait_for_event(
			event_key=f"doc:Apollo Account:{account_name}:on_update",
			condition="argument.get('status') == 'Authorized'"
		)

	crm_lead_accounts = frappe.get_all("CRM Lead Apollo ID", filters={"parent": mcc.recipient, "account": account_name}, fields=["apollo_id"])
	if not crm_lead_accounts or not crm_lead_accounts[0].get("apollo_id"):
		wait_for_event(
			event_key=f"doc:CRM Lead:{mcc.recipient}:on_update",
			condition=f"any(row.get('account') == '{account_name}' and row.get('apollo_id') for row in argument.get('apollo_ids', []))"
		)
		crm_lead_accounts = frappe.get_all("CRM Lead Apollo ID", filters={"parent": mcc.recipient, "account": account_name}, fields=["apollo_id"])
		if not crm_lead_accounts or not crm_lead_accounts[0].get("apollo_id"):
			raise SuspendJob("CRM Lead Apollo ID missing.")

	contact_apollo_id = crm_lead_accounts[0].apollo_id

	supported_channels = []
	try:
		provider = frappe.get_doc("Cadence Provider", "Apollo")
		supported_channels = [c.channel for c in (provider.get("channels") or []) if c.channel]
	except Exception:
		supported_channels = []

	cadence = frappe.get_doc("Cadence", mcc.cadence_name)
	target_sch = None
	step_index = 0

	for sch in (cadence.get("cadence_schedules") or []):
		channel = getattr(sch, "channel", None) or (sch.get("channel") if isinstance(sch, dict) else None)
		ref_dt = getattr(sch, "reference_doctype", None) or (sch.get("reference_doctype") if isinstance(sch, dict) else None)
		sch_name = getattr(sch, "name", None) or (sch.get("name") if isinstance(sch, dict) else None)
		if channel in supported_channels or ref_dt == "Email Template" or channel == "Email":
			step_index += 1
			if sch_name == comm.cadence_schedule:
				target_sch = sch
				break

	if not target_sch or step_index == 0:
		wait_for_event(
			event_key=f"doc:Cadence:{mcc.cadence_name}:on_update"
		)
		cadence.reload()
		step_index = 0
		target_sch = None
		for sch in (cadence.get("cadence_schedules") or []):
			channel = getattr(sch, "channel", None) or (sch.get("channel") if isinstance(sch, dict) else None)
			ref_dt = getattr(sch, "reference_doctype", None) or (sch.get("reference_doctype") if isinstance(sch, dict) else None)
			sch_name = getattr(sch, "name", None) or (sch.get("name") if isinstance(sch, dict) else None)
			if channel in supported_channels or ref_dt == "Email Template" or channel == "Email":
				step_index += 1
				if sch_name == comm.cadence_schedule:
					target_sch = sch
					break
		if not target_sch or step_index == 0:
			raise SuspendJob(f"Cadence schedule step {comm.cadence_schedule} missing or not supported.")

	if step_index > 4:
		raise SuspendJob(f"Calculated step index {step_index} exceeds maximum sequence step capacity (4).")

	ref_dt_val = getattr(target_sch, "reference_doctype", None) or (target_sch.get("reference_doctype") if isinstance(target_sch, dict) else None)
	is_email = ref_dt_val == "Email Template"
	subject_field_name = f"subject_{step_index}" if is_email else None
	response_field_name = f"body_{step_index}" if is_email else f"message_{step_index}"

	custom_fields = {}

	if subject_field_name:
		try:
			subject_field = frappe.get_doc("Apollo Field", subject_field_name)
		except frappe.DoesNotExistError:
			wait_for_event(
				event_key=f"doc:Apollo Field:{subject_field_name}:on_update"
			)
			subject_field = frappe.get_doc("Apollo Field", subject_field_name)

		subject_apollo_id = None
		for row in subject_field.get("apollo_ids", []):
			if row.account == account_name and row.apollo_id:
				subject_apollo_id = row.apollo_id
				break

		if not subject_apollo_id:
			wait_for_event(
				event_key=f"doc:Apollo Field:{subject_field_name}:on_update",
				condition=f"any(r.get('account') == '{account_name}' and r.get('apollo_id') for r in argument.get('apollo_ids', []))"
			)
			subject_field.reload()
			for row in subject_field.get("apollo_ids", []):
				if row.account == account_name and row.apollo_id:
					subject_apollo_id = row.apollo_id
					break
			if not subject_apollo_id:
				raise SuspendJob(f"Subject field {subject_field_name} Apollo ID missing for account {account_name}.")

		custom_fields[subject_apollo_id] = comm.subject

	try:
		response_field = frappe.get_doc("Apollo Field", response_field_name)
	except frappe.DoesNotExistError:
		wait_for_event(
			event_key=f"doc:Apollo Field:{response_field_name}:on_update"
		)
		response_field = frappe.get_doc("Apollo Field", response_field_name)

	response_apollo_id = None
	for row in response_field.get("apollo_ids", []):
		if row.account == account_name and row.apollo_id:
			response_apollo_id = row.apollo_id
			break

	if not response_apollo_id:
		wait_for_event(
			event_key=f"doc:Apollo Field:{response_field_name}:on_update",
			condition=f"any(r.get('account') == '{account_name}' and r.get('apollo_id') for r in argument.get('apollo_ids', []))",
		)
		response_field.reload()
		for row in response_field.get("apollo_ids", []):
			if row.account == account_name and row.apollo_id:
				response_apollo_id = row.apollo_id
				break
		if not response_apollo_id:
			raise SuspendJob(
				f"Message/Body field {response_field_name} Apollo ID missing for account {account_name}."
			)

	custom_fields[response_apollo_id] = comm.content

	client = ApolloClient(account_name)
	try:
		client.update_contact(contact_apollo_id, custom_fields)
		comm.db_set("apollo_id", contact_apollo_id)
		comm.db_set("apollo_status", "Scheduled")
	except Exception as e:
		frappe.log_error(title="Failed to sync Communication to Apollo", message=str(e))
		raise

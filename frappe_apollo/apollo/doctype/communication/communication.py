import frappe
from frappe_controller.utils.controller import wait_for_event

def on_update(doc, method=None):
	if doc.get_doc_before_save() and doc.get_doc_before_save().status != "Scheduled" and doc.status == "Scheduled":
		frappe.enqueue(
			method="frappe_apollo.apollo.doctype.communication.communication.update_a_contact",
			queue="medium",
			comm_name=doc.name
		)

def update_a_contact(comm_name):
	from frappe_apollo.integrations.apollo import ApolloClient
	from frappe_controller.utils.controller import SuspendJob
	
	comm = frappe.get_doc("Communication", comm_name)
	
	if comm.get("apollo_sync_status") == "Synced":
		return
		
	mcc = frappe.get_doc("Multi Channel Cadence", comm.reference_name)
	if not mcc.apollo_account or not mcc.apollo_sequence_id:
		wait_for_event(
			event_key="doc:Multi Channel Cadence:on_update",
			condition=f"argument.get('name') == '{mcc.name}' and argument.get('apollo_account') and argument.get('apollo_sequence_id')"
		)
		mcc.reload()
	
	account_name = mcc.apollo_account
	
	is_enabled = frappe.db.get_value("Cadence Provider", "Apollo", "enabled")
	if not is_enabled:
		wait_for_event(
			event_key="doc:Cadence Provider:on_update:Apollo",
			condition="argument.get('enabled') == 1"
		)
		
	account = frappe.get_doc("Apollo Account", account_name)
	if account.status != "Authorized":
		wait_for_event(
			event_key="doc:Apollo Account:on_update",
			condition=f"argument.get('name') == '{account_name}' and argument.get('status') == 'Authorized'"
		)
		
	crm_lead_accounts = frappe.get_all("CRM Lead Apollo ID", filters={"parent": mcc.recipient, "account": account_name}, fields=["apollo_id"])
	if not crm_lead_accounts or not crm_lead_accounts[0].get("apollo_id"):
		wait_for_event(
			event_key=f"doc:CRM Lead:on_update:{mcc.recipient}",
			condition=f"any(row.get('account') == '{account_name}' and row.get('apollo_id') for row in argument.get('apollo_ids', []))"
		)
		# fetch again after event
		crm_lead_accounts = frappe.get_all("CRM Lead Apollo ID", filters={"parent": mcc.recipient, "account": account_name}, fields=["apollo_id"])
		
	contact_apollo_id = crm_lead_accounts[0].apollo_id

	step_found = False
	step_doc = None
	if comm.cadence_schedule:
		cadence = frappe.get_doc("Cadence", mcc.cadence_name)
		for sch in cadence.cadence_schedules:
			if sch.name == comm.cadence_schedule:
				step_found = True
				step_doc = sch
				break

	if not step_found or not step_doc.subject_field or not step_doc.message_field:
		wait_for_event(
			event_key="doc:Cadence:on_update",
			condition=f"argument.get('name') == '{mcc.cadence_name}'"
		)
		
	# Wait for actual Field docs to have the mapped apollo_id for this account
	subject_field = frappe.get_doc("Apollo Field", step_doc.subject_field)
	subject_apollo_id = None
	for row in subject_field.get("apollo_ids", []):
		if row.account == account_name and row.apollo_sequence_id == mcc.apollo_sequence_id:
			subject_apollo_id = row.apollo_id
			break
			
	if not subject_apollo_id:
		wait_for_event(
			event_key="doc:Apollo Field:on_update",
			condition=f"argument.get('name') == '{subject_field.name}'"
		)
		subject_field.reload()
		for row in subject_field.get("apollo_ids", []):
			if row.account == account_name and row.apollo_sequence_id == mcc.apollo_sequence_id:
				subject_apollo_id = row.apollo_id
				break
		
	response_field = frappe.get_doc("Apollo Field", step_doc.message_field)
	response_apollo_id = None
	for row in response_field.get("apollo_ids", []):
		if row.account == account_name and row.apollo_sequence_id == mcc.apollo_sequence_id:
			response_apollo_id = row.apollo_id
			break
			
	if not response_apollo_id:
		wait_for_event(
			event_key="doc:Apollo Field:on_update",
			condition=f"argument.get('name') == '{response_field.name}'"
		)
		response_field.reload()
		for row in response_field.get("apollo_ids", []):
			if row.account == account_name and row.apollo_sequence_id == mcc.apollo_sequence_id:
				response_apollo_id = row.apollo_id
				break
		
	custom_fields = {
		subject_apollo_id: comm.subject,
		response_apollo_id: comm.content
	}
	
	client = ApolloClient(account_name)
	try:
		client.update_contact(contact_apollo_id, custom_fields)
		comm.db_set("apollo_id", contact_apollo_id)
		comm.db_set("apollo_sync_status", "Synced")
	except Exception as e:
		frappe.log_error(title="Failed to sync Communication to Apollo", message=str(e))
		raise

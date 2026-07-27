import frappe
from frappe import _
from frappe_cadence.cadence.doctype.cadence_provider.cadence_provider import report_event

@frappe.whitelist(allow_guest=True)
def handle():
	"""
	Public endpoint for Apollo webhooks.
	"""
	token = frappe.get_request_header("Authorization")
	if not token or not token.startswith("Bearer "):
		frappe.throw(_("Unauthorized"), frappe.AuthenticationError)
		
	bearer_token = token.split(" ")[1]
	
	# Verify token against active Accounts
	accounts = frappe.get_all("Apollo Account", fields=["name", "webhook_bearer_token"])
	authorized = False
	for acc in accounts:
		if acc.webhook_bearer_token and frappe.get_doc("Apollo Account", acc.name).get_password("webhook_bearer_token") == bearer_token:
			authorized = True
			break
			
	if not authorized:
		frappe.throw(_("Unauthorized"), frappe.AuthenticationError)
		
	payload = frappe.request.get_json()
	
	# Enqueue FS Job
	frappe.enqueue(
		method="frappe_apollo.webhook.process_webhook",
		queue="low",
		payload=payload
	)
	
	return {"status": "ok"}

def process_webhook(payload):
	"""
	FS Job: Handles Apollo webhook data asynchronously.
	"""
	event = payload.get("event")
	contact_id = payload.get("contact_id")
	sequence_id = payload.get("emailer_campaign_id")
	
	if not contact_id or not sequence_id:
		return
		
	crm_lead_accounts = frappe.get_all("CRM Lead Apollo ID", filters={"apollo_id": contact_id}, fields=["parent as lead", "account"])
	if not crm_lead_accounts:
		frappe.log_error("contact not found in CRM Lead Apollo ID")
		return
		
	lead_name = crm_lead_accounts[0].lead
	account_name = crm_lead_accounts[0].account
	
	mccs = frappe.get_all("Multi Channel Cadence", filters={
		"recipient": lead_name,
		"apollo_sequence_id": sequence_id,
		"apollo_account": account_name
	}, fields=["name"], order_by="creation desc", limit=1)
	
	if not mccs:
		frappe.log_error("mccs not found")
		return
		
	mcc_name = mccs[0].name
	
	context = {"mcc_name": mcc_name}
	
	if event == "message_sent":
		comms = frappe.get_all("Communication", filters={
			"reference_doctype": "Multi Channel Cadence",
			"reference_name": mcc_name,
			"delivery_status": "Scheduled"
		}, fields=["name"], order_by="creation desc", limit=1)
		
		if comms:
			context["communication_name"] = comms[0].name
			report_event("message_sent", context, payload)
		else:
			frappe.log_error("comms not found")
	elif event == "message_replied":
		report_event("message_replied", context, payload)
		
	elif event == "message_opened":
		comms = frappe.get_all("Communication", filters={
			"reference_doctype": "Multi Channel Cadence",
			"reference_name": mcc_name,
			"delivery_status": "Sent"
		}, fields=["name"], order_by="creation desc", limit=1)
		
		if comms:
			context["communication_name"] = comms[0].name
			report_event("message_opened", context, payload)
			
	elif event == "bounce":
		report_event("bounce", context, payload)
	

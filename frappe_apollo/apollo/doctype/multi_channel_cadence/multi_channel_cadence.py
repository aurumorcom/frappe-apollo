import frappe
from typing import Dict
from frappe_controller.utils.controller import wait_for_event

def before_save(doc, method=None):
	"""
	Load balances Apollo accounts and sequence IDs for a given sender on a Multi Channel Cadence.
	"""
	if not doc.provider or "Apollo" not in [p.cadence_provider for p in doc.get("provider", [])]:
		return

	if not doc.sender:
		return

	if not doc.cadence_name:
		return

	cadence = frappe.get_doc("Cadence", doc.cadence_name)
	
	active_mappings = [
		row for row in cadence.get("apollo_ids", [])
		if row.sender == doc.sender and row.status == "Active" and row.apollo_id
	]
	
	if doc.apollo_account and doc.apollo_sequence_id:
		# If it's a Draft, re-verify the mapping is still valid
		if doc.status == "Draft":
			is_valid = any(
				m.account == doc.apollo_account and m.apollo_id == doc.apollo_sequence_id
				for m in active_mappings
			)
			if is_valid:
				return
			# If invalid, it falls through to re-assignment
		else:
			return
	
	if not active_mappings:
		return
		
	if len(active_mappings) == 1:
		selected_mapping = active_mappings[0]
		doc.apollo_account = selected_mapping.account
		doc.apollo_sequence_id = selected_mapping.apollo_id
	
	# Multiple mappings exist, load balance by counting active MCCs per account
	account_load: Dict[str, int] = {row.account: 0 for row in active_mappings}
	
	# Fetch count of active MCCs for this sender, grouped by apollo_account
	# Note: doc.status can be "Active", "In Progress", etc. Adjust as needed.
	active_mccs = frappe.get_all(
		"Multi Channel Cadence",
		filters={
			"sender": doc.sender,
			"status": ["in", ["Active", "In Progress"]],
			"apollo_account": ["is", "set"]
		},
		fields=["apollo_account"]
	)
	
	for mcc in active_mccs:
		if mcc.apollo_account in account_load:
			account_load[mcc.apollo_account] += 1
			
	# Find the mapping with the lowest load
	selected_mapping = min(
		active_mappings,
		key=lambda x: (account_load.get(x.account, 0), x.name) # tie-breaker by name
	)
	
	doc.apollo_account = selected_mapping.account
	doc.apollo_sequence_id = selected_mapping.apollo_id

def on_update(doc, method=None):
	# If Draft -> Scheduled
	if doc.get_doc_before_save() and doc.get_doc_before_save().status == "Draft" and doc.status == "Scheduled":
		frappe.enqueue(
			method="frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.add_a_contact_to_sequence",
			queue="short",
			mcc_name=doc.name
		)

def add_a_contact_to_sequence(mcc_name):
	frappe.enqueue(
		method="frappe_apollo.apollo.doctype.crm_lead.crm_lead._create_a_contact",
		queue="short",
		mcc_name=mcc_name
	)
	frappe.enqueue(
		method="frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence._assign_contact_to_sequence",
		queue="short",
		mcc_name=mcc_name
	)

def _assign_contact_to_sequence(mcc_name):
	from frappe_apollo.integrations.apollo import ApolloClient
	print("DEBUG _assign: ApolloClient is", ApolloClient)
	
	mcc = frappe.get_doc("Multi Channel Cadence", mcc_name)
	
	# Fail fast if status changed
	if mcc.status not in ["Scheduled", "In Progress", "Active"]:
		return

	is_enabled = frappe.db.get_value("Cadence Provider", "Apollo", "enabled")
	if not is_enabled:
		wait_for_event(
			event_key="doc:Cadence Provider:Apollo:on_update",
			condition="argument.get('enabled') == 1"
		)

	if not mcc.apollo_account or not mcc.apollo_sequence_id:
		wait_for_event(
			event_key=f"doc:Cadence:{mcc.cadence_name}:on_update",
			condition=f"any(row.get('sender') == '{mcc.sender}' and row.get('status') == 'Active' and row.get('apollo_id') for row in argument.get('apollo_ids', []))",
			consider_events_since=mcc.modified
		)
		mcc.reload()
		# Re-validate
		if mcc.status not in ["Scheduled", "In Progress", "Active"]:
			return
		mcc.save(ignore_permissions=True)
		return
		
	sender = mcc.sender
	
	email_account_name = frappe.db.get_value("User Email", {"parent": sender}, "email_account")
	if not email_account_name:
		wait_for_event(
			event_key="doc:User Email:after_insert",
			condition=f"argument.get('parent') == '{sender}'"
		)
		mcc.reload()
		if mcc.status not in ["Scheduled", "In Progress", "Active"]:
			return
		email_account_name = frappe.db.get_value("User Email", {"parent": sender}, "email_account")
		
	email_account = frappe.get_doc("Email Account", email_account_name)
	if not email_account.get("apollo_ids"):
		raise Exception("No Apollo Account mapped to this Email Account.")
	
	# Find mailbox matching the mcc's apollo_account
	account_name = mcc.apollo_account
	apollo_mailbox_id = None
	for row in email_account.get("apollo_ids", []):
		if row.account == account_name:
			apollo_mailbox_id = row.apollo_id
			break
			
	if not apollo_mailbox_id:
		raise Exception(f"No Apollo Mailbox mapped for account {account_name}.")
	
	crm_lead_accounts = frappe.get_all("CRM Lead Apollo ID", filters={"parent": mcc.recipient, "account": account_name}, fields=["apollo_id"])
	if not crm_lead_accounts or not crm_lead_accounts[0].get("apollo_id"):
		wait_for_event(
			event_key=f"doc:CRM Lead:on_update:{mcc.recipient}",
			condition=f"any(row.get('account') == '{account_name}' and row.get('apollo_id') for row in argument.get('apollo_ids', []))"
		)
		mcc.reload()
		if mcc.status not in ["Scheduled", "In Progress", "Active"]:
			return
		# refetch
		crm_lead_accounts = frappe.get_all("CRM Lead Apollo ID", filters={"parent": mcc.recipient, "account": account_name}, fields=["apollo_id"])
		if not crm_lead_accounts or not crm_lead_accounts[0].get("apollo_id"):
			return

	contact_apollo_id = crm_lead_accounts[0].apollo_id

	# Call API
	client = ApolloClient(account_name)
	try:
		client.add_contacts_to_sequence(contact_apollo_id, mcc.apollo_sequence_id, apollo_mailbox_id)
	except Exception as e:
		frappe.log_error(title="Failed to assign sequence in Apollo", message=str(e))
		raise

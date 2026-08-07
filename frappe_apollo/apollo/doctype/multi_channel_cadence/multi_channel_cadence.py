import frappe
from frappe_controller.utils.controller import wait_for_event


def before_save(doc, method=None):
	"""
	Load balances Apollo accounts and sequence IDs for a given sender on a Multi Channel Cadence.
	"""
	if not doc.provider or "Apollo" not in [p.cadence_provider for p in doc.get("provider", [])]:
		return

	if not doc.sender or not doc.cadence_name:
		return

	cadence = frappe.get_doc("Cadence", doc.cadence_name)

	active_mappings = [
		row for row in cadence.get("apollo_ids", [])
		if row.sender == doc.sender and row.status == "Active"
	]

	if doc.apollo_account:
		account_seq_id = frappe.db.get_value("Apollo Account", doc.apollo_account, "apollo_sequence_id")
		if account_seq_id:
			doc.apollo_sequence_id = account_seq_id
		if doc.status == "Draft":
			is_valid = any(
				m.account == doc.apollo_account for m in active_mappings
			)
			if is_valid:
				return
		else:
			return

	if not active_mappings:
		return

	if len(active_mappings) == 1:
		selected_mapping = active_mappings[0]
		doc.apollo_account = selected_mapping.account
		doc.apollo_sequence_id = frappe.db.get_value("Apollo Account", selected_mapping.account, "apollo_sequence_id")
	else:
		account_load: dict[str, int] = {row.account: 0 for row in active_mappings}
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

		selected_mapping = min(
			active_mappings,
			key=lambda x: (account_load.get(x.account, 0), x.name)
		)

		doc.apollo_account = selected_mapping.account
		doc.apollo_sequence_id = frappe.db.get_value("Apollo Account", selected_mapping.account, "apollo_sequence_id")

def _is_contact_in_sequence(doc):
	return bool(getattr(doc, "apollo_contact_id", None) or (isinstance(doc, dict) and doc.get("apollo_contact_id")))


def on_update(doc, method=None):
	before_doc = doc.get_doc_before_save()
	before_status = before_doc.status if before_doc else None

	if before_status == "Draft" and doc.status == "Scheduled":
		frappe.enqueue(
			method="frappe_apollo.apollo.doctype.crm_lead.crm_lead._create_a_contact",
			queue="low",
			mcc_name=doc.name
		)
		frappe.enqueue(
			method="frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.add_contact_to_sequence",
			queue="high",
			mcc_name=doc.name
		)

	went_to_disabled = doc.status == "Disabled" and before_status != "Disabled"
	came_from_disabled = before_status == "Disabled" and doc.status in ["Scheduled", "In Progress"]

	if (went_to_disabled or came_from_disabled) and _is_contact_in_sequence(doc):
		if went_to_disabled:
			frappe.enqueue(
				method="frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.update_sequence_contact_status",
				queue="medium",
				mcc_name=doc.name,
				mode="stop"
			)
		elif came_from_disabled:
			frappe.enqueue(
				method="frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.add_contact_to_sequence",
				queue="high",
				mcc_name=doc.name
			)


def add_contact_to_sequence(mcc_name):
	from frappe_apollo.integrations.apollo import ApolloClient

	mcc = frappe.get_doc("Multi Channel Cadence", mcc_name)

	if mcc.status not in ["Scheduled", "In Progress", "Active"]:
		return

	is_enabled = frappe.db.get_value("Cadence Provider", "Apollo", "enabled")
	if not is_enabled:
		wait_for_event(
			event_key="doc:Cadence Provider:Apollo:on_update",
			condition="argument.get('enabled') == 1"
		)

	if not mcc.apollo_account:
		return

	if not mcc.apollo_sequence_id:
		mcc.apollo_sequence_id = frappe.db.get_value("Apollo Account", mcc.apollo_account, "apollo_sequence_id")

	if not mcc.apollo_sequence_id:
		wait_for_event(
			event_key=f"doc:Apollo Account:{mcc.apollo_account}:on_update",
			condition="argument.get('apollo_sequence_id')"
		)
		mcc.reload()
		if mcc.status not in ["Scheduled", "In Progress", "Active"]:
			return
		mcc.apollo_sequence_id = frappe.db.get_value("Apollo Account", mcc.apollo_account, "apollo_sequence_id")
		if not mcc.apollo_sequence_id:
			return
		mcc.save(ignore_permissions=True)

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

	account_name = mcc.apollo_account
	email_account = frappe.get_doc("Email Account", email_account_name)

	apollo_mailbox_id = None
	for row in email_account.get("apollo_ids", []):
		if row.account == account_name and row.apollo_id:
			apollo_mailbox_id = row.apollo_id
			break

	if not apollo_mailbox_id:
		wait_for_event(
			event_key=f"doc:Email Account:{email_account_name}:on_update",
			condition=f"any(row.get('account') == '{account_name}' and row.get('apollo_id') for row in argument.get('apollo_ids', []))"
		)
		email_account.reload()
		if mcc.status not in ["Scheduled", "In Progress", "Active"]:
			return
		for row in email_account.get("apollo_ids", []):
			if row.account == account_name and row.apollo_id:
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
		crm_lead_accounts = frappe.get_all("CRM Lead Apollo ID", filters={"parent": mcc.recipient, "account": account_name}, fields=["apollo_id"])
		if not crm_lead_accounts or not crm_lead_accounts[0].get("apollo_id"):
			return

	contact_apollo_id = crm_lead_accounts[0].apollo_id

	client = ApolloClient(account_name)
	try:
		client.add_contacts_to_sequence(contact_apollo_id, mcc.apollo_sequence_id, apollo_mailbox_id)
		mcc.db_set("apollo_contact_id", contact_apollo_id)
	except Exception as e:
		frappe.log_error(title="Failed to assign sequence in Apollo", message=str(e))
		raise


def update_sequence_contact_status(mcc_name, mode="stop"):
	from frappe_apollo.integrations.apollo import ApolloClient

	mcc = frappe.get_doc("Multi Channel Cadence", mcc_name)
	if not _is_contact_in_sequence(mcc):
		return

	if not mcc.apollo_account or not mcc.apollo_sequence_id:
		return

	account_name = mcc.apollo_account
	sequence_id = mcc.apollo_sequence_id
	contact_apollo_id = mcc.apollo_contact_id

	client = ApolloClient(account_name)
	try:
		client.update_sequence_contact_status(contact_apollo_id, sequence_id, mode)
	except Exception as e:
		frappe.log_error(title="Failed to update contact status in Apollo sequence", message=str(e))


_stop_contact_in_sequence = update_sequence_contact_status

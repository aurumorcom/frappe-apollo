import frappe


def _create_a_contact(mcc_name):
	from frappe_controller.utils.controller import wait_for_event

	mcc = frappe.get_doc("Multi Channel Cadence", mcc_name)

	# Revalidate
	if mcc.status not in ["Scheduled", "In Progress", "Active"]:
		return

	sender = mcc.sender
	lead_name = mcc.recipient

	# Verify that all expected communications are created
	cadence = frappe.get_doc("Cadence", mcc.cadence_name)
	expected_comms = len(cadence.get("cadence_schedules", []))

	actual_comms = frappe.db.count("Communication", {"reference_doctype": "Multi Channel Cadence", "reference_name": mcc.name})

	if actual_comms < expected_comms:
		wait_for_event(
			event_key="doc:Communication:after_insert",
			condition=f"argument.get('reference_doctype') == 'Multi Channel Cadence' and argument.get('reference_name') == '{mcc.name}'"
		)
		mcc.reload()
		if mcc.status not in ["Scheduled", "In Progress", "Active"]:
			return

	# Find Email Account to get Apollo Account
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

	if not email_account_name:
		return

	email_account = frappe.get_doc("Email Account", email_account_name)
	target_account = mcc.apollo_account
	if not target_account and email_account.get("apollo_ids"):
		target_account = email_account.apollo_ids[0].account

	if not target_account or not email_account.get("apollo_ids"):
		wait_for_event(
			event_key=f"doc:Email Account:{email_account_name}:on_update",
			condition="any(r.get('apollo_id') for r in argument.get('apollo_ids', []))"
		)
		email_account.reload()
		target_account = mcc.apollo_account or (email_account.apollo_ids[0].account if email_account.get("apollo_ids") else None)
		if not target_account:
			raise Exception("No Apollo Account mapped to this Email Account.")

	account_name = target_account

	# Wait for Apollo Settings & Account
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

	# Ensure the CRM Lead has an entry for this account in apollo_ids
	lead = frappe.get_doc("CRM Lead", lead_name)
	apollo_accounts = [acc.account for acc in lead.get("apollo_ids", [])]

	if account_name not in apollo_accounts:
		lead.append("apollo_ids", {
			"account": account_name,
			"apollo_id": ""
		})
		lead.save(ignore_permissions=True)

	# We check if apollo_id is set
	current_row = next((row for row in lead.get("apollo_ids", []) if row.account == account_name), None)
	if current_row:
		if not current_row.apollo_id:
			# Enqueue creation in Apollo
			frappe.enqueue(
				method="frappe_apollo.apollo.doctype.crm_lead.crm_lead.create_a_contact",
				queue="short",
				lead_name=lead_name,
				account_name=account_name
			)

			wait_for_event(
				event_key=f"doc:CRM Lead:{lead_name}:on_update",
				condition=f"any(row.get('account') == '{account_name}' and row.get('apollo_id') for row in argument.get('apollo_ids', []))",
				consider_events_since=lead.modified
			)
		else:
			# Enqueue update
			frappe.enqueue(
				method="frappe_apollo.apollo.doctype.crm_lead.crm_lead.update_a_contact",
				queue="short",
				lead_name=lead_name,
				account_name=account_name
			)


def create_a_contact(lead_name, account_name):
	from frappe_controller.utils.controller import SuspendJob, wait_for_event

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
		account_status = frappe.db.get_value("Apollo Account", account_name, "status")
		if account_status != "Authorized":
			raise SuspendJob("Apollo Account is not Authorized.")

	lead = frappe.get_doc("CRM Lead", lead_name)

	client = ApolloClient(account_name)

	try:
		lead_data = {
			"first_name": lead.first_name,
			"last_name": lead.last_name,
			"email": lead.email,
			"organization_name": lead.organization
		}
		apollo_id = client.create_contact(lead_data)
		if apollo_id:
			# Get latest lead doc because it could be modified
			lead = frappe.get_doc("CRM Lead", lead_name)
			current_row = next((row for row in lead.get("apollo_ids", []) if row.account == account_name), None)
			if current_row:
				current_row.apollo_id = apollo_id
				lead.save(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(title="Failed to create Contact in Apollo", message=str(e))
		raise

def update_a_contact(lead_name, account_name):
	from frappe_controller.utils.controller import SuspendJob, wait_for_event

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
		account_status = frappe.db.get_value("Apollo Account", account_name, "status")
		if account_status != "Authorized":
			raise SuspendJob("Apollo Account is not Authorized.")

	lead = frappe.get_doc("CRM Lead", lead_name)

	current_row = next((row for row in lead.get("apollo_ids", []) if row.account == account_name), None)
	if not current_row or not current_row.apollo_id:
		return

	client = ApolloClient(account_name)

	try:
		lead_data = {
			"first_name": lead.first_name,
			"last_name": lead.last_name,
			"email": lead.email,
			"organization_name": lead.organization
		}
		client.update_contact(current_row.apollo_id, lead_data)
	except Exception as e:
		frappe.log_error(title="Failed to update Contact in Apollo", message=str(e))
		raise

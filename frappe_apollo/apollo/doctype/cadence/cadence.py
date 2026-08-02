import frappe
from frappe_apollo.integrations.apollo import ApolloClient
from frappe_controller.utils.background_jobs import enqueue

def on_update(doc, method=None):
	emailer_steps = _get_sequence_steps(doc.name)

	for row in doc.get("apollo_ids", []):
		if not row.account or not row.sender:
			continue

		enqueue(
			"frappe_apollo.apollo.doctype.cadence.cadence._provision_sequence",
			queue="low",
			cadence_name=doc.name,
			account_name=row.account,
			sender=row.sender,
			emailer_steps=emailer_steps
		)
		
		# Field provisioning per account/schedule
		frappe.get_attr("frappe_apollo.apollo.doctype.apollo_field.apollo_field.enqueue_provision_cadence_fields")(doc.name, row.account, row.sender)

	if doc.has_value_changed("enabled"):
		for row in doc.get("apollo_ids", []):
			if row.account:
				enqueue(
					"frappe_apollo.apollo.doctype.cadence.cadence.update_sequence",
					queue="low",
					cadence_name=doc.name,
					account_name=row.account,
					is_enabled=doc.enabled
				)

def update_sequence(cadence_name, account_name, is_enabled):
	doc = frappe.get_doc("Cadence", cadence_name)
	
	row = next((r for r in doc.get("apollo_ids", []) if r.account == account_name), None)
	if not row or row.status != "Active" or not row.apollo_id:
		return

	client = ApolloClient(row.account)
	try:
		if is_enabled:
			client.approve_sequence(row.apollo_id)
		else:
			client.abort_sequence(row.apollo_id)
	except Exception as e:
		frappe.log_error(f"Failed to {'enable' if is_enabled else 'disable'} Apollo sequence {row.apollo_id} for Cadence {cadence_name}", str(e))

def on_trash(doc, method=None):
	for row in doc.get("apollo_ids", []):
		if row.account and row.apollo_id:
			enqueue(
				"frappe_apollo.apollo.doctype.cadence.cadence.archive_sequence",
				queue="low",
				account_name=row.account,
				apollo_id=row.apollo_id
			)

def archive_sequence(account_name, apollo_id):
	client = ApolloClient(account_name)
	try:
		client.archive_sequence(apollo_id)
	except Exception as e:
		frappe.log_error(f"Failed to archive Apollo sequence {apollo_id}", str(e))

def _provision_sequence(cadence_name, account_name, sender, emailer_steps=None):
	doc = frappe.get_doc("Cadence", cadence_name)
	
	row = next((r for r in doc.get("apollo_ids", []) if r.account == account_name and r.sender == sender), None)
	if not row:
		return
		
	is_enabled = frappe.db.get_value("Cadence Provider", "Apollo", "enabled")
	if not is_enabled:
		from frappe_controller.utils.controller import wait_for_event
		wait_for_event(
			"doc:Cadence Provider:Apollo:on_update",
			condition="argument.get('enabled') == 1",
			consider_events_since=doc.modified
		)
		
		# Re-fetch document and re-validate state upon resumption (Fail Fast)
		doc.reload()
		row = next((r for r in doc.get("apollo_ids", []) if r.account == account_name and r.sender == sender), None)
		if not row:
			return

	account_status = frappe.db.get_value("Apollo Account", account_name, "status")
	if account_status != "Authorized":
		from frappe_controller.utils.controller import wait_for_event
		wait_for_event(
			f"doc:Apollo Account:{account_name}:on_update",
			condition="argument.get('status') == 'Authorized'",
			consider_events_since=doc.modified
		)
		
		# Re-fetch document and re-validate state upon resumption (Fail Fast)
		doc.reload()
		row = next((r for r in doc.get("apollo_ids", []) if r.account == account_name and r.sender == sender), None)
		if not row:
			return
			
	client = ApolloClient(account_name)
	print("DEBUG: Client is", client)
	
	if row.apollo_id:
		if emailer_steps:
			try:
				update_steps = []
				for i, step in enumerate(emailer_steps):
					step_copy = step.copy()
					step_copy["position"] = i + 1
					update_steps.append(step_copy)
				client.update_sequence(row.apollo_id, {"emailer_steps": update_steps})
			except Exception as e:
				frappe.log_error(f"Failed to update Apollo sequence {row.apollo_id} for Cadence {cadence_name}", str(e))
		return
		
	try:
		apollo_id = client.create_sequence(
			name=f"{doc.cadence_name} - {sender}",
			permissions="team_can_use",
			active=True,
			emailer_steps=emailer_steps
		)
		print("DEBUG: created apollo_id:", apollo_id)
		if apollo_id:
			# Reload doc in case it was modified while API request was running
			doc.reload()
			row = next((r for r in doc.get("apollo_ids", []) if r.account == account_name and r.sender == sender), None)
			if row:
				row.apollo_id = apollo_id
				doc.flags.ignore_permissions = True
				doc.save()
	except Exception as e:
		frappe.log_error(f"Failed to create Apollo sequence for Cadence {cadence_name}", str(e))

def _get_sequence_steps(cadence_name):
	doc = frappe.get_doc("Cadence", cadence_name)
	emailer_steps = []
	accumulated_wait = 0
	
	if not doc.get("cadence_schedules"):
		return []
		
	for sch in doc.cadence_schedules:
		accumulated_wait += (sch.send_after_days or 0)
		if sch.reference_doctype == "Email Template":
			# Need subject and message field labels
			subject_field = sch.get("subject_field")
			message_field = sch.get("message_field")
			
			if subject_field and message_field:
				if subject_field.startswith("custom_"):
					subject_field = subject_field[7:]
				if message_field.startswith("custom_"):
					message_field = message_field[7:]

				emailer_touches = [{
					"type": "new_thread",
					"status": "approved",
					"include_signature": True,
					"emailer_template": {
						"subject": f"{{{{{subject_field}}}}}",
						"body_html": f"{{{{{message_field}}}}}"
					}
				}]
				emailer_steps.append({
					"type": "auto_email",
					"wait_time": accumulated_wait,
					"wait_mode": "day",
					"emailer_touches": emailer_touches
				})
				accumulated_wait = 0
				
	return emailer_steps

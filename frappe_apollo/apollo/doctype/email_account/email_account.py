import frappe


def on_update(doc, method=None):
	"""
	Hook fired when an Email Account is created or updated in Frappe.
	Triggers an Apollo mailbox fetch to assign apollo_id if it matches an Apollo mailbox or alias.
	"""
	if getattr(frappe.flags, "is_apollo_email_account_update", False):
		return

	enqueue_get_email_accounts()


@frappe.whitelist()
def enqueue_get_email_accounts():
	"""
	RQ Job: A daily cron job that sweeps all active Accounts and enqueues the FS Job get_email_accounts for each.
	"""
	accounts = frappe.get_all("Apollo Account", fields=["name"])
	method_name = "frappe_apollo.apollo.doctype.email_account.email_account.get_email_accounts"
	for acc in accounts:
		doc = frappe.get_doc("Apollo Account", acc.name)
		if (
			doc.get_password("api_key", raise_exception=False)
			or doc.get_password("access_token", raise_exception=False)
			or doc.access_token
		):
			already_queued = False
			if frappe.db.table_exists("FS Job"):
				already_queued = bool(
					frappe.db.exists(
						"FS Job",
						{
							"job_name": method_name,
							"status": "queued",
							"arguments": ["like", f"%{acc.name}%"],
						},
					)
				)

			if not already_queued:
				frappe.enqueue(
					method=method_name,
					queue="low",
					account_name=acc.name,
				)


queue_get_email_accounts = enqueue_get_email_accounts


def _map_apollo_id_to_email_account(email_id, account_name, apollo_id, create_if_missing=False):
	email_account_name = frappe.db.get_value("Email Account", {"email_id": email_id}, "name") or (
		email_id if frappe.db.exists("Email Account", email_id) else None
	)

	if email_account_name:
		doc = frappe.get_doc("Email Account", email_account_name)
		account_found = False
		for acc in doc.get("apollo_ids", []):
			if acc.account == account_name:
				account_found = True
				if acc.apollo_id != apollo_id:
					acc.apollo_id = apollo_id
					doc.save(ignore_permissions=True)
				break

		if not account_found:
			doc.append("apollo_ids", {"account": account_name, "apollo_id": apollo_id})
			doc.save(ignore_permissions=True)
	elif create_if_missing:
		doc = frappe.get_doc(
			{
				"doctype": "Email Account",
				"email_account_name": email_id,
				"email_id": email_id,
				"service": "Apollo",
				"enable_outgoing": 0,
				"enable_incoming": 0,
				"apollo_ids": [{"account": account_name, "apollo_id": apollo_id}],
			}
		)
		doc.insert(ignore_permissions=True)


def get_email_accounts(account_name):
	"""
	FS Job: Uses ApolloClient.get_email_accounts() to fetch mailboxes.
	Upserts Email Account records in Frappe with apollo_ids mapping for primary and alias addresses.
	"""
	from frappe_apollo.integrations.apollo import ApolloClient

	frappe.flags.is_apollo_email_account_update = True
	try:
		client = ApolloClient(account_name)
		mailboxes = client.get_email_accounts()
		for mb in mailboxes.get("email_accounts") or []:
			if not mb.get("active"):
				continue

			primary_email = mb.get("email")
			if not primary_email:
				continue

			apollo_id = mb.get("id")

			# Map primary email account (create if missing)
			_map_apollo_id_to_email_account(primary_email, account_name, apollo_id, create_if_missing=True)

			# Map all alias email accounts (only if already created)
			aliases = mb.get("aliases") or []
			for alias in aliases:
				if alias and alias != primary_email:
					_map_apollo_id_to_email_account(alias, account_name, apollo_id, create_if_missing=False)
	except Exception:
		frappe.log_error(f"Failed to get mailboxes for {account_name}", "Apollo Integration")
		raise
	finally:
		frappe.flags.is_apollo_email_account_update = False


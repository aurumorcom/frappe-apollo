import frappe


@frappe.whitelist()
def queue_get_email_accounts():
    """
    RQ Job: A daily cron job that sweeps all active Accounts and enqueues the FS Job get_email_accounts for each.
    """
    accounts = frappe.get_all("Apollo Account", fields=["name"])
    for acc in accounts:
        doc = frappe.get_doc("Apollo Account", acc.name)
        if doc.get_password("api_key", raise_exception=False) or doc.access_token:
            frappe.enqueue(
                method="frappe_apollo.apollo.doctype.email_account.email_account.get_email_accounts",
                queue="low",
                account_name=acc.name
            )

def get_email_accounts(account_name):
    """
    FS Job: Uses ApolloClient.get_email_accounts() to fetch mailboxes.
    Upserts Email Account records in Frappe with apollo_ids mapping.
    """
    from frappe_apollo.integrations.apollo import ApolloClient

    client = ApolloClient(account_name)
    try:
        mailboxes = client.get_email_accounts()
        for mb in mailboxes.get("email_accounts", []):
            if not mb.get("active"):
                continue

            email_id = mb.get("email")
            if not email_id:
                continue

            email_account_name = frappe.db.get_value("Email Account", {"email_id": email_id}, "name")
            apollo_id = mb.get("id")

            if email_account_name:
                doc = frappe.get_doc("Email Account", email_account_name)
                # Check if account is already mapped
                account_found = False
                for acc in doc.get("apollo_ids", []):
                    if acc.account == account_name:
                        account_found = True
                        if acc.apollo_id != apollo_id:
                            acc.apollo_id = apollo_id
                            doc.save(ignore_permissions=True)
                        break

                if not account_found:
                    doc.append("apollo_ids", {
                        "account": account_name,
                        "apollo_id": apollo_id
                    })
                    doc.save(ignore_permissions=True)
            else:
                doc = frappe.get_doc({
                    "doctype": "Email Account",
                    "email_id": email_id,
                    "service": "Apollo",
                    "enable_outgoing": 0,
                    "enable_incoming": 0,
                    "apollo_ids": [
                        {
                            "account": account_name,
                            "apollo_id": apollo_id
                        }
                    ]
                })
                doc.insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(f"Failed to get mailboxes for {account_name}", "Apollo Integration")
        raise

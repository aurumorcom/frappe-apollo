from urllib.parse import urlparse, urlunparse

import frappe
from frappe.model.document import Document


class ApolloAccount(Document):
	def on_update(self):
		if self.has_value_changed("status") and self.status == "Authorized":
			frappe.enqueue(
				"frappe_apollo.apollo.doctype.apollo_account.apollo_account.provision_sequence",
				queue="low",
				account_name=self.name,
			)

	def after_insert(self):
		frappe.enqueue(
			method="frappe_apollo.apollo.doctype.email_account.email_account.get_email_accounts",
			queue="low",
			account_name=self.name,
		)

	@frappe.whitelist()
	def get_authorization_url(self):
		raw_uri = frappe.utils.get_url("/api/method/frappe_apollo.oauth.callback")
		parsed = urlparse(raw_uri)
		redirect_uri = urlunparse(parsed._replace(netloc=parsed.hostname))

		url = f"https://app.apollo.io/#/oauth/authorize?client_id={self.client_id}&redirect_uri={redirect_uri}&response_type=code&state={self.name}"
		return url

	@frappe.whitelist()
	def clear_tokens(self):
		self.access_token = None
		self.refresh_token = None
		self.expired = None
		self.status = "Unauthorized"
		self.save()


def provision_sequence(account_name):
	import requests

	from frappe_apollo.integrations.apollo import ApolloClient

	account_status = frappe.db.get_value("Apollo Account", account_name, "status")
	if account_status != "Authorized":
		frappe.wait_for_event(
			event_key=f"doc:Apollo Account:{account_name}:on_update",
			condition="argument.get('status') == 'Authorized'",
		)

	existing_seq_id = frappe.db.get_value("Apollo Account", account_name, "apollo_sequence_id")
	if existing_seq_id:
		return

	client = ApolloClient(account_name)
	try:
		res = client.search_sequences(q_name="Cadence from Frappe")
		sequence_id = None
		if isinstance(res, dict) and "emailer_campaigns" in res:
			for campaign in res.get("emailer_campaigns") or []:
				if campaign.get("name") == "Cadence from Frappe":
					sequence_id = campaign.get("id")
					break

		if not sequence_id:
			sequence_id = client.create_sequence(name="Cadence from Frappe", active=True, emailer_steps=[])

		if sequence_id:
			doc = frappe.get_doc("Apollo Account", account_name)
			doc.db_set("apollo_sequence_id", sequence_id)
			doc.notify_update()
	except requests.exceptions.HTTPError as e:
		if e.response is not None and e.response.status_code in (401, 403):
			frappe.log_error(
				f"Apollo sequence provisioning failed due to insufficient permissions for account {account_name}: {e}",
				"Apollo Sequence Provisioning Warning",
			)
			return
		raise

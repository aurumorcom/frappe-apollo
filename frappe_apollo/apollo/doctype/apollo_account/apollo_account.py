import frappe
from frappe.model.document import Document
from urllib.parse import urlparse, urlunparse

class ApolloAccount(Document):
	def on_update(self):
		pass
			
	def after_insert(self):
		frappe.enqueue(
			method="frappe_apollo.apollo.doctype.email_account.email_account.get_email_accounts",
			queue="low",
			account_name=self.name
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


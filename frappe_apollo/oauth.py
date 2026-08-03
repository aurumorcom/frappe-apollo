from urllib.parse import urlparse, urlunparse

import frappe
import requests
from frappe import _


@frappe.whitelist(allow_guest=True)
def callback(code, state=None):
	"""
	Public endpoint for OAuth authorization callback.
	"""
	if not code:
		frappe.throw(_("Authorization code missing"))

	# Identify Account via state (which should be account_name)
	account_name = state
	if not account_name:
		frappe.throw(_("State (account name) missing"))

	account = frappe.get_doc("Apollo Account", account_name)


	raw_uri = frappe.utils.get_url("/api/method/frappe_apollo.oauth.callback")
	parsed = urlparse(raw_uri)
	redirect_uri = urlunparse(parsed._replace(netloc=parsed.hostname))

	url = "https://app.apollo.io/api/v1/oauth/token"
	payload = {
		"grant_type": "authorization_code",
		"code": code,
		"client_id": account.client_id,
		"client_secret": account.get_password("client_secret"),
		"redirect_uri": redirect_uri
	}

	response = requests.post(url, data=payload)
	response.raise_for_status()
	data = response.json()

	account.access_token = data.get("access_token")
	account.refresh_token = data.get("refresh_token")

	expires_in = data.get("expires_in")
	if expires_in:
		account.expired = frappe.utils.add_to_date(frappe.utils.now_datetime(), seconds=int(expires_in))

	account.status = "Authorized"

	account.save(ignore_permissions=True)
	frappe.db.commit()

	# Redirect back to Account form
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = f"/app/apollo-account/{account_name}"

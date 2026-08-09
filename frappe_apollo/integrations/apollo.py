from datetime import datetime

import frappe
import requests
from frappe.model.document import Document


class ApolloRateLimitError(Exception):
	pass

class ApolloClient:
	base_url = "https://api.apollo.io/api/v1"

	def __init__(self, account_name):
		self.account_name = account_name
		self.account = frappe.get_doc("Apollo Account", account_name)

	def get_email_accounts(self):
		endpoint = "/email_accounts"
		return self._request("GET", endpoint)

	def get_sequence(self, sequence_id):
		page = 1
		total_pages = 1
		while page <= total_pages:
			res = self.search_sequences(page=page, per_page=100)
			if isinstance(res, dict) and "emailer_campaigns" in res:
				pagination = res.get("pagination") or {}
				total_pages = pagination.get("total_pages") or 1
				for campaign in res.get("emailer_campaigns") or []:
					if campaign.get("id") == sequence_id:
						return {
							"emailer_campaign": campaign,
							"emailer_steps": campaign.get("emailer_steps") or []
						}
			page += 1
		return {"emailer_campaign": {}, "emailer_steps": []}

	def create_sequence(self, name, permissions="team_can_use", active=True, emailer_steps=None):
		payload = {
			"name": name,
			"permissions": permissions,
			"active": active
		}
		if emailer_steps:
			payload["emailer_steps"] = emailer_steps

		try:
			res = self._request("POST", "/sequences", json=payload)
		except requests.exceptions.HTTPError as e:
			if e.response is not None and e.response.status_code in (404, 405):
				res = self._request("POST", "/emailer_campaigns", json=payload)
			else:
				raise
		if isinstance(res, dict):
			if "emailer_campaign" in res and isinstance(res["emailer_campaign"], dict):
				return res["emailer_campaign"].get("id")
			elif "sequence" in res and isinstance(res["sequence"], dict):
				return res["sequence"].get("id")
			elif "id" in res:
				return res.get("id")
		return None

	def update_sequence(self, sequence_id, updates):
		try:
			return self._request("PUT", f"/sequences/{sequence_id}", json=updates)
		except requests.exceptions.HTTPError as e:
			if e.response is not None and e.response.status_code in (404, 405):
				return self._request("PUT", f"/emailer_campaigns/{sequence_id}", json=updates)
			raise

	def approve_sequence(self, sequence_id):
		return self.update_sequence(sequence_id, {"active": True})

	def abort_sequence(self, sequence_id):
		return self.update_sequence(sequence_id, {"active": False})

	def archive_sequence(self, sequence_id):
		endpoint = f"/emailer_campaigns/{sequence_id}/archive"
		return self._request("POST", endpoint)

	def search_sequences(self, q_name=None, page=1, per_page=25):
		endpoint = "/emailer_campaigns/search"
		payload = {
			"page": page,
			"per_page": per_page
		}
		if q_name:
			payload["q_name"] = q_name
		return self._request("POST", endpoint, json=payload)

	def create_contact(self, email, first_name=None, last_name=None, title=None, organization_name=None, custom_fields=None):
		endpoint = "/contacts"
		if isinstance(email, dict):
			payload = email
		else:
			payload = {
				"email": email,
				"first_name": first_name,
				"last_name": last_name,
				"title": title,
				"organization_name": organization_name
			}
			if custom_fields:
				payload["typed_custom_fields"] = custom_fields
		return self._request("POST", endpoint, json=payload)

	def update_contact(self, contact_id, custom_fields):
		if isinstance(contact_id, dict) and "id" in contact_id:
			contact_id = contact_id["id"]
		endpoint = f"/contacts/{contact_id}"
		payload = {
			"typed_custom_fields": custom_fields
		}
		try:
			return self._request("PATCH", endpoint, json=payload)
		except requests.exceptions.HTTPError as e:
			if e.response is not None and e.response.status_code in (404, 405):
				return self._request("PUT", endpoint, json=payload)
			raise

	def add_contacts_to_sequence(self, contact_id, sequence_id, mailbox_id):
		endpoint = f"/emailer_campaigns/{sequence_id}/add_contact_ids"
		payload = {
			"contact_ids": [contact_id],
			"emailer_campaign_id": sequence_id,
			"send_email_from_email_account_id": mailbox_id
		}
		try:
			return self._request("POST", endpoint, json=payload)
		except requests.exceptions.HTTPError as e:
			if e.response is not None and e.response.status_code in (400, 422, 404, 405):
				params = {
					"contact_ids[]": contact_id,
					"emailer_campaign_id": sequence_id,
					"send_email_from_email_account_id": mailbox_id
				}
				return self._request("POST", endpoint, params=params)
			raise

	def create_custom_field(self, label, field_type="string"):
		payload = {
			"label": label,
			"type": field_type,
			"modality": "contact"
		}
		return self._request("POST", "/fields", json=payload)

	def update_sequence_contact_status(self, person_id, sequence_id, action):
		endpoint = "/emailer_campaigns/remove_or_stop_contact_ids"
		payload = {
			"contact_ids[]": [person_id],
			"emailer_campaign_ids[]": [sequence_id],
			"mode": action
		}
		return self._request("POST", endpoint, json=payload)

	def _request(self, method, endpoint, **kwargs):
		expired_dt = self.account.get("expired")
		if self.account.refresh_token and expired_dt and isinstance(expired_dt, datetime) and expired_dt < frappe.utils.now_datetime():
			self._refresh_oauth_token()

		url = f"{self.base_url}{endpoint}"
		headers = self._get_headers()

		response = requests.request(method, url, headers=headers, **kwargs)

		if response.status_code == 401 and self.account.refresh_token:
			self._refresh_oauth_token()
			headers = self._get_headers()
			response = requests.request(method, url, headers=headers, **kwargs)

		if response.status_code == 429:
			raise ApolloRateLimitError("Apollo API rate limit exceeded")

		response.raise_for_status()
		return response.json()

	def _get_headers(self):
		headers = {
			"Cache-Control": "no-cache",
			"Content-Type": "application/json"
		}
		api_key = self.account.get_password("api_key", raise_exception=False)
		if api_key:
			headers["X-Api-Key"] = api_key
		elif self.account.access_token:
			headers["Authorization"] = f"Bearer {self.account.get_password('access_token', raise_exception=False)}"
		return headers

	def _refresh_oauth_token(self):
		url = "https://api.apollo.io/api/v1/oauth/token"
		payload = {
			"grant_type": "refresh_token",
			"refresh_token": self.account.get_password("refresh_token", raise_exception=False),
			"client_id": self.account.client_id,
			"client_secret": self.account.get_password("client_secret", raise_exception=False)
		}
		response = requests.post(url, data=payload)
		try:
			response.raise_for_status()
		except requests.exceptions.HTTPError as e:
			if response.status_code in (400, 401, 403):
				self.account.status = "Unauthorized"
				self.account.access_token = None
				self.account.refresh_token = None
				self.account.save(ignore_permissions=True)
				frappe.db.commit()
				frappe.log_error(f"Apollo OAuth token refresh failed for account {self.account_name}", str(e))
			raise

		data = response.json()

		self.account.access_token = data.get("access_token")
		self.account.refresh_token = data.get("refresh_token")

		expires_in = data.get("expires_in")
		if expires_in:
			self.account.expired = frappe.utils.add_to_date(
				frappe.utils.now_datetime(), seconds=int(expires_in)
			)

		self.account.status = "Authorized"
		self.account.save(ignore_permissions=True)
		frappe.db.commit()

import frappe
import requests
import json
from frappe import _

class ApolloRateLimitError(Exception):
	pass

class ApolloClient:
	def __init__(self, account_name):
		self.account_name = account_name
		self.account = frappe.get_doc("Apollo Account", account_name)
		self.base_url = "https://api.apollo.io/api/v1"
		
	def get_email_accounts(self):
		return self._request("GET", "/email_accounts")
		
	def search_sequences(self, q_name=None, page=1, per_page=10):
		payload = {
			"page": page,
			"per_page": per_page
		}
		if q_name:
			payload["q_name"] = q_name
		return self._request("POST", "/emailer_campaigns/search", json=payload)
		
	def create_sequence(self, name, permissions="team_can_use", active=True, emailer_steps=None):
		payload = {
			"name": name,
			"permissions": permissions,
			"active": active
		}
		if emailer_steps:
			payload["emailer_steps"] = emailer_steps
		res = self._request("POST", "/sequences", json=payload)
		return res.get("emailer_campaign", {}).get("id")
		
	def update_sequence(self, sequence_id, payload):
		return self._request("PUT", f"/sequences/{sequence_id}", json=payload)
		
	def approve_sequence(self, sequence_id):
		return self._request("POST", f"/emailer_campaigns/{sequence_id}/approve")

	def abort_sequence(self, sequence_id):
		return self._request("POST", f"/emailer_campaigns/{sequence_id}/abort")

	def archive_sequence(self, sequence_id):
		return self._request("POST", f"/emailer_campaigns/{sequence_id}/archive")

	def create_contact(self, lead_data):
		# Recommendation: run_dedupe=True
		lead_data["run_dedupe"] = True
		res = self._request("POST", "/contacts", json=lead_data)
		return res.get("contact", {}).get("id")
		
	def update_contact(self, person_id, custom_fields):
		payload = {"typed_custom_fields": custom_fields}
		return self._request("PATCH", f"/contacts/{person_id}", json=payload)
		
	def add_contacts_to_sequence(self, person_id, sequence_id, mailbox_id):
		endpoint = f"/emailer_campaigns/{sequence_id}/add_contact_ids"
		payload = {
			"contact_ids[]": [person_id],
			"emailer_campaign_id": sequence_id,
			"send_email_from_email_account_id": mailbox_id
		}
		# Try JSON first, fallback to params if 422
		try:
			return self._request("POST", endpoint, json=payload)
		except requests.exceptions.HTTPError as e:
			if e.response.status_code == 422:
				return self._request("POST", endpoint, params=payload)
			raise
			
	def create_custom_field(self, label, field_type):
		payload = {
			"label": label,
			"type": field_type,
			"modality": "contact"
		}
		return self._request("POST", "/fields", json=payload)
		
	def update_contact_status_sequence(self, person_id, sequence_id, action):
		endpoint = "/emailer_campaigns/remove_or_stop_contact_ids"
		payload = {
			"contact_ids[]": [person_id],
			"emailer_campaign_ids[]": [sequence_id],
			"mode": action
		}
		return self._request("POST", endpoint, json=payload)

	def _request(self, method, endpoint, **kwargs):
		if self.account.refresh_token and self.account.get("expired") and self.account.get("expired") < frappe.utils.now_datetime():
			self._refresh_oauth_token()
			
		url = f"{self.base_url}{endpoint}"
		headers = self._get_headers()
		
		response = requests.request(method, url, headers=headers, **kwargs)
		
		if response.status_code == 401 and self.account.refresh_token:
			# Token might be expired, try to refresh
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
		if self.account.api_key:
			headers["X-Api-Key"] = self.account.api_key
		elif self.account.access_token:
			headers["Authorization"] = f"Bearer {self.account.get_password('access_token')}"
		return headers

	def _refresh_oauth_token(self):
		url = "https://app.apollo.io/api/v1/oauth/token"
		payload = {
			"grant_type": "refresh_token",
			"refresh_token": self.account.get_password("refresh_token"),
			"client_id": self.account.client_id,
			"client_secret": self.account.get_password("client_secret")
		}
		response = requests.post(url, data=payload)
		response.raise_for_status()
		data = response.json()
		
		self.account.access_token = data.get("access_token")
		self.account.refresh_token = data.get("refresh_token")
		
		expires_in = data.get("expires_in")
		if expires_in:
			self.account.expired = frappe.utils.add_to_date(frappe.utils.now_datetime(), seconds=int(expires_in))
			
		self.account.status = "Authorized"
		self.account.save(ignore_permissions=True)
		frappe.db.commit()

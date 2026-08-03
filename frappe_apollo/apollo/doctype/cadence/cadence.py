import frappe
from frappe_controller.utils.background_jobs import enqueue

from frappe_apollo.integrations.apollo import ApolloClient


def on_update(doc, method=None):
	for row in doc.get("apollo_ids", []):
		if not row.account:
			continue

		_validate_for_sequence(doc, row.account)

		frappe.get_attr("frappe_apollo.apollo.doctype.apollo_field.apollo_field.enqueue_provision_cadence_fields")(
			doc.name, row.account, row.get("sender")
		)

	if doc.has_value_changed("enabled") and not doc.enabled:
		enqueue(
			"frappe_apollo.apollo.doctype.cadence.cadence._disable_cadence_mccs",
			queue="low",
			cadence_name=doc.name
		)

def _get_supported_channels():
	try:
		provider = frappe.get_doc("Cadence Provider", "Apollo")
		return [c.channel for c in (provider.get("channels") or []) if c.channel]
	except Exception:
		return ["Email"]

def _validate_for_sequence(doc, account_name):
	supported_channels = _get_supported_channels()
	required_steps = 0
	for sch in (doc.get("cadence_schedules") or []):
		channel = getattr(sch, "channel", None) or sch.get("channel")
		ref_dt = getattr(sch, "reference_doctype", None) or sch.get("reference_doctype")
		if channel in supported_channels or ref_dt == "Email Template" or channel == "Email":
			required_steps += 1

	if required_steps == 0:
		return

	apollo_sequence_id = frappe.db.get_value("Apollo Account", account_name, "apollo_sequence_id")
	if not apollo_sequence_id:
		frappe.msgprint(
			f"Apollo Account {account_name} does not have a configured Apollo Sequence ID. Disabling cadence.",
			alert=True
		)
		doc.enabled = 0
		if hasattr(doc, "db_set"):
			doc.db_set("enabled", 0)
		return

	client = ApolloClient(account_name)
	try:
		sequence_info = client.get_sequence(apollo_sequence_id)
		emailer_steps = (
			sequence_info.get("emailer_steps", [])
			if isinstance(sequence_info, dict) and "emailer_steps" in sequence_info
			else (sequence_info.get("sequence", {}).get("emailer_steps", []) if isinstance(sequence_info, dict) else [])
		)
		current_steps = len(emailer_steps)
	except Exception as e:
		frappe.msgprint(
			f"Failed to fetch sequence details for Apollo Account {account_name}: {e!s}. Disabling cadence.",
			alert=True
		)
		doc.enabled = 0
		if hasattr(doc, "db_set"):
			doc.db_set("enabled", 0)
		return

	if required_steps > current_steps:
		frappe.msgprint(
			f"Cadence required steps ({required_steps}) exceed Apollo sequence capacity ({current_steps}). Disabling cadence.",
			alert=True
		)
		doc.enabled = 0
		if hasattr(doc, "db_set"):
			doc.db_set("enabled", 0)

def _disable_cadence_mccs(cadence_name):
	active_mccs = frappe.get_all(
		"Multi Channel Cadence",
		filters={
			"cadence_name": cadence_name,
			"status": ["in", ["Scheduled", "In Progress", "Active"]]
		},
		fields=["name"]
	)
	for mcc in active_mccs:
		mcc_name = mcc.get("name") if isinstance(mcc, dict) else getattr(mcc, "name", None)
		if not mcc_name:
			continue
		mcc_doc = frappe.get_doc("Multi Channel Cadence", mcc_name)
		mcc_doc.status = "Disabled"
		mcc_doc.save(ignore_permissions=True)
		from frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence import (
			_stop_contact_in_sequence,
		)
		_stop_contact_in_sequence(mcc_name, mode="stop")

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from frappe_apollo.apollo.doctype.communication.communication import on_update, update_a_contact


class TestCommunicationOverride(UnitTestCase):
	@patch("frappe.enqueue")
	def test_on_update_enqueues_when_status_changes_to_scheduled(self, mock_enqueue):
		mock_doc = MagicMock()
		mock_doc_before = MagicMock()
		mock_doc_before.status = "Draft"
		mock_doc.get_doc_before_save.return_value = mock_doc_before
		mock_doc.status = "Scheduled"
		mock_doc.name = "Comm-1"

		on_update(mock_doc)

		mock_enqueue.assert_called_once_with(
			method="frappe_apollo.apollo.doctype.communication.communication.update_a_contact",
			queue="medium",
			comm_name="Comm-1",
		)

	@patch("frappe.get_doc")
	def test_idempotency(self, mock_get_doc):
		mock_comm = MagicMock()
		mock_comm.get.return_value = "Scheduled"
		mock_get_doc.return_value = mock_comm

		update_a_contact("Comm-1")
		self.assertEqual(mock_get_doc.call_count, 1)

	@patch("frappe_apollo.apollo.doctype.communication.communication.wait_for_event")
	@patch("frappe.get_doc")
	def test_wait_state_mcc(self, mock_get_doc, mock_wait):
		mock_wait.side_effect = SuspendJob("Suspended")

		mock_comm = MagicMock()
		mock_comm.get.return_value = None
		mock_mcc = MagicMock()
		mock_mcc.sender = "user@example.com"
		mock_mcc.apollo_account = None

		mock_get_doc.side_effect = [mock_comm, mock_mcc]

		with self.assertRaises(SuspendJob):
			update_a_contact("Comm-1")

		mock_wait.assert_called_once_with(
			event_key=f"doc:Multi Channel Cadence:{mock_mcc.name}:on_update",
			condition="argument.get('apollo_account') and argument.get('apollo_sequence_id')",
		)

	@patch("frappe_apollo.integrations.apollo.ApolloClient")
	@patch("frappe.get_all")
	@patch("frappe.db.get_value")
	@patch("frappe.get_doc")
	def test_success_dynamic_step_indexing(self, mock_get_doc, mock_get_value, mock_get_all, mock_client_cls):
		mock_comm = MagicMock()
		mock_comm.get.return_value = None
		mock_comm.content = "content body 1"
		mock_comm.subject = "subject line 1"
		mock_comm.cadence_schedule = "Sch-1"

		mock_mcc = MagicMock()
		mock_mcc.name = "MCC-1"
		mock_mcc.sender = "user@example.com"
		mock_mcc.cadence_name = "Cadence-1"
		mock_mcc.recipient = "Lead-1"
		mock_mcc.apollo_account = "Acc-1"
		mock_mcc.apollo_sequence_id = "Seq-1"

		mock_account = MagicMock(status="Authorized")

		mock_provider = MagicMock()
		mock_chan = MagicMock(channel="Email")
		mock_provider.get.return_value = [mock_chan]

		mock_cadence = MagicMock()
		mock_sch1 = MagicMock(reference_doctype="Email Template", channel="Email")
		mock_sch1.name = "Sch-1"
		mock_cadence.get.side_effect = lambda k, d=[]: [mock_sch1] if k == "cadence_schedules" else d

		mock_subject_field = MagicMock()
		mock_subject_row = MagicMock(account="Acc-1", apollo_id="apollo-subject-1")
		mock_subject_field.get.return_value = [mock_subject_row]

		mock_response_field = MagicMock()
		mock_response_row = MagicMock(account="Acc-1", apollo_id="apollo-body-1")
		mock_response_field.get.return_value = [mock_response_row]

		mock_get_doc.side_effect = [
			mock_comm,
			mock_mcc,
			mock_account,
			mock_provider,
			mock_cadence,
			mock_subject_field,
			mock_response_field,
		]

		mock_get_value.side_effect = lambda dt, *args: 1 if dt == "Cadence Provider" else None
		mock_get_all.side_effect = lambda dt, *args, **kwargs: (
			[MagicMock(apollo_id="apollo-person-1")] if dt == "CRM Lead Apollo ID" else []
		)

		mock_client = mock_client_cls.return_value

		update_a_contact("Comm-1")

		mock_client.update_contact.assert_called_once_with(
			"apollo-person-1", {"apollo-subject-1": "subject line 1", "apollo-body-1": "content body 1"}
		)

	@patch("frappe.get_all")
	@patch("frappe.db.get_value")
	@patch("frappe.get_doc")
	def test_out_of_bounds_step_index_raises_suspend_job(self, mock_get_doc, mock_get_value, mock_get_all):
		mock_comm = MagicMock()
		mock_comm.get.return_value = None
		mock_comm.cadence_schedule = "Sch-5"

		mock_mcc = MagicMock(
			sender="user@example.com",
			cadence_name="Cad-1",
			recipient="Lead-1",
			apollo_account="Acc-1",
			apollo_sequence_id="Seq-1",
		)
		mock_account = MagicMock(status="Authorized")

		mock_provider = MagicMock()
		mock_chan = MagicMock(channel="Email")
		mock_provider.get.return_value = [mock_chan]

		mock_cadence = MagicMock()
		schedules = []
		for i in range(1, 6):
			m = MagicMock(reference_doctype="Email Template", channel="Email")
			m.name = f"Sch-{i}"
			schedules.append(m)
		mock_cadence.get.side_effect = lambda k, d=[]: schedules if k == "cadence_schedules" else d

		mock_get_doc.side_effect = [mock_comm, mock_mcc, mock_account, mock_provider, mock_cadence]
		mock_get_value.side_effect = lambda dt, *args: 1 if dt == "Cadence Provider" else None
		mock_get_all.side_effect = lambda dt, *args, **kwargs: (
			[MagicMock(apollo_id="p-1")] if dt == "CRM Lead Apollo ID" else []
		)

		with self.assertRaises(SuspendJob) as ctx:
			update_a_contact("Comm-1")

		self.assertIn("exceeds maximum sequence step capacity", str(ctx.exception))

import os
import unittest

import frappe
from frappe.tests import IntegrationTestCase

from frappe_apollo.apollo.doctype.apollo_field.apollo_field import provision_a_field
from frappe_apollo.apollo.doctype.cadence.cadence import (
    _disable_cadence_mccs,
    _validate_for_sequence,
    on_update,
)
from frappe_apollo.tests.integration.external.conftest import my_vcr


class TestCadenceProvisioningExternal(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_name = frappe.conf.get("apollo_test_account") or os.environ.get("APOLLO_TEST_ACCOUNT")
        if cls.account_name and frappe.db.exists("Apollo Account", cls.account_name):
            doc = frappe.get_doc("Apollo Account", cls.account_name)
            try:
                if not doc.get_password("api_key") and not doc.access_token:
                    cls.account_name = None
            except Exception:
                cls.account_name = None

        if not cls.account_name:
            cls.account_name = "Dummy VCR Account"

    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        if not frappe.db.exists("Cadence Provider", "Apollo"):
            frappe.get_doc({
                "doctype": "Cadence Provider",
                "provider_name": "Apollo",
                "enabled": 1
            }).insert(ignore_permissions=True)
        else:
            frappe.db.set_value("Cadence Provider", "Apollo", "enabled", 1)

        if self.account_name == "Dummy VCR Account" and not frappe.db.exists("Apollo Account", self.account_name):
            doc = frappe.get_doc({
                "doctype": "Apollo Account",
                "account_name": self.account_name,
                "apollo_sequence_id": "6a5aecd3bcbdfc0020ac5853",
                "api_key": "dummy_api_key_for_vcr",
                "client_id": "dummy_client_id",
                "client_secret": "dummy_client_secret",
                "status": "Authorized"
            }).insert()

        for acc in frappe.get_all("Apollo Account", filters={"name": ["!=", self.account_name]}):
            frappe.db.set_value("Apollo Account", acc.name, "status", "Unauthorized")
        frappe.db.set_value("Apollo Account", self.account_name, "status", "Authorized")
        frappe.db.set_value("Apollo Account", self.account_name, "apollo_sequence_id", "6a5aecd3bcbdfc0020ac5853")

    def tearDown(self):
        frappe.db.rollback()
        super().tearDown()

    def _skip_if_no_cassette(self, cassette_name):
        if not frappe.conf.get("apollo_test_account") and not os.environ.get("APOLLO_TEST_ACCOUNT"):
            cassette_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'integrations', 'cassettes', cassette_name)
            if not os.path.exists(cassette_path):
                self.skipTest("No credentials and no cassette found for this test.")

    @my_vcr.use_cassette('test_create_cadence.yaml')
    def test_create_cadence(self):
        self._skip_if_no_cassette('test_create_cadence.yaml')

        if not frappe.db.exists("Email Template", "Test Template"):
            tmpl = frappe.get_doc({
                "doctype": "Email Template",
                "name": "Test Template",
                "subject": "Test",
                "response": "Test"
            }).insert(ignore_permissions=True, ignore_mandatory=True)

        cadence = frappe.get_doc({
            "doctype": "Cadence",
            "cadence_name": "Test VCR Cadence",
            "enabled": 1,
            "users": [{"user": "Administrator"}],
            "cadence_schedules": [{
                "send_after_days": 1,
                "reference_doctype": "Email Template",
                "reference_name": "Test Template"
            }],
            "apollo_ids": [{
                "account": self.account_name,
                "sender": "Administrator",
                "status": "Active"
            }]
        }).insert(ignore_permissions=True, ignore_mandatory=True)

        provision_a_field("subject_1", "string", self.account_name)

        field_doc = frappe.get_doc("Apollo Field", "subject_1")
        self.assertEqual(field_doc.name, "subject_1")

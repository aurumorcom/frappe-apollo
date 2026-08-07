# AI Agent Guidelines for Frappe Apollo

This document provides context and strict guidelines for AI agents working on the `frappe_apollo` repository.

## 1. Framework Context
This is a **Frappe** application. It uses Frappe's DocType system for database modeling and the `bench` CLI for execution. However, we strictly override Frappe's default testing structure to follow standard Python Testing Standards.

## 2. Testing Architecture
You MUST adhere to the following testing rules:

### Directory Structure
- **Internal Tests**: `frappe_apollo/tests/integration/internal/`
  - These tests use the local database and mock all external API calls.
  - They must mirror the source tree (e.g., `frappe_apollo/integrations/apollo.py` is tested in `frappe_apollo/tests/integration/internal/integrations/test_apollo.py`).
- **External Tests**: `frappe_apollo/tests/integration/external/`
  - These tests interact with the live Apollo API using `vcrpy`.
  - They must also mirror the source tree.

### VCR.py Configuration
- External tests use `vcrpy` to record HTTP interactions into YAML cassettes.
- **CRITICAL**: The VCR configuration in `conftest.py` MUST scrub sensitive headers (`Authorization`, `X-Api-Key`). Never commit real credentials to the repository.
- The `record_mode` is dynamic:
  - If `APOLLO_TEST_ACCOUNT` is provided, `record_mode='once'` (records new cassettes).
  - If no credentials are provided, `record_mode='none'` (replays existing cassettes using a dummy account).

### Test Isolation
- Tests MUST be isolated. Do not rely on the execution order of tests.
- Do not use `setUpClass` to create shared state that mutates across tests. Each test should create its own required state (e.g., creating a contact before updating it).
- Do not add API cleanup logic (like deleting contacts via the Apollo API) unless explicitly requested, as the API key may lack deletion permissions. Rely on Frappe's `IntegrationTestCase` database rollback for local cleanup.

## 3. Integration Guidelines
- **ApolloClient**: All interactions with the Apollo API must go through the `ApolloClient` wrapper in `frappe_apollo/integrations/apollo.py`.
- **Authentication**: The client supports both API Key and OAuth 2.0 authentication. It automatically handles OAuth token refreshes if a `401 Unauthorized` response is received.
- **Rate Limiting**: The client raises an `ApolloRateLimitError` if a `429 Too Many Requests` response is received. Agents should handle this gracefully in background jobs.

# Rules

## framework-bench

### Frappe Bench UI and Sidebar Configuration Standards

#### 🎯 Directives
- ALWAYS explicitly define a `Workspace Sidebar` for your custom apps and modules to prevent Frappe from auto-generating random sidebars based on data volume.
- ALWAYS define standard sidebars manually or check the `Standard` box in the UI so that the configuration is exported as a JSON file tracked in Git. The exact file path MUST be `apps/[your_app]/[your_app]/workspace_sidebar/[workspace_name].json`.
- ALWAYS match the `title`, `name`, and `module` of your `Workspace Sidebar` to the exact name of the `Workspace` or `Module` you are customizing to override the fallback behavior.
- NEVER rely on Frappe's `auto_generate_sidebar_from_module()` fallback. This fallback uses `choose_top_doctypes()` which dynamically restricts the sidebar to ~3 doctypes based on record count, causing missing links.
- ALWAYS use hierarchical items (`"type": "Section Break"` or `"type": "Sidebar Item Group"`) to cleanly group your sidebar links (e.g., Core, Templates, Settings, Logs).
- ALWAYS set `"standard": 1` inside the JSON so that Frappe loads it automatically during `bench migrate` as base data without requiring Developer Mode on production.

#### 📝 Examples

##### ✅ DO
```json
// Exported JSON configuration for a Workspace Sidebar (e.g., in your_app/workspace_sidebar/my_app.json)
{
 "app": "my_app",
 "creation": "2024-03-12 10:00:00.000000",
 "docstatus": 0,
 "doctype": "Workspace Sidebar",
 "items": [
  {
   "child": 0,
   "idx": 1,
   "label": "Home",
   "link_to": "My App",
   "link_type": "Workspace",
   "type": "Link"
  },
  {
   "child": 0,
   "idx": 2,
   "label": "Master Data",
   "type": "Section Break"
  },
  {
   "child": 1,
   "idx": 3,
   "label": "Settings",
   "link_to": "My App Settings",
   "link_type": "DocType",
   "type": "Link"
  }
 ],
 "modified": "2024-03-12 10:00:00.000000",
 "module": "My App",
 "standard": 1,
 "title": "My App"
}
```

##### ❌ DON'T
```python
### Anti-pattern: Leaving the Workspace without a defined Workspace Sidebar,
### forcing Frappe to guess and auto-generate the sidebar using choose_top_doctypes()

### This is what Frappe does internally if you don't define a Standard Workspace Sidebar:
def choose_top_doctypes(doctype_names):
	# ...
	doctype_limit = 3
	if len(doctype_names) > doctype_limit:
        # Avoid this fallback behavior by explicitly defining your sidebars!
		doctype_count_map = {}
		for doctype in doctype_names:
			doctype_count_map[doctype] = frappe.db.count(doctype)
		top_doctypes = [name for name, count in sorted(doctype_count_map.items(), key=lambda x: x[1], reverse=True)[:doctype_limit]]
		return top_doctypes
```

### Frappe Bench Testing Standards

#### 🎯 Directives
- ALWAYS put your tests in a dedicated `tests/` directory at the root of your custom app (e.g., `apps/my_app/my_app/tests/`).
- NEVER put tests beside the script or within the DocType directory (like in the legacy Frappe codebase). This prevents test code from being accidentally mixed with production code or deployed.
- ALWAYS structure your `tests/` directory into `unit/`, `integration/internal/`, `integration/external/`, and `e2e/`, mirroring the source directory structure for consistency (see standard Python testing rules).
- ALWAYS define tests as classes that inherit from Frappe's provided test case base classes located in `frappe.tests` (`IntegrationTestCase` or `UnitTestCase`).
- ALWAYS use `frappe.tests.IntegrationTestCase` when your test requires database interactions, caching, or other framework-level resources.
- ALWAYS use `frappe.tests.UnitTestCase` for pure logic tests where database access is not required or explicitly mocked.
- ALWAYS ensure tests NEVER leave orphan data. Do not permanently alter data in the system. Use `super().setUpClass()` and explicitly call `frappe.db.rollback()` in `tearDownClass` and `tearDown` to discard changes and avoid side effects.
- ALWAYS isolate your tests. Tests MUST NOT depend on the state created by other tests.
- ALWAYS use `frappe.tests.utils.make_test_records` to automatically load records defined in a `test_records.json` file associated with a DocType, but ensure you clean them up via rollback.
- ALWAYS use `frappe.get_doc().insert()` when you need specific dynamic data for programmatic record creation during a test's `setUp` or `setUpClass`.
- ALWAYS name test files starting with `test_` (e.g., `test_api.py`, `test_doctype_name.py`).
- ALWAYS name test methods starting with `test_` so they are discovered by the test runner.
- ALWAYS use standard Python `unittest` library assertions (e.g., `self.assertEqual`, `self.assertTrue`) within your test classes.
- ALWAYS use tools like `vcrpy` in your `tests/integration/external/` directory for mocking 3rd party APIs, as standard in our Python rules.

#### 📁 Test Directory Structure
```text
my_frappe_app/
├── my_frappe_app/              # Source code
│   ├── api.py
│   └── my_module/
│       └── doctype/
│           └── my_doctype/
│               ├── my_doctype.py
│               └── my_doctype.js
├── tests/                      # ALL tests live here
│   ├── conftest.py             # Root fixtures
│   ├── unit/                   # 1-to-1 Mirror of source (fast, mocked)
│   │   ├── test_api.py
│   │   └── my_module/
│   │       └── doctype/
│   │           └── my_doctype/
│   │               └── test_my_doctype.py
│   ├── integration/
│   │   ├── internal/           # 1-to-1 Mirror of source (uses IntegrationTestCase & local DB)
│   │   │   └── my_module/
│   │   │       └── doctype/
│   │   │           └── my_doctype/
│   │   │               └── test_my_doctype.py
│   │   └── external/           # 1-to-1 Mirror of source (uses vcrpy for 3rd-party APIs)
│   ├── e2e/                    # Playwright / Cypress UI flows
│   └── data/                   # Test records / JSON sample payloads
```

#### 📝 Examples

##### ✅ DO
```python
import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.utils import make_test_records

### Clean separation of tests from production code
class TestCustomDashboard(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Load dependencies in order
        make_test_records("CRM Lead Status")
        make_test_records("CRM Lead")

    @classmethod
    def tearDownClass(cls):
        # Prevent orphan data
        frappe.db.rollback()
        super().tearDownClass()

    def test_dashboard_logic_inserts_address(self):
        doc = frappe.get_doc({
            "doctype": "Address",
            "address_title": "_Test Address",
            "address_type": "Office",
            "city": "_Test City",
            "country": "India"
        }).insert()
        
        self.assertTrue(doc.name)
        # Changes will be discarded by frappe.db.rollback() automatically via Frappe's test runner,
        # but explicit tearDown/tearDownClass handling guarantees no side effects.
```

##### ❌ DON'T
```python
### Anti-pattern: Placing test_my_doctype.py inside the doctype/ folder like legacy code!
import frappe
import unittest

### Anti-pattern: Not inheriting from Frappe's IntegrationTestCase for DB operations
class TestMyDocType(unittest.TestCase):
    
    # Anti-pattern: Missing super().setUpClass()
    @classmethod
    def setUpClass(cls):
        frappe.get_doc({"doctype": "CRM Lead Status", "status": "Open"}).insert()

    # Anti-pattern: Missing database rollback in tearDownClass, leaving orphan data in the database
    @classmethod
    def tearDownClass(cls):
        pass

    # Anti-pattern: Test method doesn't start with test_
    def check_custom_logic(self):
        doc = frappe.get_doc({
            "doctype": "Address",
            "address_title": "_Test Address"
        }).insert()
        
        assert doc.name is not None
```
# Repository Map

```python

.agents/rules/framework-bench/anti-patterns.md

.agents/rules/framework-bench/architecture-and-structure.md

.agents/rules/framework-bench/code-style-and-formatting.md

.agents/rules/framework-bench/configuration-and-environment.md

.agents/rules/framework-bench/dependency-management.md

.agents/rules/framework-bench/documentation-and-comments.md

.agents/rules/framework-bench/error-handling.md

.agents/rules/framework-bench/logging-and-observability.md

.agents/rules/framework-bench/naming-conventions.md

.agents/rules/framework-bench/performance-and-optimization.md

.agents/rules/framework-bench/security-and-validation.md

.agents/rules/framework-bench/testing-standards.md

.agents/rules/framework-bench/type-safety.md

.editorconfig

.eslintrc

.github/pull_request_template.md

.github/workflows/release.yaml

.pre-commit-config.yaml

.pytest_cache/CACHEDIR.TAG

.pytest_cache/README.md

.pytest_cache/v/cache/lastfailed

.pytest_cache/v/cache/nodeids

.ruff_cache/0.15.19/15086465409484288713

.ruff_cache/0.15.19/16598643235251216881

.ruff_cache/0.15.19/18081213280249112655

.ruff_cache/0.15.19/231851939855375105

.ruff_cache/0.15.19/3164860890096933693

.ruff_cache/0.15.19/3885319106757219098

.ruff_cache/0.15.19/6742097463396260340

.ruff_cache/0.15.19/8209216970249017068

.ruff_cache/CACHEDIR.TAG

AGENTS.md

CHANGELOG.md

LICENSE

README.md

VERSIONING.md

docs/architecture/README.md

docs/architecture/arc42/01_introduction_and_goals.md

docs/architecture/arc42/02_architecture_constraints.md

docs/architecture/arc42/03_context_and_scope.md

docs/architecture/arc42/04_solution_strategy.md

docs/architecture/arc42/05_building_block_view.md

docs/architecture/arc42/06_runtime_view.md

docs/architecture/arc42/07_deployment_view.md

docs/architecture/arc42/08_cross_cutting_concepts.md

docs/architecture/arc42/09_architecture_decisions/0001-record-architecture-decisions.md

docs/architecture/arc42/09_architecture_decisions/0002-rename-account-and-field-doctypes.md

docs/architecture/arc42/09_architecture_decisions/0003-convert-api-key-to-password-and-disable-stren

docs/architecture/arc42/09_architecture_decisions/0004-cadence-provider-lifecycle-hooks.md

docs/architecture/arc42/09_architecture_decisions/0005-single-sequence-engine-per-account.md

docs/architecture/arc42/10_quality_requirements.md

docs/architecture/arc42/11_risks_and_technical_debt.md

docs/architecture/arc42/12_glossary.md

docs/architecture/bpmn/01-oauth-authentication.md

docs/architecture/bpmn/02-mailbox-sync.md

docs/architecture/bpmn/03-cadence-provisioning.md

docs/architecture/bpmn/04-contact-sequence-assignment.md

docs/architecture/bpmn/05-communication-sync.md

docs/architecture/bpmn/06-webhook-processing.md

docs/architecture/c4/01-context.md

docs/architecture/c4/02-container.md

docs/architecture/c4/03-component.md

frappe_apollo/__init__.py

frappe_apollo/apollo/__init__.py

frappe_apollo/apollo/doctype/__init__.py

frappe_apollo/apollo/doctype/apollo_account/__init__.py

frappe_apollo/apollo/doctype/apollo_account/apollo_account.js:
⋮
│	onload: function(frm) {
│		['api_key', 'client_secret', 'refresh_token', 'access_token', 'webhook_bearer_token'].forEach(fie
│			if (frm.fields_dict[fieldname]) {
│				frm.fields_dict[fieldname].disable_password_checks();
│			}
│		});
│	},
│	refresh: function(frm) {
│		if (!frm.is_new() && frm.doc.client_id) {
│			if (frm.doc.status === "Unauthorized") {
│				frm.add_custom_button(__('Authorize'), function() {
│					frm.call({
│						method: 'get_authorization_url',
│						doc: frm.doc,
│						callback: function(r) {
│							if (r.message) {
│								window.location.href = r.message;
│							}
│						}
│					});
│				});
│			} else if (frm.doc.status === "Authorized") {
│				frm.add_custom_button(__('Unauthorize'), function() {
│					frm.call({
│						method: 'clear_tokens',
│						doc: frm.doc,
│						callback: function(r) {
│							frm.reload_doc();
│						}
│					});
│				});
⋮

frappe_apollo/apollo/doctype/apollo_account/apollo_account.json

frappe_apollo/apollo/doctype/apollo_account/apollo_account.py:
⋮
│class ApolloAccount(Document):
│	def on_update(self):
│		if self.has_value_changed("status") and self.status == "Authorized":
│			from frappe_controller.utils.background_jobs import enqueue
│
│			enqueue(
│				"frappe_apollo.apollo.doctype.apollo_account.apollo_account.provision_sequence",
│				queue="low",
│				account_name=self.name,
⋮
│	def after_insert(self):
⋮
│	@frappe.whitelist()
│	def get_authorization_url(self):
⋮
│	@frappe.whitelist()
│	def clear_tokens(self):
⋮
│def provision_sequence(account_name):
⋮

frappe_apollo/apollo/doctype/apollo_field/__init__.py

frappe_apollo/apollo/doctype/apollo_field/apollo_field.json

frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:
⋮
│class ApolloField(Document):
⋮
│def enqueue_provision_cadence_fields(cadence_name, account_name, sender=None):
⋮
│def provision_a_field(label, apollo_type, account_name):
⋮
│def _update_sequence(client, sequence_id, label):
⋮

frappe_apollo/apollo/doctype/apollo_field_apollo_id/__init__.py

frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.json

frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.py:
⋮
│class ApolloFieldApolloID(Document):
⋮

frappe_apollo/apollo/doctype/cadence/cadence.py:
⋮
│def on_update(doc, method=None):
⋮
│def on_trash(doc, method=None):
⋮
│def _get_supported_channels():
⋮
│def _validate_for_sequence(doc, account_name):
⋮
│def _disable_cadence_mccs(cadence_name):
⋮

frappe_apollo/apollo/doctype/cadence_apollo_id/__init__.py

frappe_apollo/apollo/doctype/cadence_apollo_id/cadence_apollo_id.json

frappe_apollo/apollo/doctype/cadence_apollo_id/cadence_apollo_id.py:
⋮
│class CadenceApolloID(Document):
⋮

frappe_apollo/apollo/doctype/cadence_provider/cadence_provider.py:
⋮
│def on_update(doc, method=None):
⋮

frappe_apollo/apollo/doctype/communication/communication.py:
⋮
│def on_update(doc, method=None):
⋮
│def update_a_contact(comm_name):
⋮

frappe_apollo/apollo/doctype/crm_lead/__init__.py

frappe_apollo/apollo/doctype/crm_lead/crm_lead.py:
⋮
│def _create_a_contact(mcc_name):
⋮
│def create_a_contact(lead_name, account_name):
⋮
│def update_a_contact(lead_name, account_name):
⋮

frappe_apollo/apollo/doctype/crm_lead_apollo_id/__init__.py

frappe_apollo/apollo/doctype/crm_lead_apollo_id/crm_lead_apollo_id.json

frappe_apollo/apollo/doctype/crm_lead_apollo_id/crm_lead_apollo_id.py:
⋮
│class CRMLeadApolloID(Document):
⋮

frappe_apollo/apollo/doctype/email_account/__init__.py

frappe_apollo/apollo/doctype/email_account/email_account.py:
⋮
│@frappe.whitelist()
│def queue_get_email_accounts():
⋮
│def get_email_accounts(account_name):
⋮

frappe_apollo/apollo/doctype/email_account_apollo_id/__init__.py

frappe_apollo/apollo/doctype/email_account_apollo_id/email_account_apollo_id.json

frappe_apollo/apollo/doctype/email_account_apollo_id/email_account_apollo_id.py:
⋮
│class EmailAccountApolloID(Document):
⋮

frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py:
⋮
│def before_save(doc, method=None):
⋮
│def on_update(doc, method=None):
⋮
│def add_a_contact_to_sequence(mcc_name):
⋮
│def add_contact_to_sequence(mcc_name):
⋮
│def _stop_contact_in_sequence(mcc_name, mode="stop"):
⋮

frappe_apollo/config/__init__.py

frappe_apollo/fixtures/custom_field.json

frappe_apollo/fixtures/property_setter.json

frappe_apollo/frappe_apollo/.frappe

frappe_apollo/frappe_apollo/__init__.py

frappe_apollo/hooks.py

frappe_apollo/install.py:
⋮
│def after_install() -> None:
⋮

frappe_apollo/integrations/__init__.py

frappe_apollo/integrations/apollo.py:
⋮
│class ApolloRateLimitError(Exception):
⋮
│class ApolloClient:
│	base_url = "https://api.apollo.io/api/v1"
│
│	def __init__(self, account_name):
⋮
│	def get_email_accounts(self):
⋮
│	def get_sequence(self, sequence_id):
⋮
│	def create_sequence(self, name, permissions="team_can_use", active=True, emailer_steps=None):
⋮
│	def update_sequence(self, sequence_id, updates):
⋮
│	def approve_sequence(self, sequence_id):
⋮
│	def abort_sequence(self, sequence_id):
⋮
│	def archive_sequence(self, sequence_id):
⋮
│	def search_sequences(self, q_name=None, page=1, per_page=25):
⋮
│	def create_contact(self, email, first_name=None, last_name=None, title=None, organization_name=Non
⋮
│	def update_contact(self, contact_id, custom_fields):
⋮
│	def add_contacts_to_sequence(self, contact_id, sequence_id, mailbox_id):
⋮
│	def create_custom_field(self, label, field_type="string"):
⋮
│	def update_sequence_contact_status(self, person_id, sequence_id, action):
⋮
│	def _request(self, method, endpoint, **kwargs):
⋮
│	def _get_headers(self):
⋮
│	def _refresh_oauth_token(self):
⋮

frappe_apollo/modules.txt

frappe_apollo/oauth.py:
⋮
│@frappe.whitelist(allow_guest=True)
│def callback(code, state=None):
⋮

frappe_apollo/overrides/__init__.py

frappe_apollo/patches.txt

frappe_apollo/patches/__init__.py

frappe_apollo/templates/__init__.py

frappe_apollo/templates/pages/__init__.py

frappe_apollo/tests/__init__.py

frappe_apollo/tests/integration/__init__.py

frappe_apollo/tests/integration/external/__init__.py

frappe_apollo/tests/integration/external/apollo/__init__.py

frappe_apollo/tests/integration/external/apollo/doctype/__init__.py

frappe_apollo/tests/integration/external/apollo/doctype/cadence/__init__.py

frappe_apollo/tests/integration/external/apollo/doctype/cadence/test_cadence.py:
⋮
│class TestCadenceProvisioningExternal(IntegrationTestCase):
│    @classmethod
│    def setUpClass(cls):
│        super().setUpClass()
│        cls.account_name = frappe.conf.get("apollo_test_account") or os.environ.get("APOLLO_TEST_AC
│        if cls.account_name and frappe.db.exists("Apollo Account", cls.account_name):
│            doc = frappe.get_doc("Apollo Account", cls.account_name)
│            try:
│                if not doc.get_password("api_key") and not doc.access_token:
│                    cls.account_name = None
│            except Exception:
⋮
│    @classmethod
│    def tearDownClass(cls):
⋮
│    def setUp(self):
⋮
│    def tearDown(self):
⋮
│    def _skip_if_no_cassette(self, cassette_name):
⋮
│    @my_vcr.use_cassette('test_create_cadence.yaml')
│    def test_create_cadence(self):
⋮

frappe_apollo/tests/integration/external/conftest.py:
⋮
│if not hasattr(aiohttp.streams, "AsyncStreamReaderMixin"):
│    class AsyncStreamReaderMixin:
⋮

frappe_apollo/tests/integration/external/integrations/__init__.py

frappe_apollo/tests/integration/external/integrations/cassettes/__init__.py

frappe_apollo/tests/integration/external/integrations/cassettes/test_add_contacts_to_sequence.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_add_people_to_sequence.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_apollo_refresh.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_auto_provision_sequence.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_create_cadence.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_create_contact.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_create_custom_field.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_create_field.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_create_people.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_create_sequence.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_get_email_accounts.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_get_mailboxes.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_search_sequences.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_update_contact.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_update_people.yaml

frappe_apollo/tests/integration/external/integrations/cassettes/test_update_sequence.yaml

frappe_apollo/tests/integration/external/integrations/test_apollo.py:
⋮
│class TestApolloExternalAPI(IntegrationTestCase):
│	@classmethod
│	def setUpClass(cls):
│		super().setUpClass()
│		import os
│		# Use the account provided by the user via site_config or environment variable
│		cls.account_name = frappe.conf.get("apollo_test_account") or os.environ.get("APOLLO_TEST_ACCOUNT"
│		cls.sequence_id = frappe.conf.get("apollo_test_sequence_id") or os.environ.get("APOLLO_TEST_SEQUE
│
│		if cls.account_name and frappe.db.exists("Apollo Account", cls.account_name):
│			doc = frappe.get_doc("Apollo Account", cls.account_name)
⋮
│	@classmethod
│	def tearDownClass(cls):
⋮
│	def setUp(self):
⋮
│	def tearDown(self):
⋮
│	def _cleanup_all_sequences(self):
⋮
│	@my_vcr.use_cassette('test_get_email_accounts.yaml')
│	def test_get_email_accounts_live(self):
⋮
│	@my_vcr.use_cassette('test_search_sequences.yaml')
│	def test_search_sequences_live(self):
⋮
│	@my_vcr.use_cassette('test_create_contact.yaml')
│	def test_create_contact_live(self):
⋮
│	@my_vcr.use_cassette('test_create_custom_field.yaml')
│	def test_create_custom_field_live(self):
⋮
│	@my_vcr.use_cassette('test_update_contact.yaml')
│	def test_update_contact_live(self):
⋮
│	@my_vcr.use_cassette('test_add_contacts_to_sequence.yaml')
│	def test_add_contacts_to_sequence_live(self):
⋮
│	@my_vcr.use_cassette('test_create_sequence.yaml')
│	def test_create_sequence_live(self):
⋮
│	@my_vcr.use_cassette('test_update_sequence.yaml')
│	def test_update_sequence_live(self):
⋮
│	@my_vcr.use_cassette('test_apollo_refresh.yaml')
│	def test_proactive_token_refresh(self):
⋮

frappe_apollo/tests/integration/internal/__init__.py

frappe_apollo/tests/integration/internal/apollo/__init__.py

frappe_apollo/tests/integration/internal/apollo/doctype/__init__.py

frappe_apollo/tests/integration/internal/apollo/doctype/apollo_account/__init__.py

frappe_apollo/tests/integration/internal/apollo/doctype/apollo_account/test_apollo_account.py:
⋮
│class TestApolloAccountIntegration(IntegrationTestCase):
│	@classmethod
│	def tearDownClass(cls):
│		frappe.db.rollback()
⋮
│	def setUp(self):
⋮
│	def tearDown(self):
⋮
│	@patch("frappe_controller.utils.controller.wait_for_event")
│	def test_provision_sequence_suspends_when_unauthorized(self, mock_wait):
⋮
│	@patch("frappe_apollo.integrations.apollo.ApolloClient")
│	def test_provision_sequence_creates_sequence_and_updates_account(self, mock_client_cls):
⋮

frappe_apollo/tests/integration/internal/apollo/doctype/apollo_field/__init__.py

frappe_apollo/tests/integration/internal/apollo/doctype/cadence/__init__.py

frappe_apollo/tests/integration/internal/apollo/doctype/cadence/test_cadence.py:
⋮
│class TestApolloLifecycleE2E(IntegrationTestCase):
│    @classmethod
│    def tearDownClass(cls):
│        frappe.db.rollback()
⋮
│    def setUp(self):
⋮
│    def tearDown(self):
⋮
│    def _create_test_cadence(self):
⋮
│    @patch("frappe_controller.utils.controller.wait_for_event")
│    def test_provision_field_suspension_provider_disabled(self, mock_wait):
⋮
│    @patch("frappe_controller.utils.controller.wait_for_event")
│    def test_provision_field_suspension_account_unauthorized(self, mock_wait):
⋮
│    @patch("frappe_apollo.integrations.apollo.ApolloClient")
│    def test_provision_field_creates_apollo_fields(self, mock_client_cls):
⋮
│    def test_mcc_draft_reassignment(self):
⋮
│    @patch("frappe_apollo.integrations.apollo.ApolloClient")
│    @patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event
│    def test_mcc_sequence_assignment(self, mock_mcc_wait, mock_client_cls):
⋮

frappe_apollo/tests/integration/internal/apollo/doctype/cadence_provider/__init__.py

frappe_apollo/tests/integration/internal/apollo/doctype/cadence_provider/test_cadence_provider.py:
⋮
│class TestCadenceProvider(IntegrationTestCase):
│    @classmethod
│    def tearDownClass(cls):
│        frappe.db.rollback()
⋮
│    def setUp(self):
⋮
│    def tearDown(self):
⋮
│    @patch("frappe.get_doc")
⋮
│    def test_field_provisioning_listens_to_provider_enablement_event(self, mock_wait, mock_get_valu
⋮
│    @patch("frappe.db.get_value")
│    @patch("frappe_controller.utils.controller.wait_for_event")
│    def test_contact_creation_registers_provider_event_listener(self, mock_wait, mock_get_value):
⋮
│    @patch("frappe.db.get_value")
│    @patch("frappe_controller.utils.controller.wait_for_event")
│    def test_contact_update_registers_provider_event_listener(self, mock_wait, mock_get_value):
⋮
│    @patch("frappe.get_doc")
⋮
│    def test_mcc_sequence_assignment_suspends_when_provider_disabled(self, mock_wait, mock_get_valu
⋮
│    @patch("frappe.get_all")
│    @patch("frappe_controller.utils.background_jobs.enqueue")
│    def test_cadence_provider_on_update_enqueues_valid_method_path(self, mock_enqueue, mock_get_all
⋮

frappe_apollo/tests/integration/internal/apollo/doctype/communication/__init__.py

frappe_apollo/tests/integration/internal/apollo/doctype/communication/test_communication.py:
⋮
│class TestCommunicationIntegration(IntegrationTestCase):
│    @classmethod
│    def tearDownClass(cls):
│        frappe.db.rollback()
⋮
│    def tearDown(self):
⋮
│    @patch("frappe_apollo.apollo.doctype.communication.communication.wait_for_event", side_effect=S
⋮
│    def test_missing_custom_fields_raises_wait(self, mock_get_all, mock_get_doc, mock_get_value, mo
│        def mock_get_value_side_effect(dt, name_or_filters=None, fieldname=None):
│            if dt == "Cadence Provider": return 1
│            if dt == "User Email": return "Email-Acc-1"
⋮
│        def mock_get_doc_side_effect(*args, **kwargs):
⋮
│    @patch("frappe_apollo.apollo.doctype.communication.communication.wait_for_event", side_effect=S
⋮
│    def test_valid_sync(self, mock_client_class, mock_get_all, mock_get_doc, mock_get_value, mock_w
│        def mock_get_value_side_effect(dt, name_or_filters=None, fieldname=None):
│            if dt == "Cadence Provider": return 1
│            if dt == "User Email": return "Email-Acc-1"
⋮
│        def mock_get_doc_side_effect(*args, **kwargs):
⋮

frappe_apollo/tests/integration/internal/apollo/doctype/email_account/test_email_account.py:
⋮
│class TestEmailAccountIntegration(IntegrationTestCase):
│    @classmethod
│    def tearDownClass(cls):
│        frappe.db.rollback()
⋮
│    def setUp(self):
⋮
│    def tearDown(self):
⋮
│    @patch("frappe.enqueue")
│    def test_queue_get_email_accounts(self, mock_enqueue):
⋮
│    @patch("frappe.enqueue")
│    def test_queue_get_email_accounts_deduplication_when_queued(self, mock_enqueue):
⋮
│    @patch("frappe.enqueue")
│    def test_queue_get_email_accounts_no_deduplication_when_finished(self, mock_enqueue):
⋮
│    def test_scheduler_hook_registered_as_daily(self):
⋮
│    @patch("frappe_apollo.integrations.apollo.ApolloClient")
│    def test_get_email_accounts_creation(self, mock_client_cls):
⋮
│    @patch("frappe_apollo.integrations.apollo.ApolloClient")
│    def test_get_email_accounts_append(self, mock_client_cls):
⋮

frappe_apollo/tests/integration/internal/apollo/doctype/multi_channel_cadence/__init__.py

frappe_apollo/tests/integration/internal/apollo/doctype/multi_channel_cadence/test_multi_channel_cad
⋮
│class TestMCCIntegration(IntegrationTestCase):
│    @classmethod
│    def tearDownClass(cls):
│        frappe.db.rollback()
⋮
│    def tearDown(self):
⋮
│    @patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event
⋮
│    def test_sequence_inactive_raises_wait(self, mock_client_class, mock_get_all, mock_get_doc, moc
│        from frappe.database.database import Database
│        real_get_value = Database.get_value
│        def mock_get_value_side_effect(*args, **kwargs):
⋮
│        def mock_get_doc_side_effect(*args, **kwargs):
⋮
│    @patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event
⋮
│    def test_valid_sync(self, mock_enqueue, mock_client_class, mock_get_all, mock_get_doc, mock_get
│        from frappe.database.database import Database
│        real_get_value = Database.get_value
│        def mock_get_value_side_effect(*args, **kwargs):
⋮
│        def mock_get_doc_side_effect(*args, **kwargs):
⋮

frappe_apollo/tests/integration/internal/integrations/__init__.py

frappe_apollo/tests/integration/internal/test_install.py:
⋮
│class TestInstallIntegration(IntegrationTestCase):
│
│	def setUp(self):
│		super().setUp()
│		if frappe.db.exists("Cadence Provider", "Apollo"):
⋮
│	@classmethod
│	def tearDownClass(cls):
⋮
│	def tearDown(self):
⋮
│	def test_after_install_integration(self):
⋮

frappe_apollo/tests/integration/internal/test_oauth.py:
⋮
│class TestOAuth(IntegrationTestCase):
│	def setUp(self):
│		super().setUp()
│
│		if not frappe.db.exists("Apollo Account", "Test Account OAuth"):
│			# Create Account
│			frappe.get_doc({
│				"doctype": "Apollo Account",
│				"account_name": "Test Account OAuth",
│				"webhook_bearer_token": "secret123",
│				"client_id": "client_id",
⋮
│	@classmethod
│	def tearDownClass(cls):
⋮
│	def tearDown(self):
⋮
│	@patch("frappe_apollo.oauth.requests.post")
│	def test_oauth_callback(self, mock_post):
⋮

frappe_apollo/tests/integration/internal/test_uninstall.py:
⋮
│class TestUninstallIntegration(IntegrationTestCase):
│
│	def setUp(self):
│		super().setUp()
⋮
│	@classmethod
│	def tearDownClass(cls):
⋮
│	def tearDown(self):
⋮
│	def test_before_uninstall_integration(self):
⋮

frappe_apollo/tests/integration/internal/test_webhook.py:
⋮
│class TestWebhookIntegration(IntegrationTestCase):
│    def setUp(self):
│        super().setUp()
│
│        lead_email = f"webhook_{frappe.generate_hash(length=6)}@example.com"
│        account_name = f"Webhook Account {frappe.generate_hash(length=6)}"
│        cadence_name = f"Webhook Cadence {frappe.generate_hash(length=6)}"
│
│        lead = frappe.get_doc({
│            "doctype": "CRM Lead",
│            "first_name": "Webhook",
⋮
│    @classmethod
│    def tearDownClass(cls):
⋮
│    def tearDown(self):
⋮
│    @patch("frappe.get_request_header")
│    def test_security_unauthorized_no_token(self, mock_header):
⋮
│    @patch("frappe.get_request_header")
│    def test_security_unauthorized_wrong_token(self, mock_header):
⋮
│    @patch("frappe.enqueue")
│    @patch("frappe.get_request_header")
│    def test_security_authorized(self, mock_header, mock_enqueue):
⋮
│    @patch("frappe_apollo.webhook.report_event")
│    def test_process_webhook_message_sent(self, mock_report_event):
│        # Create Communication
│        comm = frappe.get_doc({
│            "doctype": "Communication",
│            "communication_type": "Communication",
│            "reference_doctype": "Multi Channel Cadence",
│            "reference_name": self.mcc_name,
│            "delivery_status": "Scheduled",
│            "subject": "Test",
│            "content": "Test body"
⋮
│        def mock_get_all_side_effect(doctype, *args, **kwargs):
⋮
│    @patch("frappe_apollo.webhook.report_event")
│    def test_process_webhook_message_opened(self, mock_report_event):
│        comm = frappe.get_doc({
│            "doctype": "Communication",
│            "communication_type": "Communication",
│            "reference_doctype": "Multi Channel Cadence",
│            "reference_name": self.mcc_name,
│            "delivery_status": "Sent",
│            "subject": "Test",
│            "content": "Test body"
⋮
│        def mock_get_all_side_effect(doctype, *args, **kwargs):
⋮
│    @patch("frappe_apollo.webhook.report_event")
│    def test_process_webhook_message_replied(self, mock_report_event):
│        payload = {
│            "event": "message_replied",
│            "contact_id": "contact_123",
│            "emailer_campaign_id": "seq_123"
⋮
│        def mock_get_all_side_effect(doctype, *args, **kwargs):
⋮
│    @patch("frappe_apollo.webhook.report_event")
│    def test_process_webhook_unmapped(self, mock_report_event):
│        payload = {
│            "event": "message_sent",
│            "contact_id": "unknown",
│            "emailer_campaign_id": "seq_123"
⋮
│        def mock_get_all_side_effect(doctype, *args, **kwargs):
⋮

frappe_apollo/tests/unit/__init__.py

frappe_apollo/tests/unit/apollo/__init__.py

frappe_apollo/tests/unit/apollo/doctype/__init__.py

frappe_apollo/tests/unit/apollo/doctype/apollo_account/test_apollo_account.py:
⋮
│class TestApolloAccount(UnitTestCase):
│	@patch("frappe_controller.utils.background_jobs.enqueue")
│	def test_on_update_enqueues_provision_sequence_when_status_changes_to_authorized(self, mock_enqueu
│		doc = ApolloAccount({"doctype": "Apollo Account", "name": "Acc1", "status": "Authorized"})
│		doc.has_value_changed = MagicMock(side_effect=lambda field: True if field == "status" else False)
│
│		doc.on_update()
│
│		mock_enqueue.assert_called_once_with(
│			"frappe_apollo.apollo.doctype.apollo_account.apollo_account.provision_sequence",
│			queue="low",
⋮
│	@patch("frappe.db.get_value")
│	@patch("frappe_controller.utils.controller.wait_for_event")
│	def test_provision_sequence_suspends_if_not_authorized(self, mock_wait, mock_db_get_value):
⋮
│	@patch("frappe_apollo.integrations.apollo.ApolloClient")
│	@patch("frappe.db.get_value")
│	def test_provision_sequence_returns_early_if_sequence_id_exists(self, mock_db_get_value, mock_clie
│		def db_get_value_side_effect(dt, name, field=None):
│			if field == "status":
│				return "Authorized"
│			if field == "apollo_sequence_id":
│				return "existing_seq_123"
⋮
│	@patch("frappe.get_doc")
⋮
│	def test_provision_sequence_uses_existing_apollo_sequence_if_found(
│		self, mock_db_get_value, mock_client_cls, mock_get_doc
│	):
│		def db_get_value_side_effect(dt, name, field=None):
│			if field == "status":
│				return "Authorized"
│			if field == "apollo_sequence_id":
│				return None
⋮
│	@patch("frappe.get_doc")
⋮
│	def test_provision_sequence_creates_sequence_if_not_found(
│		self, mock_db_get_value, mock_client_cls, mock_get_doc
│	):
│		def db_get_value_side_effect(dt, name, field=None):
│			if field == "status":
│				return "Authorized"
│			if field == "apollo_sequence_id":
│				return None
⋮
│	@patch("frappe.log_error")
⋮
│	def test_provision_sequence_handles_403_forbidden(self, mock_db_get_value, mock_client_cls, mock_l
│		import requests
│
│		def db_get_value_side_effect(dt, name, field=None):
⋮

frappe_apollo/tests/unit/apollo/doctype/apollo_field/__init__.py

frappe_apollo/tests/unit/apollo/doctype/apollo_field/test_apollo_field.py:
⋮
│class TestField(UnitTestCase):
│	@patch("frappe_controller.utils.background_jobs.enqueue")
│	@patch("frappe.get_doc")
│	def test_enqueue_provision_cadence_fields(self, mock_get_doc, mock_enqueue):
│		mock_cadence = MagicMock()
│		mock_cadence.name = "Cad1"
│
│		mock_step1 = MagicMock()
│		mock_step1.get.side_effect = lambda k, d=None: (
│			"Email" if k == "channel" else ("Email Template" if k == "reference_doctype" else d)
│		)
⋮
│	@patch("frappe_apollo.apollo.doctype.apollo_field.apollo_field._update_sequence")
⋮
│	def test_provision_a_field_creates_field_doc_and_custom_field(
│		self, mock_get_doc, mock_get_value, mock_client_cls, mock_update_seq
│	):
│		mock_client = mock_client_cls.return_value
⋮
│		def mock_get_doc_side_effect(doctype, *args, **kwargs):
⋮
│	@patch("frappe_apollo.integrations.apollo.ApolloClient")
⋮
│	def test_provision_a_field_re_raises_exception(
│		self, mock_log_error, mock_get_doc, mock_get_value, mock_client_cls
⋮
│	@patch("frappe_controller.utils.controller.wait_for_event")
⋮
│	def test_provision_a_field_waits_for_apollo_sequence_id(
│		self, mock_get_doc, mock_get_value, mock_client_cls, mock_wait
│	):
│		mock_field_doc = MagicMock()
⋮
│		def get_value_side_effect(dt, name, field):
⋮
│	def test_update_sequence_appends_steps_when_needed(self):
⋮
│	def test_update_sequence_noop_when_capacity_sufficient(self):
⋮

frappe_apollo/tests/unit/apollo/doctype/cadence/__init__.py

frappe_apollo/tests/unit/apollo/doctype/cadence/test_cadence.py:
⋮
│class TestCadenceProvisioning(UnitTestCase):
│	@patch("frappe_apollo.apollo.doctype.cadence.cadence._validate_for_sequence")
│	@patch("frappe.get_attr")
│	def test_on_update_validates_and_enqueues_fields(self, mock_get_attr, mock_validate):
│		doc = MagicMock()
│		doc.name = "Test Cadence"
│		doc.has_value_changed.return_value = False
│
│		row1 = MagicMock(account="Acc1")
│		row1.get.side_effect = lambda k: "Sender1" if k == "sender" else None
│		row2 = MagicMock(account="Acc2")
⋮
│	@patch("frappe_apollo.apollo.doctype.cadence.cadence.enqueue")
⋮
│	def test_on_update_disabling_enqueues_disable_mccs(self, mock_get_attr, mock_validate, mock_enqueu
⋮
│	@patch("frappe.msgprint")
⋮
│	def test_validate_for_sequence_mismatch_disables_cadence(self, mock_client_cls, mock_db_get_value,
⋮
│	@patch("frappe.msgprint")
│	@patch("frappe_apollo.apollo.doctype.cadence.cadence.ApolloClient")
│	def test_validate_for_sequence_zero_steps_returns_early(self, mock_client_cls, mock_msgprint):
⋮
│	@patch("frappe.msgprint")
│	@patch("frappe.db.get_value")
│	def test_validate_for_sequence_missing_sequence_id_disables(self, mock_db_get_value, mock_msgprint
⋮
│	@patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence._stop_contact_in_
⋮
│	def test_disable_cadence_mccs(self, mock_get_all, mock_get_doc, mock_stop_contact):
⋮

frappe_apollo/tests/unit/apollo/doctype/communication/__init__.py

frappe_apollo/tests/unit/apollo/doctype/communication/test_communication.py:
⋮
│class TestCommunicationOverride(UnitTestCase):
│
│	@patch("frappe.enqueue")
│	def test_on_update_enqueues_when_status_changes_to_scheduled(self, mock_enqueue):
│		mock_doc = MagicMock()
│		mock_doc_before = MagicMock()
│		mock_doc_before.status = "Draft"
│		mock_doc.get_doc_before_save.return_value = mock_doc_before
│		mock_doc.status = "Scheduled"
│		mock_doc.name = "Comm-1"
│
│		on_update(mock_doc)
│
⋮
│	@patch("frappe.get_doc")
│	def test_idempotency(self, mock_get_doc):
⋮
│	@patch("frappe_apollo.apollo.doctype.communication.communication.wait_for_event")
│	@patch("frappe.get_doc")
│	def test_wait_state_mcc(self, mock_get_doc, mock_wait):
⋮
│	@patch("frappe_apollo.integrations.apollo.ApolloClient")
⋮
│	def test_success_dynamic_step_indexing(self, mock_get_doc, mock_get_value, mock_get_all, mock_clie
⋮
│	@patch("frappe.get_all")
⋮
│	def test_out_of_bounds_step_index_raises_suspend_job(self, mock_get_doc, mock_get_value, mock_get_
⋮

frappe_apollo/tests/unit/apollo/doctype/crm_lead/__init__.py

frappe_apollo/tests/unit/apollo/doctype/crm_lead/test_crm_lead.py:
⋮
│class TestCRMLead(UnitTestCase):
│
│    @patch("frappe.get_doc")
│    @patch("frappe.db.count")
│    @patch("frappe_controller.utils.controller.wait_for_event")
│    def test_create_a_contact_suspends_for_missing_communications(self, mock_wait, mock_count, mock
│        mcc = MagicMock()
│        mcc.name = "mcc1"
│        mcc.status = "Scheduled"
│        mcc.sender = "sender"
│        mcc.recipient = "lead1"
│        mcc.cadence = "cad1"
│
⋮
│    @patch("frappe.get_doc")
⋮
│    def test_create_a_contact_enqueues_create_if_no_apollo_id(self, mock_wait, mock_enqueue, mock_g
│        mcc = MagicMock()
⋮
│        def get_doc_side_effect(dt, name):
⋮
│        def get_value_side_effect(dt, *args):
⋮
│    @patch("frappe.get_doc")
⋮
│    def test_create_a_contact_enqueues_update_if_apollo_id_exists(self, mock_enqueue, mock_get_valu
│        mcc = MagicMock()
⋮
│        def get_doc_side_effect(dt, name):
⋮
│        def get_value_side_effect(dt, *args):
⋮
│    @patch("frappe.get_doc")
⋮
│    def test_update_a_contact(self, mock_client_cls, mock_get_value, mock_get_doc):
⋮
│    @patch("frappe.get_doc")
⋮
│    def test_create_a_contact_refetches_email_account_name_after_resumption(self, mock_wait, mock_e
│        mcc = MagicMock()
⋮
│        def get_value_side_effect(dt, name_or_filters=None, *args):
⋮
│        def wait_side_effect(*args, **kwargs):
⋮
│    @patch("frappe.get_doc")
⋮
│    def test_create_a_contact_registers_event_listener_when_account_unauthorized(self, mock_wait, m
│        def get_value_side_effect(dt, name_or_filters=None, *args):
│            if dt == "Cadence Provider": return 1
│            if dt == "Apollo Account": return "Unauthorized"
⋮

frappe_apollo/tests/unit/apollo/doctype/email_account/test_email_account.py:
⋮
│class TestEmailAccount(UnitTestCase):
│
│    @patch("frappe.enqueue")
│    @patch("frappe.get_doc")
│    @patch("frappe.get_all")
│    def test_queue_get_email_accounts_enqueues_for_api_key_password_field(self, mock_get_all, mock_
│        mock_get_all.return_value = [frappe._dict({"name": "Acc1"})]
│        mock_doc = MagicMock()
│        mock_doc.get_password.side_effect = lambda field, raise_exception=False: "secret_api_key" i
│        mock_doc.access_token = None
│        mock_get_doc.return_value = mock_doc
│
⋮

frappe_apollo/tests/unit/apollo/doctype/multi_channel_cadence/__init__.py

frappe_apollo/tests/unit/apollo/doctype/multi_channel_cadence/test_multi_channel_cadence.py:
⋮
│class TestMultiChannelCadence(UnitTestCase):
│	@patch("frappe.db.get_value")
│	@patch("frappe.get_doc")
│	@patch("frappe.get_all")
│	def test_before_save_pulls_sequence_id_from_apollo_account(self, mock_get_all, mock_get_doc, mock_
│		mcc = MagicMock()
│		mcc.get.side_effect = lambda k, d=[]: [MagicMock(cadence_provider="Apollo")] if k == "provider" e
│		mcc.sender = "user@example.com"
│		mcc.apollo_account = None
│		mcc.apollo_sequence_id = None
│		mcc.cadence_name = "Cad1"
⋮
│	@patch("frappe.get_doc")
│	@patch("frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.wait_for_event")
│	def test_assign_contact_fail_fast_wrong_status(self, mock_wait, mock_get_doc):
⋮
│	@patch("frappe.get_doc")
⋮
│	def test_assign_contact_waits_for_account_sequence_id(self, mock_wait, mock_client_cls, mock_get_a
⋮
│	@patch("frappe_apollo.integrations.apollo.ApolloClient")
⋮
│	def test_stop_contact_in_sequence(self, mock_get_doc, mock_get_all, mock_client_cls):
⋮
│	@patch("frappe.enqueue")
│	def test_on_update_enqueues_stop_contact_on_deactivation(self, mock_enqueue):
⋮

frappe_apollo/tests/unit/integrations/__init__.py

frappe_apollo/tests/unit/integrations/test_apollo.py:
⋮
│class TestApolloClient(UnitTestCase):
│
│	@patch("frappe.get_doc")
│	def test_get_headers_api_key(self, mock_get_doc):
│		mock_account = MagicMock()
│		mock_account.get_password.side_effect = lambda field, raise_exception=False: "test_key" if field 
│		mock_account.access_token = None
│		mock_account.refresh_token = None
│		mock_get_doc.return_value = mock_account
│
│		client = ApolloClient("Test Account")
│		headers = client._get_headers()
│
⋮
│	@patch("frappe.get_doc")
│	def test_get_headers_oauth(self, mock_get_doc):
⋮
│	@patch("frappe.get_doc")
│	@patch("frappe_apollo.integrations.apollo.requests.request")
│	def test_rate_limit_error(self, mock_request, mock_get_doc):
⋮
│	@patch("frappe.get_doc")
│	@patch("frappe_apollo.integrations.apollo.requests.request")
│	def test_oauth_refresh(self, mock_request, mock_get_doc):
⋮
│	@patch("frappe.get_doc")
│	@patch("frappe_apollo.integrations.apollo.requests.request")
│	def test_fallback_logic_add_contacts(self, mock_request, mock_get_doc):
│		mock_account = MagicMock()
⋮
│		def mock_request_side_effect(*args, **kwargs):
⋮
│	@patch("frappe.log_error")
⋮
│	def test_refresh_oauth_token_failure_marks_unauthorized(self, mock_post, mock_get_doc, mock_commit
⋮
│	@patch("frappe.get_doc")
│	@patch("frappe_apollo.integrations.apollo.requests.request")
│	def test_get_email_accounts(self, mock_request, mock_get_doc):
⋮

frappe_apollo/tests/unit/overrides/__init__.py

frappe_apollo/tests/unit/test_install.py:
⋮
│class TestInstall(UnitTestCase):
│
│	@patch("frappe_apollo.install.frappe")
│	def test_after_install_creates_apollo_provider_when_missing(self, mock_frappe):
│		def exists_side_effect(dt, name=None):
│			if dt == "DocType" and name == "Cadence Provider":
│				return True
│			if dt == "Cadence Provider" and name == "Apollo":
│				return False
│			return False
│
│		mock_frappe.db.exists.side_effect = exists_side_effect
⋮
│	@patch("frappe_apollo.install.frappe")
│	def test_after_install_idempotent_when_provider_exists(self, mock_frappe):
│		def exists_side_effect(dt, name=None):
│			if dt == "DocType" and name == "Cadence Provider":
│				return True
│			if dt == "Cadence Provider" and name == "Apollo":
│				return True
⋮
│	@patch("frappe_apollo.install.frappe")
│	def test_after_install_appends_email_channel_if_missing(self, mock_frappe):
│		def exists_side_effect(dt, name=None):
│			if dt == "DocType" and name == "Cadence Provider":
│				return True
│			if dt == "Cadence Provider" and name == "Apollo":
│				return True
⋮
│	@patch("frappe_apollo.install.frappe")
│	def test_after_install_handles_missing_doctype(self, mock_frappe):
⋮

frappe_apollo/tests/unit/test_uninstall.py:
⋮
│class TestUninstall(UnitTestCase):
│
│	@patch("frappe_apollo.uninstall.frappe")
│	def test_before_uninstall_removes_apollo_provider(self, mock_frappe):
│		def exists_side_effect(dt, name=None):
│			if dt == "DocType" and name == "Cadence Provider":
│				return True
│			if dt == "Cadence Provider" and name == "Apollo":
│				return True
│			return False
│
│		mock_frappe.db.exists.side_effect = exists_side_effect
│
⋮
│	@patch("frappe_apollo.uninstall.frappe")
│	def test_before_uninstall_handles_non_existent_provider(self, mock_frappe):
│		def exists_side_effect(dt, name=None):
│			if dt == "DocType" and name == "Cadence Provider":
│				return True
│			if dt == "Cadence Provider" and name == "Apollo":
│				return False
⋮
│	@patch("frappe_apollo.uninstall.frappe")
│	def test_before_uninstall_handles_missing_doctype(self, mock_frappe):
⋮

frappe_apollo/third_party/add-contacts-to-sequence.md

frappe_apollo/third_party/create-a-contact.md

frappe_apollo/third_party/create-a-custom-field.md

frappe_apollo/third_party/get-a-list-of-email-accounts.md

frappe_apollo/third_party/search-for-sequences.md

frappe_apollo/third_party/update-a-contact.md

frappe_apollo/third_party/update-contact-status-sequence.md

frappe_apollo/third_party/use-oauth-20-authorization-flow-to-access-apollo-user-information-partners

frappe_apollo/uninstall.py:
⋮
│def before_uninstall() -> None:
⋮

frappe_apollo/webhook.py:
⋮
│@frappe.whitelist(allow_guest=True)
│def handle():
⋮
│def process_webhook(payload):
⋮

frappe_apollo/workspace_sidebar/apollo.json

license.txt

pyproject.toml

```
# 12 Glossary

Alphabetical glossary of domain and technical terms utilized throughout `frappe_apollo` ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1)).

## Terms & Definitions

| Term | Definition |
| :--- | :--- |
| **`Apollo Account`** | DocType storing credentials (API Key, OAuth tokens) for a specific Apollo.io workspace ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py:5)). |
| **`Apollo Field`** | DocType encapsulating custom field definitions synchronized to Apollo custom fields ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:5)). |
| **`Apollo Field Apollo ID`** | Child DocType attached to `Apollo Field` storing mapped Apollo custom field IDs per account ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.py:1)). |
| **`ApolloClient`** | REST API wrapper handling request execution, authentication headers, and token refresh ([`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:9)). |
| **`Cadence`** | Multi-touch sales outreach schedule template defined in `frappe_cadence` ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence/cadence.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence/cadence.py:5)). |
| **`Cadence Apollo ID`** | Child DocType tracking which Apollo Account is assigned to process a Frappe Cadence for a given sender ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence_apollo_id/cadence_apollo_id.json`](apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence_apollo_id/cadence_apollo_id.json:1)). |
| **`CRM Lead`** | Sales prospect record managed within `crm` ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/crm_lead/crm_lead.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/crm_lead/crm_lead.py:3)). |
| **`FS Job` / `frappe.enqueue`** | Background tasks processed asynchronously via `frappe.enqueue` or `frappe_controller` (`FS Job`) governed by `hooks.controller_events` ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:162)). |
| **`Multi Channel Cadence`** | Active instance of a Cadence executed against a specific recipient ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py:5)). |
| **`Sequence`** | Apollo.io automated email campaign (`emailer_campaign`). |
| **`Webhook Bearer Token`** | Secret key validating inbound engagement events posted by Apollo.io ([`apps/frappe_apollo/frappe_apollo/webhook.py`](apps/frappe_apollo/frappe_apollo/webhook.py:9)). |

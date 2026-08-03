# 05 Building Block View

The Building Block View defines the static structural components of `frappe_apollo` ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1)).

## Level 1: C2 Container View

Refer to [`c4/02-container.md`](../c4/02-container.md) for full container descriptions.

```mermaid
erDiagram
    "Frappe Desk" ||--o{ "Gunicorn" : "sends_http_requests_and_api_calls"
    "Gunicorn" ||--o{ "MariaDB" : "reads_and_writes_doctypes"
    "Gunicorn" ||--o{ "Worker FS" : "enqueues_fs_and_rq_jobs"
    "Worker FS" ||--o{ "MariaDB" : "updates_document_states"
    "Worker FS" ||--o{ "Apollo REST API (api.apollo.io)" : "executes_rest_api_calls"
    "Apollo REST API (api.apollo.io)" ||--o{ "Gunicorn" : "delivers_webhook_payloads"
```

## Level 2: C3 Component View

Refer to [`c4/03-component.md`](../c4/03-component.md) for individual component field definitions and relationships.

```mermaid
erDiagram
    "Apollo Account" ||--o{ "Cadence Apollo ID" : "scopes_sequence_account_assignment"
    "Apollo Account" ||--o{ "CRM Lead Apollo ID" : "scopes_contact"
    "Apollo Account" ||--o{ "Email Account Apollo ID" : "scopes_mailbox"
    "Apollo Account" ||--o{ "Apollo Field Apollo ID" : "scopes_custom_field"
    "Cadence" ||--o{ "Cadence Apollo ID" : "assigns_apollo_account"
    "CRM Lead" ||--o{ "CRM Lead Apollo ID" : "contains_apollo_contact_mappings"
    "Email Account" ||--o{ "Email Account Apollo ID" : "contains_apollo_mailbox_mappings"
    "Apollo Field" ||--o{ "Apollo Field Apollo ID" : "contains_apollo_field_mappings"
    "Multi Channel Cadence" }|..|| "Apollo Account" : "references_apollo_account"
    "Communication" }|..|| "Multi Channel Cadence" : "references_mcc"
    "ApolloClient" ||--|| "Apollo Account" : "uses_account_credentials"
    "OAuth Callback" ||--|| "Apollo Account" : "updates_oauth_tokens"
    "Webhook Receiver" ||--|| "Cadence Provider" : "dispatches_event_reports"
```

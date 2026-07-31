# 08 Cross-Cutting Concepts

This section documents architecture-wide patterns and mechanisms across `frappe_apollo` ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1)).

## Cross-Cutting Patterns

### 1. Authentication & Secrets Management
- **API Key & OAuth Tokens**: Stored in `Apollo Account` DocType. Secret credentials (`api_key`, `client_secret`, `access_token`, `refresh_token`, `webhook_bearer_token`) use Frappe's `Password` fieldtype ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.json`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.json:28)). All frontend strength checks for these tokens are disabled via `disable_password_checks()` in [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.js`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.js:3).
- **Token Auto-Refresh**: In `ApolloClient._request()`, if the access token has expired or an `HTTP 401` status is returned, `_refresh_oauth_token()` automatically requests a new token pair using the stored `refresh_token` ([`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:101)).

### 2. Error Handling & Rate Limiting (`controller_events`)
- **Controller Rate Limits**: Declared in [`hooks.controller_events`](apps/frappe_apollo/frappe_apollo/hooks.py:162) to bound execution frequencies and configure `FS Job` retries/timeouts via `frappe_controller`:
  - `rate_limit_per_minute`: 50
  - `rate_limit_per_hour`: 200
  - `rate_limit_per_day`: 600
  - `retries`: 3
  - `timeout`: 300
- **Rate Limit Exception Handling**: `ApolloRateLimitError` is raised on `HTTP 429` responses ([`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:107)).

### 3. Asynchronous Job Resumption (`wait_for_event`)
- Background jobs (`FS Job`) that require missing credentials, account authorizations, or custom field mappings utilize `wait_for_event()` from `frappe_controller.utils.controller` ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py:23)).
- The job enters a suspended state without consuming worker threads until the target DocType event (e.g., `doc:Apollo Account:on_update`) emits a matching condition.

### 4. Webhook Security Verification
- Inbound requests to `/api/method/frappe_apollo.webhook.handle` require a `Bearer` token in the `Authorization` header ([`apps/frappe_apollo/frappe_apollo/webhook.py`](apps/frappe_apollo/frappe_apollo/webhook.py:9)).
- The endpoint queries active `Apollo Account` records and validates the bearer token before delegating execution to `process_webhook` in the FastStream background worker (`FS Job`).

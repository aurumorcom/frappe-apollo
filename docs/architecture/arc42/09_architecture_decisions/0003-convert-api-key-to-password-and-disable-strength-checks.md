# 0003 - Convert API Key to Password Type, Disable Strength Checks, and Add Workspace Sidebar

- **Status**: Accepted
- **Date**: 2026-07-31

## Context

In `Apollo Account` ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.json`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.json:1)), `api_key` was previously defined with `"fieldtype": "Data"`, leaving plain-text secrets unencrypted in the database table and inconsistent with other credentials (`client_secret`, `access_token`, `refresh_token`, `webhook_bearer_token`).

Furthermore, when entering long, high-entropy tokens or keys into `Password` fields on the `Apollo Account` form, Frappe's `ControlPassword` control automatically invoked the backend endpoint `frappe.core.doctype.user.user.test_password_strength`. For complex secrets, the `zxcvbn` password evaluator generated `guesses` integers exceeding 64-bit signed/unsigned range ($> 2^{63}-1$), causing Rust's `orjson.dumps()` in Frappe's response builder to raise `TypeError: Integer exceeds 64-bit range`.

Additionally, form field visibility for `status` and `expired` was noisy, list views lacked status indicators, and sidebar navigation across Apollo and Cadence workspaces lacked standardized bundling without section breaks.

## Decision

1. **Convert `api_key` to `Password` FieldType**:
   - Updated `api_key` field definition in `apollo_account.json` from `Data` to `Password`. All credentials in `Apollo Account` now persist encrypted in Frappe's `__Auth` table.
   - Refactored `ApolloClient._get_headers()` in [`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:118) and `queue_get_email_accounts()` in [`apps/frappe_apollo/frappe_apollo/apollo/doctype/email_account/email_account.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/email_account/email_account.py:8) to access `api_key` via `doc.get_password("api_key")`.

2. **Disable Frontend Password Strength Checks**:
   - Added `onload` handler in [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.js`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.js:1) calling `.disable_password_checks()` on `api_key`, `client_secret`, `refresh_token`, `access_token`, and `webhook_bearer_token`.
   - Bypasses `test_password_strength` RPC execution on keyup for non-user API tokens and prevents `orjson` integer overflow crashes.

3. **Form & List View UI Optimization**:
   - Set `"hidden": 1` on `status` and `expired` fields in `apollo_account.json` to declutter form inputs.
   - Set `"in_list_view": 1` on `account_name` and `status` fields to provide clear list-level visibility.

4. **Standard Workspace Sidebars**:
   - Created `apps/frappe_apollo/frappe_apollo/workspace_sidebar/apollo.json` bundling main integration DocTypes (`Apollo Account`, `Apollo Field`, `Cadence Provider`, `Cadence`, `Multi Channel Cadence`, `Email Account`, `CRM Lead`, `Communication`) without section breaks.
   - Flattened `apps/frappe_cadence/frappe_cadence/workspace_sidebar/cadence.json` by removing section breaks and converting all items to top-level link elements (`"child": 0`).

## Consequences

- Fully secures all Apollo credentials using AES/Fernet encryption in Frappe's `__Auth` table.
- Eliminates 64-bit integer overflow crashes during API secret entry.
- Provides clean, flat navigation across Apollo and Cadence workspaces in Frappe Desk.

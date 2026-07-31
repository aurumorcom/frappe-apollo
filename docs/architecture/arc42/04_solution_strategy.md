# 04 Solution Strategy

This section highlights the fundamental strategy decisions behind `frappe_apollo` ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1)).

## Fundamental Architectural Strategies

### 1. Multi-Account Scoped Mapping
- **Problem**: Large sales organizations utilize multiple Apollo workspace accounts and sender mailboxes.
- **Strategy**: Attach child tables (`Cadence Apollo ID`, `CRM Lead Apollo ID`, `Email Account Apollo ID`, `Apollo Field Apollo ID`) to core DocTypes to support 1:N account-scoped mappings ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence_apollo_id/cadence_apollo_id.json`](apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence_apollo_id/cadence_apollo_id.json:1)).

### 2. Event-Driven Asynchronous Enqueuing & Resumption (`frappe_controller` FS Jobs)
- **Problem**: API calls to Apollo are subject to rate limiting and temporary account authorization delays.
- **Strategy**: Offload sync logic to FastStream worker queues (`FS Job` via `frappe_controller`) and utilize `wait_for_event()` primitives from `frappe_controller.utils.controller` to pause and auto-resume jobs when prerequisite account or field state becomes valid ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py:23)).

### 3. Load Balancing Across Active Sender Accounts
- **Problem**: Distributing outreach load across multiple Apollo accounts prevents sender fatigue and mailbox throttle limits.
- **Strategy**: Calculate active cadence load per account in `before_save` hook of `Multi Channel Cadence` and assign the least-loaded authorized account to new cadence runs ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py:51)).

### 4. Dynamic Field Hashing and Apollo Custom Field Sync
- **Problem**: Apollo sequence templates require specific custom field IDs for dynamic subject and body substitution.
- **Strategy**: Compute MD5 hash of `cadence_step_field` names to generate unique `Apollo Field` documents and create matching custom fields in Apollo via `ApolloClient.create_custom_field()` ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:54)).

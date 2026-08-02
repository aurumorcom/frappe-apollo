# 04 Solution Strategy

This section highlights the fundamental strategy decisions behind `frappe_apollo` ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1)).

## Fundamental Architectural Strategies

### 1. Multi-Account Scoped Mapping
- **Problem**: Large sales organizations utilize multiple Apollo workspace accounts and sender mailboxes.
- **Strategy**: Attach child tables (`Cadence Apollo ID`, `CRM Lead Apollo ID`, `Email Account Apollo ID`, `Apollo Field Apollo ID`) to core DocTypes to support 1:N account-scoped mappings ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence_apollo_id/cadence_apollo_id.json`](apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence_apollo_id/cadence_apollo_id.json:1)).

### 2. Event-Driven Asynchronous Enqueuing & Resumption (`frappe_controller` FS Jobs)
- **Problem**: API calls to Apollo are subject to rate limiting and temporary account authorization delays.
- **Strategy**: Offload sync logic to FastStream worker queues (`FS Job` via `frappe_controller`) and utilize `wait_for_event()` primitives from `frappe_controller.utils.controller` to pause and auto-resume jobs when prerequisite account or field state becomes valid ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py:23)).

### 3. Load Balancing Across Active Sender Accounts and Mailboxes
- **Problem**: Apollo enforces strict platform limits. Free accounts are limited to a single mailbox and a maximum of 2 active sequences, restricting outbound volume. Paid accounts allow multiple mailboxes but still require efficient distribution to prevent sender fatigue.
- **Strategy**: Implement two distinct functional load balancing options:
  1. **One Cadence to Multiple Apollo Accounts**: Load balance a single Frappe cadence across multiple free Apollo accounts (each possessing a single mailbox) to bypass sequence and volume limitations. Calculate active cadence load per account in the `before_save` hook of `Multi Channel Cadence` and assign the least-loaded authorized account to new cadence runs ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py:51)).
  2. **One Cadence to Single Apollo Account (Multiple Mailboxes)**: Route a single Frappe cadence to a single paid Apollo account, utilizing Apollo's native multi-mailbox features to distribute the outreach load.

### 4. Dynamic Field Hashing and Apollo Custom Field Sync
- **Problem**: Apollo sequence templates require specific custom field IDs for dynamic subject and body substitution.
- **Strategy**: Compute MD5 hash of `cadence_step_field` names to generate unique `Apollo Field` documents and create matching custom fields in Apollo via `ApolloClient.create_custom_field()` ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:54)).

### 5. Non-Blocking Resumption & Precise Event Condition Matching
- **Problem**: Asynchronous background jobs can experience race conditions during cold starts (e.g. mailbox sync pending, field mapping in progress, or unauthorized account authorization). Unhandled exceptions or bare `raise SuspendJob` calls freeze jobs or cause payload corruption.
- **Strategy**:
  - Always register explicit `wait_for_event()` listeners before suspending execution (e.g. `doc:Email Account:<name>:on_update` in [`Multi Channel Cadence`](apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py:144) and `doc:Apollo Account:<name>:on_update` in [`CRM Lead`](apps/frappe_apollo/frappe_apollo/apollo/doctype/crm_lead/crm_lead.py:108)).
  - Re-query and re-validate document state (such as `email_account_name` and `step_doc`) immediately post-resumption.
  - Scope `wait_for_event` condition expressions precisely by `account` and `sender` or `apollo_sequence_id` to eliminate false-positive job wake-ups in multi-account environments ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:55)).

# 04 Solution Strategy

This section highlights the fundamental strategy decisions behind `frappe_apollo` ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1)).

## Fundamental Architectural Strategies

### 1. Multi-Account Scoped Mapping
- **Problem**: Large sales organizations utilize multiple Apollo workspace accounts and sender mailboxes.
- **Strategy**: Attach child tables (`CRM Lead Apollo ID`, `Email Account Apollo ID`, `Apollo Field Apollo ID`) to core DocTypes to support 1:N account-scoped mappings.

### 2. Event-Driven Asynchronous Enqueuing & Resumption (`frappe_controller` FS Jobs)
- **Problem**: API calls to Apollo are subject to rate limiting and temporary account authorization delays.
- **Strategy**: Offload sync logic to FastStream worker queues (`FS Job` via `frappe_controller`) and utilize `wait_for_event()` primitives from `frappe_controller.utils.controller` to pause and auto-resume jobs when prerequisite account or field state becomes valid ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py:23)).

### 3. Load Balancing Across Active Sender Accounts and Mailboxes
- **Problem**: Apollo enforces strict platform limits. Free accounts are limited to a single mailbox and a maximum of 2 active sequences, restricting outbound volume. Paid accounts allow multiple mailboxes but still require efficient distribution to prevent sender fatigue.
- **Strategy**: Because Frappe centralizes all logic, we use a single Apollo sequence per Account.
  1. **Multiple Cadences to 1 Apollo Sequence**: Frappe handles all A/B testing and logic. All Frappe cadences push contacts into a single standardized 4-step sequence within an Apollo account, allowing free accounts (limited to 2 sequences) to run infinite Frappe cadences.
  2. **Load Balancing via Mailboxes**: For paid Apollo accounts with multiple mailboxes, Apollo's native multi-mailbox load balancing is utilized under that single sequence. For multiple free accounts, Frappe distributes contacts across accounts.

### 4. Generic Field Sync and Frappe-side Content Generation
- **Problem**: Apollo sequence templates require specific custom field IDs for dynamic subject and body substitution, but we are using a single sequence for all cadences.
- **Strategy**: Provision generic standard fields (e.g. `subject_X`, `body_X`, `message_X`) dynamically based on Cadence required steps. Frappe will render the actual content based on the Cadence logic and populate these generic custom fields for each contact right before they are added to the single sequence.

### 5. Non-Blocking Resumption & Precise Event Condition Matching
- **Problem**: Asynchronous background jobs can experience race conditions during cold starts (e.g. mailbox sync pending, field mapping in progress, or unauthorized account authorization). Unhandled exceptions or bare `raise SuspendJob` calls freeze jobs or cause payload corruption.
- **Strategy**:
  - Always register explicit `wait_for_event()` listeners before suspending execution (e.g. `doc:Email Account:<name>:on_update` in [`Multi Channel Cadence`](apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py:144) and `doc:Apollo Account:<name>:on_update` in [`CRM Lead`](apps/frappe_apollo/frappe_apollo/apollo/doctype/crm_lead/crm_lead.py:108)).
  - Re-query and re-validate document state (such as `email_account_name` and `step_doc`) immediately post-resumption.
  - Scope `wait_for_event` condition expressions precisely by `account` to eliminate false-positive job wake-ups in multi-account environments ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:55)).

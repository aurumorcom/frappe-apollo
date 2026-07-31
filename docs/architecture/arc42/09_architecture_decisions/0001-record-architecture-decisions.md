# 0001 - Baseline Architectural Decisions for Frappe Apollo Integration

- **Status**: Accepted
- **Date**: 2026-07-17

## Context

The `frappe_apollo` custom application integrates Apollo.io multi-channel cadences into Frappe CRM ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1)). We require a robust mechanism to manage multi-account authentication, sequence synchronization, contact mapping, field mapping, and event tracking while preventing API rate limits from blocking web workers.

## Decisions

### ADR 1: Account-Scoped Child Table Mappings
- **Decision**: Store external Apollo IDs (`sequence_id`, `contact_id`, `mailbox_id`, `field_id`) in dedicated child tables (`Cadence Apollo ID`, `CRM Lead Apollo ID`, `Email Account Apollo ID`, `Apollo Field Apollo ID`) keyed by `Apollo Account` ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence_apollo_id/cadence_apollo_id.json`](apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence_apollo_id/cadence_apollo_id.json:1)).
- **Consequence**: Allows a single Frappe CRM instance to seamlessly map entities across multiple Apollo accounts without data collisions.

### ADR 2: Event-Driven Resumption via `wait_for_event`
- **Decision**: Leverage `wait_for_event()` from `frappe_controller` inside FastStream background workers (`FS Job`) when dependent records (such as authorized `Apollo Account` or created `Apollo Field` mappings) are not yet ready ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py:23)).
- **Consequence**: Avoids polling loops or worker thread starvation. Jobs sleep until state change events are fired.

### ADR 3: Automatic Load Balancing Across Accounts
- **Decision**: In `Multi Channel Cadence.before_save`, automatically count active outreach campaigns per authorized sender account and assign the least-loaded account ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py:51)).
- **Consequence**: Equalizes send volumes across accounts and mitigates mailbox throttling.

### ADR 4: Asynchronous Webhook Processing via `frappe_controller`
- **Decision**: The public webhook endpoint `/api/method/frappe_apollo.webhook.handle` performs authentication and enqueues payload processing as an `FS Job` (`frappe_controller`) configured in `controller_events` ([`apps/frappe_apollo/frappe_apollo/webhook.py`](apps/frappe_apollo/frappe_apollo/webhook.py:29)).
- **Consequence**: Ensures HTTP responses return immediately with 200 OK while processing engagement events asynchronously through Redis streams.

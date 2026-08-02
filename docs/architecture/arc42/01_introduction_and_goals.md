# 01 Introduction and Goals

`frappe_apollo` is a specialized Frappe custom application designed to integrate Apollo.io's multi-channel sales engagement platform into the Frappe CRM and Cadence automation ecosystem ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1)).

## Requirements Overview

The primary business goal of this project is to utilize Apollo.io as the engine for cold email campaigns. Because Apollo enforces strict platform limits (especially on free tiers), the system must support flexible account configurations to maximize throughput:
- **Free Account Workaround**: Load balance campaigns across multiple free Apollo accounts, each configured with a single sender mailbox and constrained to a maximum of 2 active sequences per account.
- **Paid Account Utilization**: Support a single paid Apollo account configured with multiple sender mailboxes for centralized campaign execution.

The system bridges local CRM leads, outreach cadences, and scheduled communications with Apollo sequences, contacts, mailboxes, and custom fields to accommodate these configurations.

### Key Functional Requirements
- **OAuth 2.0 & API Key Authentication**: Securely connect Apollo workspace accounts via OAuth callback or API Key ([`apps/frappe_apollo/frappe_apollo/oauth.py`](apps/frappe_apollo/frappe_apollo/oauth.py:7)).
- **Sequence Provisioning**: Automatically create and map multi-touch email sequences in Apollo when a Cadence document is configured ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence/cadence.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence/cadence.py:5)).
- **Dynamic Custom Field Generation**: Provision unique custom fields in Apollo for subject and body templates, allowing dynamic per-contact personalization ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:8)).
- **Contact & Cadence Assignment**: Upsert CRM leads as Apollo contacts and assign them to mapped sequence campaigns with sender load balancing ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py:5)).
- **Webhook Engagement Tracking**: Real-time asynchronous processing of email opens, clicks, replies, and bounces from Apollo webhooks ([`apps/frappe_apollo/frappe_apollo/webhook.py`](apps/frappe_apollo/frappe_apollo/webhook.py:5)).

## Quality Goals

| Quality Goal | Motivation / Scenario | Target Metric |
| :--- | :--- | :--- |
| **Reliability** | Ensure no data loss during rate limits or transient network failures with Apollo API. | Exponential backoff retries (3 retries) and job suspension/resumption via `frappe_controller` (`FS Job`) ([`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:107)). |
| **Data Consistency** | Maintain strict multi-account mapping between Frappe entities and Apollo IDs. | Child table ID mappings (`Cadence Apollo ID`, `CRM Lead Apollo ID`, `Email Account Apollo ID`, `Apollo Field Apollo ID`). |
| **Performance** | Non-blocking webhooks and responsive UI under high lead volumes. | Asynchronous FastStream worker queue execution (`frappe_controller` `FS Job`) for all API sync operations governed by `controller_events`. |

## Stakeholders

| Role | Expectation |
| :--- | :--- |
| **Sales Representatives** | Automated outbound cadence execution without leaving Frappe CRM. |
| **Sales Operations / Admins** | Seamless account load balancing and reliable tracking of email engagement metrics. |
| **System Engineers** | Clean failure isolation, non-blocking webhook processing, and compliant rate-limit handling. |

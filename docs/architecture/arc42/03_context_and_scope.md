# 03 Context and Scope

This chapter describes the external interfaces and operational environment of `frappe_apollo`.

## Business & System Context

Detailed C1 Entity Relationship modeling is defined in [`c4/01-context.md`](../c4/01-context.md).

```mermaid
erDiagram
    "User" ||--o{ "Apollo Account" : "manages_and_authenticates"
    "User" ||--o{ "CRM Lead" : "creates_and_manages"
    "Apollo Account" ||--o{ "Apollo auth and sequences" : "authenticates_via_oauth_and_api_key"
    "Multi Channel Cadence" ||--o{ "Apollo auth and sequences" : "schedules_sequences_and_contacts"
    "Apollo auth and sequences" ||--o{ "Mailbox Provider send-email" : "dispatches_outbound_cadence_emails"
    "Mailbox Provider send-email" ||--o{ "CRM Lead" : "delivers_emails_to_prospects"
    "Apollo webhook delivery" ||--o{ "Webhook Endpoint" : "posts_webhook_engagement_events"
```

## External Interface Mapping

| Interface | Protocol | Direction | Description |
| :--- | :--- | :--- | :--- |
| **Apollo OAuth Endpoint** | HTTPS GET / POST | Outbound | Authorizes workspace accounts and exchanges authorization codes ([`apps/frappe_apollo/frappe_apollo/oauth.py`](apps/frappe_apollo/frappe_apollo/oauth.py:25)). |
| **Apollo API v1** | HTTPS REST (JSON) | Outbound | Invokes sequence creation, contact insertion, mailbox queries, and field updates ([`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:13)). |
| **Apollo Webhook Receiver** | HTTPS POST | Inbound | Receives engagement payload notifications (`message_sent`, `message_opened`, `message_replied`, `bounce`) ([`apps/frappe_apollo/frappe_apollo/webhook.py`](apps/frappe_apollo/frappe_apollo/webhook.py:5)). |

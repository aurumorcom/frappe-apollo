# 02 Architecture Constraints

This section lists technical, organizational, and regulatory constraints imposed on `frappe_apollo` ([`apps/frappe_apollo/pyproject.toml`](apps/frappe_apollo/pyproject.toml:1)).

## Technical Constraints

| Constraint | Specification / Source | Impact on Architecture |
| :--- | :--- | :--- |
| **Language & Runtime** | Python >= 3.14 ([`apps/frappe_apollo/pyproject.toml`](apps/frappe_apollo/pyproject.toml:7)) | Application code must strictly adhere to modern Python 3.14 features and typing standards. |
| **Application Framework** | Frappe Framework v16 / Bench Architecture | All data structures must be encapsulated as DocTypes or Custom Fields ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:11)). |
| **Required App Dependencies** | `frappe_controller`, `frappe_cadence`, `crm` ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:11)) | Must extend base classes (`BaseCadenceProvider`) and hook into standard workflow lifecycle methods. |
| **Background Processing** | Redis Streams & FastStream Workers (`frappe_controller` `FS Job`) | Long-running I/O calls to Apollo REST API must run inside enqueued `FS Job` instances managed via `frappe_controller.utils.background_jobs.enqueue()`. |
| **External API Rate Limits** | Apollo.io REST API v1 (`https://api.apollo.io/api/v1`) | Must support rate limit error detection (`HTTP 429`) and controller event rate limiting configured via `controller_events` in [`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:162). |

## Organizational & Operational Constraints

| Constraint | Detail |
| :--- | :--- |
| **Apollo Account Limits (Free Tier)** | Free Apollo accounts are strictly limited to 2 active sequences and 1 mailbox per account. The system bypasses this by utilizing only ONE sequence per account and distributing Frappe cadences across multiple free accounts. |
| **Apollo Account Limits (Paid Tier)** | Paid Apollo accounts support multiple mailboxes per account. The system utilizes ONE sequence and leverages Apollo's native multi-mailbox load balancing. |
| **Apollo Sequence Step Limit** | Under the single sequence engine architecture, Apollo campaigns are restricted to a maximum of 4 standardized steps (emails). Frappe cadences must adhere to this step limit constraint. |
| **Multi-Tenancy** | Accounts are namespaced per Frappe site. Multi-account mapping is required to support multiple sales accounts per site. |
| **Security & Privacy** | API Keys, OAuth Secrets, and Webhook Bearer Tokens must be stored as encrypted `Password` field types ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.json`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.json:38)). |

# 11 Risks and Technical Debt

This section outlines technical debt, potential architectural risks, and mitigation strategies for `frappe_apollo` ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1)).

## Identified Technical Debt & Architectural Risks

### 1. Hardcoded Base URLs & OAuth Endpoints
- **Risk**: Apollo API endpoints (`https://api.apollo.io/api/v1` and `https://app.apollo.io/#/oauth/authorize`) are hardcoded inside client methods ([`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:13)).
- **Impact**: Limits staging/sandbox testing environments or domain endpoint upgrades without code modifications.
- **Mitigation**: Move base URLs into configuration settings or environment variables.

### 2. Print & Debug Statement Traces
- **Risk**: Debug print statements (`print("DEBUG: Client is", client)`) exist in production code paths ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence/cadence.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence/cadence.py:93)).
- **Impact**: Pollutes worker logs and stdout.
- **Mitigation**: Replace raw `print()` statements with structured `frappe.logger().debug()` calls.

### 3. API Rate Limit Spikes
- **Risk**: Apollo imposes strict per-minute/per-day rate limits on contact creation and sequence assignment ([`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:107)).
- **Impact**: High-volume lead imports could trigger `ApolloRateLimitError` across background workers.
- **Mitigation**: Utilize `controller_events` in [`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:162) to enforce rate limits and retries on `FS Job` executions.

### 4. Dynamic Field Hash Uniqueness
- **Risk**: Dynamic custom fields are auto-named using MD5 hash prefixes (`md5(cadence_step_field)[:10]`) ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:55)).
- **Impact**: Truncating hashes to 10 characters presents a theoretical collision risk across thousands of cadence steps.
- **Mitigation**: Verify uniqueness or expand hash prefix length if collision issues arise.

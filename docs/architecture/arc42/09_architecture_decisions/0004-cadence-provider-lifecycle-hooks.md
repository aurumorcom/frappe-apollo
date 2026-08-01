# ADR 4: Cadence Provider Setup via App Lifecycle Hooks

## Status
Accepted

## Context
The `frappe_apollo` application ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1)) integrates heavily with `frappe_cadence`, functioning as a provider for multi-channel sales cadences. For the integration to work seamlessly out of the box, the system needs an `Apollo` record in the `Cadence Provider` DocType. 
Manually requiring system administrators to create this record introduces friction and increases the likelihood of human error or misconfiguration (e.g., missing the "Email" channel assignment or priority settings). Conversely, leaving orphan metadata upon uninstallation pollutes the database.

## Decision
We decided to automate the provisioning and teardown of the Apollo provider integration utilizing Frappe's native app lifecycle hooks:

1. **`after_install` Hook**:
   - Implemented in [`apps/frappe_apollo/frappe_apollo/install.py`](apps/frappe_apollo/frappe_apollo/install.py:6).
   - Automatically provisions a `Cadence Provider` document named `"Apollo"`, enabled by default, and associated with the `"Email"` channel at `priority = 1`.
   - Includes idempotency checks to ensure safe re-runs and guards against the absence of the `Cadence Provider` DocType.

2. **`before_uninstall` Hook**:
   - Implemented in [`apps/frappe_apollo/frappe_apollo/uninstall.py`](apps/frappe_apollo/frappe_apollo/uninstall.py:6).
   - Automatically deletes the `"Apollo"` `Cadence Provider` document and its associated child table records (`Cadence Provider Channel`) when the app is removed from a site.

## Consequences

### Positive
- **Zero-Touch Setup**: Reduces onboarding friction by configuring the provider automatically upon running `bench install-app frappe_apollo`.
- **Clean Uninstallation**: Prevents orphan `Cadence Provider` records and dangling foreign keys upon `bench uninstall-app frappe_apollo`.
- **Idempotency**: The installation logic safely handles upgrades and repeated executions without duplicating the `"Email"` channel row or overwriting existing user configurations.

### Negative
- **Tightly Coupled Dependency**: The install/uninstall scripts strictly depend on `frappe_cadence`'s `Cadence Provider` DocType schema. If `frappe_cadence` introduces breaking schema changes to this DocType, the hooks must be updated. This risk is mitigated by using defensive `frappe.db.exists` guard clauses.

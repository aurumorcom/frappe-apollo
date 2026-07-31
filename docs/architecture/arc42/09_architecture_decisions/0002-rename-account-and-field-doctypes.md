# 0002 - Rename Account, Field, and Field Apollo ID DocTypes

- **Status**: Accepted
- **Date**: 2026-07-20

## Context

Originally, `frappe_apollo` declared DocTypes named `Account`, `Field`, and `Field Apollo ID`. These generic identifiers created namespace confusion with core Frappe / ERPNext DocTypes (such as financial `Account` or Frappe schema `DocField`) and reduced domain specificity in custom field mapping and multi-account integrations.

## Decision

We renamed the following DocTypes and their associated controllers, JSON definitions, and link fields:
1. `Account` -> `Apollo Account` ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py:5))
2. `Field` -> `Apollo Field` ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:5))
3. `Field Apollo ID` -> `Apollo Field Apollo ID` ([`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.py:1))

In addition, all link options (`cadence_apollo_id.json`, `crm_lead_apollo_id.json`, `email_account_apollo_id.json`, `custom_field.json`), event signals (`doc:Apollo Account:on_update`, `doc:Apollo Field:on_update`), and background job method paths (`frappe_apollo.apollo.doctype.apollo_field.apollo_field.provision_a_field`) were updated to reflect the `Apollo` namespace prefix.

## Consequences

- Resolves naming collisions with core Frappe ecosystem models.
- Enhances code clarity and consistency across `frappe_apollo`.
- Requires updated architectural models, event listener strings, and fixture configurations.

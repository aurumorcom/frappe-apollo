## Breaking Changes

- **Public API Renaming**
  Internal functions have been renamed to public API functions (`add_contact_to_sequence`, `update_sequence_contact_status`, `toggle_cadence_mccs`), and contact lookup has been simplified using `apollo_contact_id`.
  - Migration: Update all external call sites to use the newly renamed public API function names and adapt to the simplified contact lookup using `apollo_contact_id`.
  - Commits: [35ce458](https://github.com/aurumorinc/frappe-apollo/commit/35ce4584), [60f1195](https://github.com/aurumorinc/frappe-apollo/commit/60f11955), [3288df3](https://github.com/aurumorinc/frappe-apollo/commit/3288df3d)

- **Sequence Contact Management API Renaming**
  Public API functions for sequence contact management (`add_contact_to_sequence`, `update_sequence_contact_status`, `toggle_cadence_mccs`) have been renamed with high severity impact.
  - Migration: Update all external call sites to use the newly renamed public API function names and adapt to the simplified contact lookup using `apollo_contact_id`.

## New Features

- **Background Job Configurations**
  Added rate limiting, retry configurations, and timeouts for asynchronous background jobs, while updating queue priority from "short" to "low" for lead contact operations.
  - Commits: [d0ea4de](https://github.com/aurumorinc/frappe-apollo/commit/d0ea4de4), [a3259a5](https://github.com/aurumorinc/frappe-apollo/commit/a3259a53)

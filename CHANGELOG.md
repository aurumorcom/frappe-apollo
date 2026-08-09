## Features

* **Email Account Sync Hook (`on_update`)**
  Added the `on_update` hook for the Email Account doctype to automatically trigger sync and alias mapping processes ([4d5298e](https://github.com/aurumorcom/frappe-apollo/commit/4d5298e9)).
* **Email Account Helper Functions**
  Refactored `get_email_accounts` using modular helper functions to improve maintainability ([81e4ffc](https://github.com/aurumorcom/frappe-apollo/commit/81e4ffcd)).
* **Scheduler Event Renaming**
  Renamed the internal scheduler event associated with email account synchronization ([7cf8e8e](https://github.com/aurumorcom/frappe-apollo/commit/7cf8e8e8)).

## Other

* **Reentrancy Flag Test Coverage**
  Added a test case to verify that the `is_apollo_email_account_update` reentrancy flag is properly reset within the `finally` block of `get_email_accounts()` ([bd64896](https://github.com/aurumorcom/frappe-apollo/commit/bd648965)).

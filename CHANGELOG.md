## New Features

* **Asynchronous Job Queue for Contact Creation and MCC Scheduling**
  Replaced legacy event waiting mechanisms with asynchronous job queue enqueuing and direct promise results for contact creation and MCC scheduling flows.
  Commits: [`bdb212d`](https://github.com/aurumorcom/frappe-apollo/commit/bdb212db), [`2b07bce`](https://github.com/aurumorcom/frappe-apollo/commit/2b07bceb), [`6540ef6`](https://github.com/aurumorcom/frappe-apollo/commit/6540ef60)

## Improvements

* **MCC Scheduling Test Assertions**
  Updated test assertions and event emission to verify that `add_contact_to_sequence` correctly suspends awaiting child job completion.
  Commits: [`ea68e33`](https://github.com/aurumorcom/frappe-apollo/commit/ea68e33b)

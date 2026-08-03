# Changelog v16.5.0

## Features

* **Apollo Sequence Provisioning**: Added automated sequence provisioning triggered upon account authorization, enqueuing a background job when an `ApolloAccount` status transitions to `Authorized` (Commits: [9a7e7a1](https://github.com/aurumorinc/frappe-apollo/commit/9a7e7a1f), [dbd0e0b](https://github.com/aurumorinc/frappe-apollo/commit/dbd0e0bf)).

## Improvements

* **Apollo Cadence Refactoring**: Simplified cadence and field provisioning to utilize a single generic Apollo sequence per account with dynamic step management (Commits: [500d518](https://github.com/aurumorinc/frappe-apollo/commit/500d5180), [0976a5a](https://github.com/aurumorinc/frappe-apollo/commit/0976a5a1), [72e99ba](https://github.com/aurumorinc/frappe-apollo/commit/72e99bad)).
* **Apollo Testing**: Added and updated comprehensive unit and integration test suites covering the `ApolloAccount` provisioning workflow and sequence step management (Commits: [38f64b7](https://github.com/aurumorinc/frappe-apollo/commit/38f64b77), [3fc6c53](https://github.com/aurumorinc/frappe-apollo/commit/3fc6c531), [738cd5f](https://github.com/aurumorinc/frappe-apollo/commit/738cd5f4)).
* **Code Formatting**: Applied PEP 8 import ordering rules, removed trailing whitespace, and cleaned up comments across source and test files (Commits: [64dac44](https://github.com/aurumorinc/frappe-apollo/commit/64dac446), [2fcf875](https://github.com/aurumorinc/frappe-apollo/commit/2fcf8753), [5b0fd78](https://github.com/aurumorinc/frappe-apollo/commit/5b0fd780)).

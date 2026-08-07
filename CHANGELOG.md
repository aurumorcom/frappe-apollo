## New Features

- **Apollo Sequence Handling**
  - Added graceful handling and search-based lookup for Apollo sequences, including validation, user-friendly messaging, cadence disabling, and paginated search.
  - Commits: [52c6510](https://github.com/aurumorinc/frappe-apollo/commit/52c65105), [215a3c4](https://github.com/aurumorinc/frappe-apollo/commit/215a3c48)

## Improvements

- **Apollo Client Unit Tests**
  - Added unit tests for the `get_sequence` method in `ApolloClient` to verify successful retrieval and missing sequence handling with mocked `search_sequences`.
  - Commit: [bb66307](https://github.com/aurumorinc/frappe-apollo/commit/bb663071)

- **Apollo Method Renaming**
  - Renamed `update_contact_status_sequence()` method to `update_sequence_contact_status()` across the codebase, call sites, tests, and documentation for consistent naming patterns.
  - Commit: [7835c00](https://github.com/aurumorinc/frappe-apollo/commit/7835c006)

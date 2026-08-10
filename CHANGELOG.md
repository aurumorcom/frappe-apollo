## Fixes

* **Apollo API Response Handling for Contact Creation**
  - Updated contact creation logic to properly handle both dictionary and string responses returned from the Apollo client.
  - Implemented robust ID extraction to retrieve contact IDs from nested response structures or fall back to utilizing string responses directly.
  - Added the `ignore_mandatory` flag when persisting leads to prevent unexpected validation errors during save operations.
  - Included comprehensive unit test coverage to verify correct ID extraction across different payload structures.
  - Commits: [2eb4143](https://github.com/aurumorcom/frappe-apollo/commit/2eb4143a), [9ffc078](https://github.com/aurumorcom/frappe-apollo/commit/9ffc0781)

## Features

* **Rate Limit and Deduplication for Sequence Updates**
  - Added background job rate limiting for `update_sequence_steps` to prevent API thrashing.
  - Deduplicated cadence updates by account to optimize background processing.
  - Refactored sequence update logic into dedicated helper functions and simplified field provisioning by delegating directly to `update_sequence_steps`.
  - Expanded unit test coverage for the updated sequence logic.
  - Commits: [a595942](https://github.com/aurumorinc/frappe-apollo/commit/a595942a), [b60e048](https://github.com/aurumorinc/frappe-apollo/commit/b60e0486), [fb13734b](https://github.com/aurumorinc/frappe-apollo/commit/fb13734b)

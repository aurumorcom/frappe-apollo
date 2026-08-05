## Features

- **Apollo Error Handling**
  - Added comprehensive error handling for Apollo API requests and fallback support for legacy endpoints.
  - Commits: [29dcc1e](https://github.com/aurumorinc/frappe-apollo/commit/29dcc1ed), [22a00bc](https://github.com/aurumorinc/frappe-apollo/commit/22a00bc2), [df21f53](https://github.com/aurumorinc/frappe-apollo/commit/df21f538)

## Improvements

- **Test Cleanup Refactoring**
  - Cleaned up test documents in teardown methods and removed unused helper methods.
  - Commits: [ad040d9](https://github.com/aurumorinc/frappe-apollo/commit/ad040d95), [b1c3b7f](https://github.com/aurumorinc/frappe-apollo/commit/b1c3b7ff), [863a36c](https://github.com/aurumorinc/frappe-apollo/commit/863a36c)
- **Cadence Doctype Hook**
  - Added an empty `on_trash` hook method to the Cadence doctype.
  - Commit: [6cceaab](https://github.com/aurumorinc/frappe-apollo/commit/6cceaabb)

## Infrastructure

- **Email Queue Schedule**
  - Changed the email queue schedule to run daily and added duplicate prevention logic.
  - Commits: [dc8c619](https://github.com/aurumorinc/frappe-apollo/commit/dc8c619e), [ab43478](https://github.com/aurumorinc/frappe-apollo/commit/ab434786)

## Docs

- **Framework-Bench Rules**
  - Added framework-bench development standards and repository map to `AGENTS.md`.
  - Commit: [c93b77c](https://github.com/aurumorinc/frappe-apollo/commit/c93b77c0)

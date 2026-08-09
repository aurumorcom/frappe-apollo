# Changelog v16.11.0

### Features

* **Integrations Tab & Apollo Fields visibility**: Made `apollo_ids` field visible and organized it under a new "Integrations" tab within the Email Account custom field ([f138aab](https://github.com/aurumorcom/frappe-apollo/commit/f138aab8)).
* **Cadence Apollo ID Doctype update**: Removed the status field from the Cadence Apollo ID doctype ([f138aab](https://github.com/aurumorcom/frappe-apollo/commit/f138aab8)).
* **Apollo Field Doctype configuration**: Added `integrations_tab` to the Apollo Field doctype ([f138aab](https://github.com/aurumorcom/frappe-apollo/commit/f138aab8)).

### Improvements

* **Codebase formatting with Black and Isort**: Applied comprehensive PEP 8 code formatting across the entire test suite, `install.py`, and `hooks.py` ([4e0358c](https://github.com/aurumorcom/frappe-apollo/commit/4e0358c5)).
* **Test suite code formatting**: Formatted test files to maintain consistency with PEP 8 standards ([a489c36](https://github.com/aurumorcom/frappe-apollo/commit/a489c368)).
* **Code readability refactoring**: Refactored various modules across the codebase to improve maintainability and readability ([99e57f6](https://github.com/aurumorcom/frappe-apollo/commit/99e57f6e)).

### Infrastructure

* **Release workflow organization update**: Updated GitHub Actions workflow configuration to target the correct organization name (`aurumorcom`), job name (`tag-release`), and workflow path ([088d074](https://github.com/aurumorcom/frappe-apollo/commit/088d0743)).
* **Bumpversion pyproject migration**: Replaced the legacy `bumpver` configuration with `bumpversion` in `pyproject.toml` ([8d87210](https://github.com/aurumorcom/frappe-apollo/commit/8d872104)).
* **Bumpversion configuration file creation**: Added a dedicated `bumpversion.toml` configuration file ([bf76bbf](https://github.com/aurumorcom/frappe-apollo/commit/bf76bbfe), [66d8d1a](https://github.com/aurumorcom/frappe-apollo/commit/66d8d1a3)).

### Docs

* **Pull request template cleanup**: Removed the redundant "✅ Developer Checklist" section from the pull request template ([f7819a3](https://github.com/aurumorcom/frappe-apollo/commit/f7819a37), [61b29d3](https://github.com/aurumorcom/frappe-apollo/commit/61b29d39)).

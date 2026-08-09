# Changelog v17.0.0

## Breaking Changes

* **Apollo UI and Field Restructuring**
  * Description: Made `apollo_ids` visible under a new "Integrations" tab in Email Account, removed the `status` field from Cadence Apollo ID, and added `integrations_tab` to the Apollo Field.
  * Migration Path: Update any custom scripts or integrations referencing the removed `status` field on Cadence Apollo ID, and adjust UI expectations for the new Integrations tab layout.
  * Commits: [`f138aab`](https://github.com/aurumorcom/frappe-apollo/commit/f138aab8)

* **Cadence Apollo ID Status Field Removal and Email Account View Modification**
  * Description: Removed the status field from Cadence Apollo ID and modified the Email Account view (Severity: medium).
  * Migration Path: Update any custom scripts or integrations referencing the removed status field on Cadence Apollo ID, and adjust UI expectations for the new Integrations tab layout.

## Improvements

* **Code Formatting and Style**
  * Description: Applied consistent code formatting using black and isort across the test suite and codebase.
  * Commits: [`4e0358c`](https://github.com/aurumorcom/frappe-apollo/commit/4e0358c5), [`a489c36`](https://github.com/aurumorcom/frappe-apollo/commit/a489c368), [`99e57f6`](https://github.com/aurumorcom/frappe-apollo/commit/99e57f6e)

## Infrastructure

* **Release Workflow Update**
  * Description: Updated GitHub Actions workflow configuration to use the correct organization name, renamed the release job, and referenced the correct tag-release YAML.
  * Commits: [`088d074`](https://github.com/aurumorcom/frappe-apollo/commit/088d0743)

* **Version Management Migration**
  * Description: Replaced bumpver configuration with bumpversion in `pyproject.toml` and created `bumpversion.toml` for the `frappe_apollo` package.
  * Commits: [`7ba8ca3`](https://github.com/aurumorcom/frappe-apollo/commit/7ba8ca3f)

## Docs

* **PR Template Cleanup**
  * Description: Removed the redundant developer checklist section from the pull request template.
  * Commits: [`f7819a3`](https://github.com/aurumorcom/frappe-apollo/commit/f7819a37), [`61b29d3`](https://github.com/aurumorcom/frappe-apollo/commit/61b29d39)

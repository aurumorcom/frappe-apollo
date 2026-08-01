# Changelog v16.1.0

## Breaking Changes
- **Refactor Cadence Provisioning**: Consolidate and extract cadence provider logic, rename/remove deprecated classes, and update API calls. Commits: [04c2cd4](https://github.com/aurumorinc/frappe-apollo/commit/04c2cd49), [6f2f6e2](https://github.com/aurumorinc/frappe-apollo/commit/6f2f6e29), [56bc10a](https://github.com/aurumorinc/frappe-apollo/commit/56bc10a6)
- **Rename Account and Field DocTypes**: Standardize doctype naming with Apollo prefix and update references. Commits: [1ac7ba5](https://github.com/aurumorinc/frappe-apollo/commit/1ac7ba52), [c13e039](https://github.com/aurumorinc/frappe-apollo/commit/c13e0396), [4f6114c](https://github.com/aurumorinc/frappe-apollo/commit/4f6114c5)
- **Migrate People to CRM Lead**: Replace People doctype with CRM Lead Apollo ID child table and streamline sync modules. Commits: [23a92a2](https://github.com/aurumorinc/frappe-apollo/commit/23a92a27), [d303e1b](https://github.com/aurumorinc/frappe-apollo/commit/d303e1b3), [211af0c](https://github.com/aurumorinc/frappe-apollo/commit/211af0c9)
- **Renamed Account and Field DocTypes to Apollo Account and Apollo Field**: Update any custom scripts or API integrations referencing the old DocType names to use the new Apollo prefixes. Severity: high.
- **Migrated People to CRM Lead Apollo ID and Restructured Modules**: Review customized sync modules and update references from the deprecated People doctype to CRM Lead Apollo ID child tables. Severity: high.
- **Refactored Cadence Provisioning and Renamed ApolloCadenceProvider**: Update custom integrations calling deprecated cadence provider methods to use the consolidated provider structure. Severity: high.

## Features
- **Cadence Enhancements**: Improve load balancing, add status validations, and restructure provisioning per account. Commits: [2246e80](https://github.com/aurumorinc/frappe-apollo/commit/2246e80f), [35d0233](https://github.com/aurumorinc/frappe-apollo/commit/35d0233b), [e762188](https://github.com/aurumorinc/frappe-apollo/commit/e762188c)
- **OAuth Token Management**: Add support for tracking token expiration, proactive token refresh, and UI authorization controls. Commits: [8421da5](https://github.com/aurumorinc/frappe-apollo/commit/8421da52), [a1ee39e](https://github.com/aurumorinc/frappe-apollo/commit/a1ee39ed), [b270949](https://github.com/aurumorinc/frappe-apollo/commit/b270949f)
- **Cadence Sequences**: Implement comprehensive sequence lifecycle methods, background jobs, and event waiting for apollo_ids. Commits: [33e55b6](https://github.com/aurumorinc/frappe-apollo/commit/33e55b6c), [4f2dc0d](https://github.com/aurumorinc/frappe-apollo/commit/4f2dc0d1), [1446cf8](https://github.com/aurumorinc/frappe-apollo/commit/1446cf8b)
- **Email Integration**: Integrate Apollo email service option, email account synchronization, and communication sync. Commits: [836c3df](https://github.com/aurumorinc/frappe-apollo/commit/836c3df5), [5c81104](https://github.com/aurumorinc/frappe-apollo/commit/5c81104c), [6bc3ef4](https://github.com/aurumorinc/frappe-apollo/commit/6bc3ef40)

## Improvements
- **Codebase Refactoring**: Simplify settings checks, use built-in frappe.enqueue, and standardize campaign terminology to cadence. Commits: [d566344](https://github.com/aurumorinc/frappe-apollo/commit/d5663446), [81f802c](https://github.com/aurumorinc/frappe-apollo/commit/81f802cd), [fca67bc](https://github.com/aurumorinc/frappe-apollo/commit/fca67bc4)
- **Workspace Navigation**: Simplify DocType labels and organize sidebar navigation. Commits: [190921c](https://github.com/aurumorinc/frappe-apollo/commit/190921c5), [2fddf7a](https://github.com/aurumorinc/frappe-apollo/commit/2fddf7a2), [35cbce2](https://github.com/aurumorinc/frappe-apollo/commit/35cbce2f)

## Fixes
- **Secure Password Retrieval**: Replace direct attribute access with get_password method and validate credentials before enqueuing jobs. Commits: [0a33f30](https://github.com/aurumorinc/frappe-apollo/commit/0a33f30a), [1f8919f](https://github.com/aurumorinc/frappe-apollo/commit/1f8919fa), [5b23d05](https://github.com/aurumorinc/frappe-apollo/commit/5b23d05a)
- **Integrations Tab Layout**: Update layout ordering for the Integrations tab break. Commits: [4ba6174](https://github.com/aurumorinc/frappe-apollo/commit/4ba61744), [42138fb](https://github.com/aurumorinc/frappe-apollo/commit/42138fbf), [5f57783](https://github.com/aurumorinc/frappe-apollo/commit/5f577830)

## Infrastructure
- **Project Configuration**: Configure bumpver tool, GitHub Actions release workflow, and rename project references to frappe_apollo. Commits: [e90b4d1](https://github.com/aurumorinc/frappe-apollo/commit/e90b4d14), [808506a](https://github.com/aurumorinc/frappe-apollo/commit/808506a0), [e237f5e](https://github.com/aurumorinc/frappe-apollo/commit/e237f5e6)
- **Core Initialization**: Initialize project structure, add API client, OAuth flow, webhooks, and core DocTypes. Commits: [a1f5ce4](https://github.com/aurumorinc/frappe-apollo/commit/a1f5ce47), [2e98286](https://github.com/aurumorinc/frappe-apollo/commit/2e982864), [752f92e](https://github.com/aurumorinc/frappe-apollo/commit/752f92e2)

## Docs
- **Versioning Documentation**: Update versioning pattern to `16.MINOR.PATCH` and add versioning analysis rules. Commits: [d9cb1c7](https://github.com/aurumorinc/frappe-apollo/commit/d9cb1c7b), [ab733d0](https://github.com/aurumorinc/frappe-apollo/commit/ab733d03), [cb154a7](https://github.com/aurumorinc/frappe-apollo/commit/cb154a72)
- **Architecture Decisions**: Document conversion of API key to Password type and workspace sidebar navigation in ADR 0003. Commits: [0578414](https://github.com/aurumorinc/frappe-apollo/commit/0578414d), [0855607](https://github.com/aurumorinc/frappe-apollo/commit/08556074), [23a488e](https://github.com/aurumorinc/frappe-apollo/commit/23a488e7)

## Other
- **Test Suite Isolation**: Improve test suite isolation using transaction rollbacks and helper updates. Commits: [5f57783](https://github.com/aurumorinc/frappe-apollo/commit/5f577830), [01c3213](https://github.com/aurumorinc/frappe-apollo/commit/01c32137), [ca01f68](https://github.com/aurumorinc/frappe-apollo/commit/ca01f685)

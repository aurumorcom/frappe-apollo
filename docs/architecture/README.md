# Architecture Documentation: Frappe Apollo Integration (`frappe_apollo`)

Welcome to the architectural documentation for the **`frappe_apollo`** application ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1)).

## Navigation Index

### 1. C4 Modeling (`c4/`)
- [**C1 System Context Model**](c4/01-context.md): High-level system context and external boundary erDiagram.
- [**C2 Container Model**](c4/02-container.md): Execution containers, WSGI app, database, Redis workers, and Apollo API.
- [**C3 Component Model**](c4/03-component.md): Complete entity relationship diagram and component specifications.

### 2. Behavioral Workflows
- [**BPMN Business Workflows**](bpmn.md): Single unified file containing the full behavioral and event-driven workflow graph for the entire project.

### 3. arc42 System Documentation (`arc42/`)
- [**01 Introduction and Goals**](arc42/01_introduction_and_goals.md)
- [**02 Architecture Constraints**](arc42/02_architecture_constraints.md)
- [**03 Context and Scope**](arc42/03_context_and_scope.md)
- [**04 Solution Strategy**](arc42/04_solution_strategy.md)
- [**05 Building Block View**](arc42/05_building_block_view.md)
- [**06 Runtime View**](arc42/06_runtime_view.md)
- [**07 Deployment View**](arc42/07_deployment_view.md)
- [**08 Cross-Cutting Concepts**](arc42/08_cross_cutting_concepts.md)
- [**09 Architecture Decisions (ADRs)**](arc42/09_architecture_decisions/0001-record-architecture-decisions.md)
  - [0001 Baseline Architectural Decisions](arc42/09_architecture_decisions/0001-record-architecture-decisions.md)
  - [0002 Rename Account, Field, and Field Apollo ID DocTypes](arc42/09_architecture_decisions/0002-rename-account-and-field-doctypes.md)
  - [0003 Convert API Key to Password Type, Disable Strength Checks, and Add Workspace Sidebar](arc42/09_architecture_decisions/0003-convert-api-key-to-password-and-disable-strength-checks.md)
  - [0004 Cadence Provider Setup via App Lifecycle Hooks](arc42/09_architecture_decisions/0004-cadence-provider-lifecycle-hooks.md)
  - [0005 Single Sequence Engine per Account](arc42/09_architecture_decisions/0005-single-sequence-engine-per-account.md)
- [**10 Quality Requirements**](arc42/10_quality_requirements.md)
- [**11 Risks and Technical Debt**](arc42/11_risks_and_technical_debt.md)
- [**12 Glossary**](arc42/12_glossary.md)

# Architecture Documentation: Frappe Apollo Integration (`frappe_apollo`)

Welcome to the architectural documentation for the **`frappe_apollo`** application ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1)).

## Navigation Index

### 1. C4 Modeling (`c4/`)
- [**C1 System Context Model**](c4/01-context.md): High-level system context and external boundary erDiagram.
- [**C2 Container Model**](c4/02-container.md): Execution containers, WSGI app, database, Redis workers, and Apollo API.
- [**C3 Component Model**](c4/03-component.md): Complete entity relationship diagram and component specifications.

### 2. Behavioral Workflows (`bpmn/`)
- [**01 OAuth Authorization Flow**](bpmn/01-oauth-authentication.md): OAuth dialog and token exchange.
- [**02 Email Account / Mailbox Sync Workflow**](bpmn/02-mailbox-sync.md): Daily cron mailbox synchronization.
- [**03 Cadence & Custom Field Provisioning**](bpmn/03-cadence-provisioning.md): Sequence creation & step field provisioning.
- [**04 Lead Contact Sync & Sequence Assignment**](bpmn/04-contact-sequence-assignment.md): Lead contact creation & sequence enrollment.
- [**05 Communication Schedule Synchronization**](bpmn/05-communication-sync.md): Communication custom field schedule mapping.
- [**06 Webhook Engagement Processing**](bpmn/06-webhook-processing.md): Incoming webhook engagement processing.

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
- [**10 Quality Requirements**](arc42/10_quality_requirements.md)
- [**11 Risks and Technical Debt**](arc42/11_risks_and_technical_debt.md)
- [**12 Glossary**](arc42/12_glossary.md)

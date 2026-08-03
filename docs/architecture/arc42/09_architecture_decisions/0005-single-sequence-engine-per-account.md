# ADR 0005: Single Sequence Engine per Apollo Account

## Status
Accepted

## Date
2026-08-03

## Context
Apollo enforces a strict limit of 2 active sequences for free accounts. Previously, the architecture provisioned a new Apollo sequence for every Frappe `Cadence`, which rapidly exhausted limits on free accounts and complicated sequence management on paid accounts. Furthermore, performing A/B testing and advanced cadence branching within Apollo duplicates logic that is better orchestrated natively within Frappe CRM.

## Decision
1. **Single Sequence Architecture**: Each `Apollo Account` will utilize exactly ONE generic Apollo sequence, acting purely as a "cold mail dispatch engine."
2. **Dynamic Step Validation**: The single sequence's step count is dynamically queried from the Apollo API payload. Frappe ensures the local cadence step requirement does not exceed this dynamic capacity.
3. **Frappe-Driven Logic**: All A/B testing, cadence branching, and content generation will execute exclusively within Frappe. Frappe will map multiple distinct `Cadence` records to this single Apollo sequence.
4. **Dynamic Contact Fields**: Instead of sequence-level templates, the sequence uses clean, generic custom variables without random MD5 hashes (e.g., `{{custom_field_subject_1}}`, `{{custom_field_message_1}}`). Frappe populates these fields per contact right before assigning them.
5. **Schema Simplification**: The `Cadence Apollo ID` child table is retained to assign which `Apollo Account` is used for a given cadence and sender, but it no longer stores an Apollo Sequence ID. The `Apollo Account` DocType will directly store its master `apollo_sequence_id`.

## Consequences
### Positive
- Completely bypasses the 2-sequence limitation on free Apollo accounts.
- Infinite Frappe `Cadence` scalability, limited only by API usage and mailbox volumes.
- Centralizes all A/B testing and outreach analytics within Frappe CRM.
- Greatly simplifies the sequence and field provisioning workflow with readable labels.

### Negative & Risks
- Required number of steps in Frappe Cadences must not exceed the pre-configured steps on the Apollo Sequence.
- Increased reliance on robust Contact custom field synchronization prior to sequence assignment.
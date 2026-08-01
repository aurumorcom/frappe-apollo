# 5. Communication Schedule Synchronization

This document details the behavioral workflow for synchronizing communication field schedules to Apollo custom fields in [`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1).

## Trigger
Communication status updated to `'Scheduled'` (`Communication on_update`).

## Workflow Flowchart

```mermaid
flowchart TD
    CommScheduled(["Communication Status -> 'Scheduled'"]) --> OnUpdateComm["Communication on_update Hook"]
    OnUpdateComm --> EnqueueCommSync["Enqueue update_a_contact()"]
    EnqueueCommSync --> CheckCommMCC{"MCC Account & Sequence ID Available?"}
    CheckCommMCC -- No --> WaitCommMCC["wait_for_event('Multi Channel Cadence on_update')"]
    WaitCommMCC -. Event Trigger .-> CheckCommMCC
    CheckCommMCC -- Yes --> CheckCommProviderEnabled{"Provider Enabled?"}
    CheckCommProviderEnabled -- No --> WaitCommProvider["wait_for_event('Cadence Provider on_update')"]
    WaitCommProvider -. Event Trigger .-> CheckCommProviderEnabled
    CheckCommProviderEnabled -- Yes --> CheckCommAccountAuth{"Account Authorized?"}
    CheckCommAccountAuth -- No --> WaitCommAuth["wait_for_event('Apollo Account on_update')"]
    WaitCommAuth -. Event Trigger .-> CheckCommAccountAuth
    CheckCommAccountAuth -- Yes --> CheckCommLeadID{"CRM Lead Apollo ID Available?"}
    CheckCommLeadID -- No --> WaitCommLead["wait_for_event('CRM Lead on_update')"]
    WaitCommLead -. Event Trigger .-> CheckCommLeadID
    CheckCommLeadID -- Yes --> CheckStepFields{"Cadence Step Subject & Message Fields Set?"}
    CheckStepFields -- No --> WaitStepFields["wait_for_event('Cadence on_update')"]
    WaitStepFields -. Event Trigger .-> CheckStepFields
    CheckStepFields -- Yes --> CheckSubjectFieldID{"Subject Field Apollo ID Mapped?"}
    CheckSubjectFieldID -- No --> WaitSubjectField["wait_for_event('Apollo Field on_update')"]
    WaitSubjectField -. Event Trigger .-> CheckSubjectFieldID
    CheckSubjectFieldID -- Yes --> CheckMessageFieldID{"Message Field Apollo ID Mapped?"}
    CheckMessageFieldID -- No --> WaitMessageField["wait_for_event('Apollo Field on_update')"]
    WaitMessageField -. Event Trigger .-> CheckMessageFieldID
    CheckMessageFieldID -- Yes --> PatchContactAPI["ApolloClient update_contact(custom_fields)"]
    PatchContactAPI --> MarkSynced["Set Communication apollo_sync_status = 'Synced'"]
    MarkSynced --> EndCommSync(["Communication Custom Fields Synced"])
```

## Component References

- **Communication**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py:4)
- **Multi Channel Cadence**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py:5)
- **Cadence**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence/cadence.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence/cadence.py:5)
- **Apollo Field**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:5)
- **Apollo Field Apollo ID**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.py:1)
- **CRM Lead Apollo ID**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/crm_lead_apollo_id/crm_lead_apollo_id.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/crm_lead_apollo_id/crm_lead_apollo_id.py:1)
- **Apollo Account**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py:5)
- **ApolloClient**: [`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:9)

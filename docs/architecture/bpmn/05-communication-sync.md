# 5. Communication Schedule Synchronization

This document details the behavioral workflow for synchronizing communication field schedules to Apollo custom fields in [`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1).

## Trigger
Communication status updated to `'Scheduled'` (`Communication on_update`).

## Workflow Flowchart

```mermaid
flowchart TD
    CommScheduled(["Communication Status -> 'Scheduled'"]) --> OnUpdateComm["Communication on_update Hook"]
    OnUpdateComm --> EnqueueCommSync["Enqueue update_a_contact()"]
    EnqueueCommSync --> CheckCommMCC{"MCC Account Available?"}
    CheckCommMCC -- No --> WaitCommMCC["wait_for_event('Multi Channel Cadence on_update')"]
    WaitCommMCC -. Event Trigger .-> CheckCommMCC
    CheckCommMCC -- Yes --> CheckCommProviderEnabled{"Provider Enabled?"}
    CheckCommProviderEnabled -- No --> WaitCommProvider["wait_for_event('Cadence Provider on_update')"]
    WaitCommProvider -. Event Trigger .-> CheckCommProviderEnabled
    CheckCommProviderEnabled -- Yes --> CheckCommAccountAuth{"Account Authorized & Sequence ID Set?"}
    CheckCommAccountAuth -- No --> WaitCommAuth["wait_for_event('Apollo Account on_update')"]
    WaitCommAuth -. Event Trigger .-> CheckCommAccountAuth
    CheckCommAccountAuth -- Yes --> CheckCommLeadID{"CRM Lead Apollo ID Available?"}
    CheckCommLeadID -- No --> WaitCommLead["wait_for_event('CRM Lead on_update')"]
    WaitCommLead -. Event Trigger .-> CheckCommLeadID
    CheckCommLeadID -- Yes --> CheckSubjectFieldID{"Generic Subject Field Mapped?"}
    CheckSubjectFieldID -- No --> WaitSubjectField["wait_for_event('Apollo Field on_update')"]
    WaitSubjectField -. Event Trigger .-> CheckSubjectFieldID
    CheckSubjectFieldID -- Yes --> CheckMessageFieldID{"Generic Message Field Mapped?"}
    CheckMessageFieldID -- No --> WaitMessageField["wait_for_event('Apollo Field on_update')"]
    WaitMessageField -. Event Trigger .-> CheckMessageFieldID
    CheckMessageFieldID -- Yes --> PatchContactAPI["ApolloClient update_contact(custom_fields)"]
    PatchContactAPI --> MarkSynced["Set Communication apollo_status = 'Scheduled'"]
    MarkSynced --> EndCommSync(["Communication Custom Fields Synced"])
```

## Component References

- **Communication**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py:4)
- **Multi Channel Cadence**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py:5)
- **Apollo Field**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:5)
- **Apollo Field Apollo ID**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.py:1)
- **CRM Lead Apollo ID**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/crm_lead_apollo_id/crm_lead_apollo_id.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/crm_lead_apollo_id/crm_lead_apollo_id.py:1)
- **Apollo Account**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py:5)
- **ApolloClient**: [`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:9)

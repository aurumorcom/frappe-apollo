# 4. Lead Contact Sync & Sequence Assignment

This document details the behavioral workflow for creating lead contacts in Apollo and assigning them to sequences in [`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1).

## Trigger
Multi Channel Cadence status updated to `'Scheduled'` (`Multi Channel Cadence on_update`).

## Workflow Flowchart

```mermaid
flowchart TD
    MCCScheduled(["Multi Channel Cadence Status -> 'Scheduled'"]) --> OnUpdateMCC["Multi Channel Cadence on_update Hook"]
    OnUpdateMCC --> LoadBalanceAccount["before_save Load Balance Sender Accounts"]
    LoadBalanceAccount --> EnqueueAddContact["Enqueue add_a_contact_to_sequence()"]
    
    %% Contact Creation Subflow (_create_a_contact)
    EnqueueAddContact --> CreateContactTask["CRM Lead _create_a_contact()"]
    CreateContactTask --> CheckCommsCreated{"Communications Generated? (actual >= expected)"}
    CheckCommsCreated -- No --> WaitComms["wait_for_event('Communication after_insert')"]
    WaitComms -. Event Trigger .-> CheckCommsCreated
    CheckCommsCreated -- Yes --> CheckUserEmail{"User Email Mapped for Sender?"}
    
    CheckUserEmail -- No --> WaitUserEmail["wait_for_event('User Email after_insert')"]
    WaitUserEmail -. Event Trigger .-> CheckUserEmail
    CheckUserEmail -- Yes --> CheckProviderAndAccount{"Provider Enabled & Account Authorized?"}
    
    CheckProviderAndAccount -- No --> WaitLeadAccount["wait_for_event('Apollo Account on_update')"]
    WaitLeadAccount -. Event Trigger .-> CheckProviderAndAccount
    CheckProviderAndAccount -- Yes --> CheckLeadApolloID{"CRM Lead Apollo ID Exists?"}
    
    CheckLeadApolloID -- No --> EnqueueCreateContact["Enqueue create_a_contact()"]
    EnqueueCreateContact --> WaitLeadContact["wait_for_event('CRM Lead on_update')"]
    EnqueueCreateContact --> CallCreateContactAPI["ApolloClient create_contact()"]
    CallCreateContactAPI --> SaveLeadApolloID["Store in CRM Lead Apollo ID"]
    SaveLeadApolloID --> EmitLeadUpdate["Emit CRM Lead on_update Event"]
    EmitLeadUpdate -. Event Trigger .-> WaitLeadContact
    WaitLeadContact --> CheckLeadApolloID
    
    CheckLeadApolloID -- Yes --> EnqueueUpdateContact["Enqueue update_a_contact()"]
    EnqueueUpdateContact --> CallUpdateContactAPI["ApolloClient update_contact()"]
    CallUpdateContactAPI --> ContactCreatedReady(["Lead Contact Ready in Apollo"])
    
    %% Sequence Assignment Subflow (add_contact_to_sequence)
    EnqueueAddContact --> AssignSequence["Multi Channel Cadence add_contact_to_sequence()"]
    AssignSequence --> CheckMCCSeqAccount{"MCC Account Authorized & Sequence ID Set?"}
    CheckMCCSeqAccount -- No --> WaitMCCSeq["wait_for_event('Apollo Account on_update')"]
    WaitMCCSeq -. Event Trigger .-> CheckMCCSeqAccount
    CheckMCCSeqAccount -- Yes --> CheckMCCUserEmail{"User Email Mapped for Sender?"}
    CheckMCCUserEmail -- No --> WaitMCCEmail["wait_for_event('User Email after_insert')"]
    WaitMCCEmail -. Event Trigger .-> CheckMCCUserEmail
    CheckMCCUserEmail -- Yes --> CheckMCCLeadContact{"CRM Lead Apollo ID Available?"}
    CheckMCCLeadContact -- No --> WaitMCCLead["wait_for_event('CRM Lead on_update')"]
    WaitMCCLead -. Event Trigger .-> CheckMCCLeadContact
    CheckMCCLeadContact -- Yes --> AddToSeqAPI["ApolloClient add_contacts_to_sequence()"]
    AddToSeqAPI --> EndContactAssign(["Lead Assigned to Apollo Sequence"])
```

## Component References

- **Multi Channel Cadence**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/multi_channel_cadence/multi_channel_cadence.py:5)
- **CRM Lead**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/crm_lead/crm_lead.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/crm_lead/crm_lead.py:3)
- **CRM Lead Apollo ID**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/crm_lead_apollo_id/crm_lead_apollo_id.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/crm_lead_apollo_id/crm_lead_apollo_id.py:1)
- **Communication**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py:4)
- **Apollo Account**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py:5)
- **ApolloClient**: [`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:9)

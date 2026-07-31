# 3. Cadence & Custom Field Provisioning

This document details the behavioral workflow for provisioning sequences and custom fields in Apollo API in [`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1).

## Trigger
User saves or updates a Cadence document (`Cadence on_update`).

## Workflow Flowchart

```mermaid
flowchart TD
    CadenceSaved(["User Saves/Updates Cadence"]) --> OnUpdateCadence["Cadence on_update Hook"]
    OnUpdateCadence --> EnqueueSeqProv["Enqueue _provision_sequence()"]
    OnUpdateCadence --> EnqueueFieldProv["Enqueue provision_a_field()"]
    
    %% Sequence Provisioning Loop
    EnqueueSeqProv --> CheckAccountAuth{"Provider Enabled & Account Authorized?"}
    CheckAccountAuth -- No --> WaitAccountAuth["wait_for_event('Apollo Account on_update')"]
    WaitAccountAuth -. Event Trigger .-> CheckAccountAuth
    CheckAccountAuth -- Yes --> CheckSeqExists{"Sequence Apollo ID Exists?"}
    CheckSeqExists -- Yes --> UpdateSeq["ApolloClient update_sequence()"]
    CheckSeqExists -- No --> CreateSeq["ApolloClient create_sequence()"]
    CreateSeq --> SaveSeqID["Save ID in Cadence Apollo ID"]
    SaveSeqID --> EmitCadenceUpdate["Emit Cadence on_update Event"]
    UpdateSeq --> EndCadenceProv(["Cadence Provisioned"])
    EmitCadenceUpdate --> EndCadenceProv
    
    %% Field Provisioning Loop
    EnqueueFieldProv --> CheckSeqIDReady{"Sequence Apollo ID Available?"}
    CheckSeqIDReady -- No --> WaitCadenceSeq["wait_for_event('Cadence on_update')"]
    WaitCadenceSeq -. Event Trigger .-> CheckSeqIDReady
    CheckSeqIDReady -- Yes --> GetOrCreateField["Get/Create Apollo Field Doc & Attach to Cadence Step"]
    GetOrCreateField --> CheckFieldMap{"Apollo Field Apollo ID Mapped for Account?"}
    CheckFieldMap -- Yes --> EndFieldProv(["Fields Provisioned"])
    CheckFieldMap -- No --> CreateCustomField["ApolloClient create_custom_field()"]
    CreateCustomField --> SaveFieldMap["Save ID in Apollo Field Apollo ID"]
    SaveFieldMap --> EmitFieldUpdate["Emit Apollo Field on_update Event"]
    EmitFieldUpdate --> EndFieldProv
```

## Component References

- **Cadence**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence/cadence.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence/cadence.py:5)
- **Cadence Apollo ID**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence_apollo_id/cadence_apollo_id.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence_apollo_id/cadence_apollo_id.py:1)
- **Apollo Field**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:5)
- **Apollo Field Apollo ID**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.py:1)
- **Apollo Account**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py:5)
- **ApolloClient**: [`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:9)

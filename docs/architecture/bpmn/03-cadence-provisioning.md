# 3. Apollo Account Sequence & Field Provisioning

This document details the behavioral workflow for provisioning the single cold-mail engine sequence and generic custom fields when an Apollo Account is authorized and Cadences are updated.

## Trigger
- Sequence Provisioning: Apollo Account is authorized (`Apollo Account on_update` where `status == Authorized`).
- Field Provisioning: A Frappe Cadence is created or updated (`Cadence on_update`).

## Workflow Flowchart

```mermaid
flowchart TD
    %% Engine Sequence Provisioning Loop
    AccountAuth(["Apollo Account status = Authorized"]) --> OnUpdateAccount["Apollo Account on_update Hook"]
    OnUpdateAccount --> EnqueueSeqProv["Enqueue provision_sequence() Job"]
    
    EnqueueSeqProv --> CheckSeqExists{"apollo_sequence_id exists locally?"}
    CheckSeqExists -- Yes --> EndSeqProv(["Sequence Provisioned"])
    CheckSeqExists -- No --> SearchSeq["ApolloClient search_sequences('Cadence from Frappe')"]
    SearchSeq --> CheckSearch{"Found sequence?"}
    CheckSearch -- Yes --> SaveSeqID["Save sequence_id to Apollo Account"]
    CheckSearch -- No --> CreateSeq["ApolloClient create_sequence(name='Cadence from Frappe', steps=[])"]
    CreateSeq --> SaveSeqID
    SaveSeqID --> EmitAccountUpdate["Emit Apollo Account on_update Event"]
    EmitAccountUpdate --> EndSeqProv
    
    %% Generic Field Provisioning Loop
    CadenceUpdate(["Cadence on_update"]) --> EnqueueFields["Enqueue provision_a_field() for required steps (e.g., subject_1)"]
    
    EnqueueFields --> CheckProvider{"Cadence Provider Enabled?"}
    CheckProvider -- No --> WaitProvider[/wait_for_event 'Cadence Provider'/]
    WaitProvider --> CheckProvider
    CheckProvider -- Yes --> CheckAccount{"Apollo Account Authorized?"}
    
    CheckAccount -- No --> WaitAccount[/wait_for_event 'Apollo Account'/]
    WaitAccount --> CheckAccount
    CheckAccount -- Yes --> CreateLocalField["Get/Create Local Apollo Field Doc"]
    
    CreateLocalField --> CheckFieldMap{"Mapped for Account?"}
    CheckFieldMap -- No --> CreateCustomField["ApolloClient create_custom_field()"]
    CreateCustomField --> SaveFieldMap["Save ID in Apollo Field apollo_ids"]
    SaveFieldMap --> CheckLocalSeqID
    CheckFieldMap -- Yes --> CheckLocalSeqID{"Apollo Account has apollo_sequence_id?"}
    
    CheckLocalSeqID -- No --> WaitSeqID[/wait_for_event 'apollo_sequence_id'/]
    WaitSeqID --> CheckLocalSeqID
    CheckLocalSeqID -- Yes --> CheckStepCapacity["_update_sequence() - Check if sequence steps < field_index"]
    
    CheckStepCapacity -- Yes --> AppendSteps["ApolloClient update_sequence(append new steps with custom_field variables)"]
    AppendSteps --> EndFieldProv(["Field & Step Provisioned"])
    CheckStepCapacity -- No --> EndFieldProv
```

## Component References

- **Apollo Field**: [`frappe_apollo/apollo/doctype/apollo_field/apollo_field.py`](../../../frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:5)
- **Apollo Account**: [`frappe_apollo/apollo/doctype/apollo_account/apollo_account.py`](../../../frappe_apollo/apollo/doctype/apollo_account/apollo_account.py:5)
- **Cadence**: [`frappe_apollo/apollo/doctype/cadence/cadence.py`](../../../frappe_apollo/apollo/doctype/cadence/cadence.py:5)
- **ApolloClient**: [`frappe_apollo/integrations/apollo.py`](../../../frappe_apollo/integrations/apollo.py:11)

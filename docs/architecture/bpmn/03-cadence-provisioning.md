# 3. Apollo Account Sequence & Field Provisioning

This document details the behavioral workflow for provisioning the single cold-mail engine sequence and generic custom fields when an Apollo Account is authorized in [`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1).

## Trigger
Apollo Account is authorized via OAuth or API Key (`Apollo Account on_update` where `status == Authorized`).

## Workflow Flowchart

```mermaid
flowchart TD
    AccountAuth(["Apollo Account status = Authorized"]) --> OnUpdateAccount["Apollo Account on_update Hook"]
    OnUpdateAccount --> EnqueueSeqProv["Enqueue _provision_engine_sequence()"]
    
    %% Engine Sequence Provisioning Loop
    EnqueueSeqProv --> CheckSeqExists{"apollo_sequence_id Exists?"}
    CheckSeqExists -- Yes --> UpdateSeq["ApolloClient update_sequence()"]
    CheckSeqExists -- No --> CreateSeq["ApolloClient create_sequence(4 Steps)"]
    CreateSeq --> SaveSeqID["Save ID in Apollo Account & doc.save()"]
    SaveSeqID --> EmitAccountUpdate["Emit Apollo Account on_update Event"]
    UpdateSeq --> EnqueueFieldProv["Enqueue _provision_generic_fields()"]
    EmitAccountUpdate --> EnqueueFieldProv
    
    %% Generic Field Provisioning Loop (e.g., subject_step_1, body_step_1)
    EnqueueFieldProv --> LoopFields["For each of the 4 steps (Subject/Body)"]
    LoopFields --> GetOrCreateField["Get/Create Generic Apollo Field Doc"]
    GetOrCreateField --> CheckFieldMap{"Mapped for Account?"}
    CheckFieldMap -- Yes --> EndFieldProv(["Fields Provisioned"])
    CheckFieldMap -- No --> CreateCustomField["ApolloClient create_custom_field()"]
    CreateCustomField --> SaveFieldMap["Save ID in Apollo Field Apollo ID"]
    SaveFieldMap --> EmitFieldUpdate["Emit Apollo Field on_update Event"]
    EmitFieldUpdate --> EndFieldProv
```

## Component References

- **Apollo Field**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field/apollo_field.py:5)
- **Apollo Field Apollo ID**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_field_apollo_id/apollo_field_apollo_id.py:1)
- **Apollo Account**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py:5)
- **ApolloClient**: [`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:9)

# 06 Runtime View

The Runtime View describes the behavioral interactions and event-driven workflows across `frappe_apollo` ([`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1)).

## Behavioral Workflows

The system's behavioral logic is structured into dedicated 1-trigger-1-file BPMN workflow models located in [`bpmn/`](../bpmn/):

1. [**OAuth Authorization Flow**](../bpmn/01-oauth-authentication.md)
2. [**Email Account / Mailbox Sync Workflow**](../bpmn/02-mailbox-sync.md)
3. [**Cadence & Custom Field Provisioning**](../bpmn/03-cadence-provisioning.md)
4. [**Lead Contact Sync & Sequence Assignment**](../bpmn/04-contact-sequence-assignment.md)
5. [**Communication Schedule Synchronization**](../bpmn/05-communication-sync.md)
6. [**Webhook Engagement Processing**](../bpmn/06-webhook-processing.md)

## Master Behavioral Graph

```mermaid
flowchart TD
    %% Workflow 1: OAuth Authentication
    subgraph OAuth_Authentication ["1. OAuth Authorization Flow"]
        StartOAuth(["User Initiates OAuth Authorization"]) --> AccountAuthUrl["Apollo Account get_authorization_url()"]
        AccountAuthUrl --> ApolloAuthRedirect["Redirect User to Apollo OAuth Dialog"]
        ApolloAuthRedirect --> ApolloCallback["Apollo API Posts Code to oauth_callback"]
        ApolloCallback --> TokenExchange["ApolloClient Exchanges Code for Access/Refresh Tokens"]
        TokenExchange --> SaveAccountToken["Save Tokens to Apollo Account (status = 'Authorized')"]
        SaveAccountToken --> EndOAuth(["OAuth Authorized"])
    end

    %% Workflow 2: Mailbox Sync
    subgraph Mailbox_Sync ["2. Email Account / Mailbox Sync Workflow"]
        CronTrigger(["Daily Cron Scheduler Event"]) --> QueueEmailAccounts["Email Account queue_get_email_accounts()"]
        QueueEmailAccounts --> FetchMailboxes["ApolloClient get_email_accounts()"]
        FetchMailboxes --> LoopMailboxes{"Mailbox Active?"}
        LoopMailboxes -- Yes --> UpsertEmailAccount["Upsert Email Account with Email Account Apollo ID"]
        LoopMailboxes -- No --> SkipMailbox["Skip Inactive Mailbox"]
        UpsertEmailAccount --> EndMailboxSync(["Mailboxes Synced"])
        SkipMailbox --> EndMailboxSync
    end

    %% Workflow 3: Cadence & Field Provisioning
    subgraph Cadence_Provisioning ["3. Cadence & Custom Field Provisioning"]
        CadenceSaved(["User Saves/Updates Cadence"]) --> OnUpdateCadence["Cadence on_update Hook"]
        OnUpdateCadence --> CheckProviderAuth{"Apollo Enabled & Account Authorized?"}
        CheckProviderAuth -- No --> WaitAccountAuth["wait_for_event('Apollo Account on_update')"]
        WaitAccountAuth --> OnUpdateCadence
        CheckProviderAuth -- Yes --> ProvisionSeq["ApolloClient create_sequence() / update_sequence()"]
        ProvisionSeq --> SaveSeqID["Save Sequence ID in Cadence Apollo ID"]
        SaveSeqID --> ProvisionFields["enqueue_provision_cadence_fields()"]
        ProvisionFields --> CreateFieldAPI["ApolloClient create_custom_field()"]
        CreateFieldAPI --> SaveFieldMapping["Save ID in Apollo Field Apollo ID & Link to Step"]
        SaveFieldMapping --> EndCadenceProv(["Sequence & Fields Provisioned"])
    end

    %% Workflow 4: Contact & Sequence Assignment
    subgraph Contact_Sequence_Assignment ["4. Lead Contact Sync & Sequence Assignment"]
        MCCScheduled(["Multi Channel Cadence Status -> 'Scheduled'"]) --> OnUpdateMCC["Multi Channel Cadence on_update Hook"]
        OnUpdateMCC --> LoadBalanceAccount["before_save Load Balance Sender Accounts"]
        LoadBalanceAccount --> CreateContactTask["CRM Lead _create_a_contact()"]
        CreateContactTask --> CheckLeadApolloID{"CRM Lead Apollo ID Exists?"}
        CheckLeadApolloID -- No --> CreateApolloContact["ApolloClient create_contact()"]
        CreateApolloContact --> SaveLeadApolloID["Store in CRM Lead Apollo ID"]
        CheckLeadApolloID -- Yes --> AssignSequence["_assign_contact_to_sequence()"]
        SaveLeadApolloID --> AssignSequence
        AssignSequence --> AddToSeqAPI["ApolloClient add_contacts_to_sequence()"]
        AddToSeqAPI --> EndContactAssign(["Lead Assigned to Apollo Sequence"])
    end

    %% Workflow 5: Communication Synchronization
    subgraph Communication_Sync ["5. Communication Schedule Synchronization"]
        CommScheduled(["Communication Status -> 'Scheduled'"]) --> OnUpdateComm["Communication on_update Hook"]
        OnUpdateComm --> UpdateContactCustomFields["Communication update_a_contact()"]
        UpdateContactCustomFields --> MapCustomFieldIDs["Map Subject & Message Fields via Apollo Field Apollo ID"]
        MapCustomFieldIDs --> PatchContactAPI["ApolloClient update_contact()"]
        PatchContactAPI --> MarkSynced["Set Communication apollo_status = 'Scheduled'"]
        MarkSynced --> EndCommSync(["Communication Custom Fields Synced"])
    end

    %% Workflow 6: Webhook Handling
    subgraph Webhook_Processing ["6. Webhook Engagement Processing"]
        ApolloWebhook(["Trigger: Apollo API Webhook Event"]) --> HandleWebhook["webhook_handle() Endpoint"]
        HandleWebhook --> VerifyBearerToken{"Valid Webhook Bearer Token?"}
        VerifyBearerToken -- No --> Throw401["Throw AuthenticationError (401)"]
        VerifyBearerToken -- Yes --> EnqueueProcessWebhook["process_webhook Background Job"]
        EnqueueProcessWebhook --> ResolveMCC["Find Multi Channel Cadence & Communication"]
        ResolveMCC --> DispatchEventReport["Cadence Provider report_event()"]
        DispatchEventReport --> EndWebhook(["Webhook Processed"])
    end

    %% Cross-Workflow Inter-connections
    EndOAuth -. Unlocks .-> CheckProviderAuth
    EndOAuth -. Unlocks .-> CheckLeadApolloID
    EndCadenceProv -. Maps Sequence .-> AssignSequence
    EndContactAssign -. Prepares Contact .-> UpdateContactCustomFields
```

## Key Event Triggers & Handlers

- **OAuth State Callback**: [`frappe_apollo.oauth.callback`](apps/frappe_apollo/frappe_apollo/oauth.py:7)
- **Webhook Endpoint**: [`frappe_apollo.webhook.handle`](apps/frappe_apollo/frappe_apollo/webhook.py:5)
- **Daily Cron Sweep**: [`frappe_apollo.apollo.doctype.email_account.email_account.queue_get_email_accounts`](apps/frappe_apollo/frappe_apollo/apollo/doctype/email_account/email_account.py:4)
- **Cadence Life Cycle Hooks**: [`frappe_apollo.apollo.doctype.cadence.cadence.on_update`](apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence/cadence.py:5) and [`on_trash`](apps/frappe_apollo/frappe_apollo/apollo/doctype/cadence/cadence.py:51)
- **Communication Sync Hook**: [`frappe_apollo.apollo.doctype.communication.communication.on_update`](apps/frappe_apollo/frappe_apollo/apollo/doctype/communication/communication.py:4)

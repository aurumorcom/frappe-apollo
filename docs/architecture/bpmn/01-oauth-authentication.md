# 1. OAuth Authorization Flow

This document details the behavioral workflow for OAuth authorization with Apollo API in [`apps/frappe_apollo/frappe_apollo/hooks.py`](apps/frappe_apollo/frappe_apollo/hooks.py:1).

## Trigger
User initiates OAuth Authorization or external OAuth dialog callback to [`oauth_callback`](apps/frappe_apollo/frappe_apollo/oauth.py:7).

## Workflow Flowchart

```mermaid
flowchart TD
    StartOAuth(["User Initiates OAuth Authorization"]) --> AccountAuthUrl["Apollo Account.get_authorization_url()"]
    AccountAuthUrl --> ApolloAuthRedirect["Redirect User to Apollo OAuth Dialog"]
    ApolloAuthRedirect --> ApolloCallback["Apollo API Posts Code to oauth_callback"]
    ApolloCallback --> TokenExchange["ApolloClient Exchanges Code for Access/Refresh Tokens"]
    TokenExchange --> SaveAccountToken["Save Tokens to Apollo Account (status = 'Authorized')"]
    SaveAccountToken --> EmitAccountUpdate["Emit Apollo Account on_update Event"]
    EmitAccountUpdate --> EndOAuth(["OAuth Authorized"])
```

## Component References

- **Apollo Account**: [`apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py`](apps/frappe_apollo/frappe_apollo/apollo/doctype/apollo_account/apollo_account.py:5)
- **ApolloClient**: [`apps/frappe_apollo/frappe_apollo/integrations/apollo.py`](apps/frappe_apollo/frappe_apollo/integrations/apollo.py:9)
- **oauth_callback**: [`apps/frappe_apollo/frappe_apollo/oauth.py`](apps/frappe_apollo/frappe_apollo/oauth.py:7)

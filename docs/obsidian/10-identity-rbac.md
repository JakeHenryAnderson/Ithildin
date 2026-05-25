---
title: Identity and RBAC
tags: [ithildin, identity, rbac]
---

# Identity and RBAC

Ithildin needs identity for humans, agents, endpoints, and tools.

## Principal Types

| Principal | Example |
| --- | --- |
| Human user | `user:alice` |
| Agent instance | `agent:cursor-local-dev` |
| Model identity | `model:llama-local` |
| Tool | `tool:fs.read_file@1.0.0` |
| Endpoint | `endpoint:dev-laptop-01` |
| Organization/tenant | `tenant:acme-law` |

## MVP Roles

| Role | Permissions |
| --- | --- |
| Owner | Full local configuration, policy edit, log export. |
| Admin | Manage tools, users, runtime settings. |
| SecurityAdmin | Manage policy, approval rules, audit retention. |
| Developer | Use approved tools in assigned workspaces. |
| Approver | Approve queued tool calls within assigned scope. |
| Auditor | Read logs and policy decisions. |
| AgentReadOnly | Read-only tools only. |
| AgentDeveloper | Read tools plus approved write tools in workspace. |

## Authorization Model

Use RBAC for coarse gates and ABAC for resource-specific decisions.

## Later Identity Work

- OIDC using Keycloak or another self-hosted identity provider.
- SSO/SAML for enterprise.
- SCIM provisioning.
- Agent identities as first-class objects.
- Short-lived delegated credentials.
- Two-person approval.
- Break-glass workflow.
- Per-tenant policy stores.


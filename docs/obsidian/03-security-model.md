---
title: Security Model
tags: [ithildin, security]
---

# Security Model

The security model is capability-based, policy-mediated, and audit-backed.

## Security Invariant

No agent-originated action reaches the endpoint unless:

1. the caller is authenticated;
2. the tool is registered;
3. the input matches schema;
4. the resource is in scope;
5. policy allows it or requires approval;
6. approval is satisfied when required;
7. execution happens inside the declared sandbox;
8. the full decision and result are logged.

## Trust Zones

| Zone | Includes |
| --- | --- |
| Untrusted | LLM output, prompts, tool suggestions, external content. |
| Semi-trusted | MCP client session, local browser UI, user-entered task. |
| Trusted | Ithildin router, policy evaluator, approval state machine, audit writer. |
| Constrained | Tool executor containers, mounted workspaces, network allowlists. |
| External | Model provider, package registries, remote APIs, cloud control plane. |

## MVP Controls

| Control | Requirement |
| --- | --- |
| Authentication | Local admin bootstrap token/session. |
| Tool registry | Static local manifests. |
| Policy | Deny-default YAML evaluator; OPA later. |
| Approval | Required for writes, deletes, external network, and high-risk operations. |
| Audit | Append-only JSONL plus SQLite/Postgres records. |
| Sandbox | Containerized execution, non-root, explicit mounts. |
| Path control | Canonical path validation and workspace allowlists. |
| Network control | HTTP allowlists; block private/link-local destinations. |
| Secret handling | Redaction in logs; no secret-returning tools in MVP. |
| Failure mode | Fail closed if policy, approval, or audit writer is unavailable. |


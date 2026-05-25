---
title: System Architecture
tags: [ithildin, architecture, mcp]
---

# System Architecture

## MVP Flow

```text
Agent / local LLM
  -> MCP tools/list + tools/call
  -> Ithildin MCP Gateway
  -> schema validation + policy decision
  -> Policy Engine
  -> allow / deny / require approval
  -> Approval + Audit Layer
  -> Sandboxed Governed Tools
  -> Endpoint workspace / APIs / local services
```

## Long-Term Shape

```text
Local/private LLMs, SaaS agents, IDE agents, copilots
  -> MCP/API-compatible governed access layer
  -> policy, identity, approval, audit, observability
  -> endpoint tools, local files, repositories, APIs, workflows
  -> optional enterprise control plane for fleet policy + audit
```

## Architectural Principles

| Principle | Practical meaning |
| --- | --- |
| Agent is untrusted | LLM output is treated as a proposed action, never as authority. |
| Router is trusted | The router validates identity, schemas, policy, approval, and execution scope. |
| Deny by default | Unknown agents, tools, paths, destinations, and actions are denied. |
| Tool manifests are authoritative | Tool behavior is described by trusted manifests, not model-facing prose. |
| Human approval is first-class | Approval is part of the execution state machine. |
| Logs are evidence | Audit events include actor, tool, resource, policy version, approval state, and outcome. |
| Local-first before cloud | The local runtime works without AWS or a hosted control plane. |
| Boring isolation | Prefer containers, read-only mounts, non-root users, network allowlists, and resource limits. |
| Small tool surface | Fewer well-governed tools are better than many weakly governed tools. |

## MVP Components

| Component | Responsibility |
| --- | --- |
| `ithildin-api` | Auth, REST API, approval workflow, audit index, tool registry. |
| `ithildin-mcp` | MCP adapter; may be the same process initially. |
| `ithildin-policy` | Embedded evaluator first; OPA sidecar later. |
| `ithildin-ui` | Dashboard, approvals, audit viewer. |
| `ithildin-executor` | Runs governed tools inside constrained profiles. |


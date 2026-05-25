---
title: Tool Governance
tags: [ithildin, mcp, tools]
---

# Tool Governance

Ithildin should expose tools to agents through MCP, while treating MCP as one protocol adapter rather than the whole product.

## Governance Rule

MCP tool descriptions are not policy.

MCP tool annotations are not policy.

Ithildin tool manifests are policy inputs.

## Tool Manifest Shape

```yaml
name: fs.apply_patch
version: 1.0.0
title: Apply file patch
risk: write
category: filesystem
mcp:
  exposed: true
  annotations:
    readOnlyHint: false
    destructiveHint: false
    idempotentHint: false
sandbox:
  filesystem:
    allowed_mounts:
      - /workspace
    deny_paths:
      - /workspace/.env
      - /workspace/secrets
  network:
    mode: none
approval:
  required: true
input_schema:
  type: object
  required: ["path", "patch"]
  properties:
    path:
      type: string
    patch:
      type: string
```

## Required Behavior

| Action | Behavior |
| --- | --- |
| `tools/list` | Return only tools the principal may know about. |
| `tools/call` | Validate schema, canonicalize inputs, evaluate policy. |
| Unknown tool | Deny and log. |
| Invalid input | Deny before policy execution. |
| Write operation | Require approval unless explicit policy says otherwise. |
| Destructive operation | Defer for MVP or always require approval. |
| External network | Allowlist and SSRF protection. |
| Tool output | Redact sensitive values before model sees them. |

## MVP Tools

| Tool | Risk | Behavior |
| --- | --- | --- |
| `fs.list` | read | List files under allowed workspace. |
| `fs.stat` | read | Return metadata for allowed file. |
| `fs.read` | read | Read allowed file with size limits. |
| `fs.search` | read | Search text under workspace. |
| `git.status` | read | Show repo status. |
| `git.diff` | read | Show diff. |
| `git.log` | read | Show recent commits. |
| `fs.propose_patch` | write-proposal | Generate patch preview; no mutation. |
| `fs.apply_patch` | write | Requires approval. |
| `http.fetch` | network | Allowlist only; SSRF protections. |


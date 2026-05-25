---
title: Testing Strategy
tags: [ithildin, testing, security]
---

# Testing Strategy

## Unit Tests

| Area | Tests |
| --- | --- |
| Path validation | `../`, symlinks, absolute paths, hidden paths. |
| Policy evaluator | allow, deny, approval, default deny. |
| Tool registry | invalid manifests, unknown tools, version mismatch. |
| Approval | expiry, replay, hash mismatch, denied state. |
| Audit | hash chain, redaction, missing required fields. |
| Schemas | invalid parameters, extra fields, type mismatch. |

## Integration Tests

| Flow | Expected result |
| --- | --- |
| Agent lists tools | Only permitted tools returned. |
| Agent reads allowed file | Success and audit event. |
| Agent reads `/etc/passwd` | Deny. |
| Agent writes file | Approval required. |
| Approved patch executes | Success. |
| Modified request after approval | Deny. |
| Policy unavailable | Fail closed. |
| Audit writer unavailable | Fail closed or block execution. |

## End-to-End Harness

Start Docker Compose, register a test agent, call `tools/list`, call `fs.read`, call `fs.apply_patch`, approve through API, verify file mutation, and verify audit chain.


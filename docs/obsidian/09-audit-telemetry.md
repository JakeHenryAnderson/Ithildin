---
title: Audit and Telemetry
tags: [ithildin, audit, telemetry]
---

# Audit and Telemetry

Audit logs are evidence. They are also sensitive data.

## MVP Architecture

Use two layers:

1. SQLite structured audit table for queries.
2. Append-only JSONL event log with hash chaining for tamper evidence.

## Event Shape

```json
{
  "event_id": "evt_01HY...",
  "timestamp": "2026-05-25T10:31:12Z",
  "event_type": "policy.evaluated",
  "request_id": "req_01HY...",
  "principal": "agent:local-dev",
  "human_user": "user:alice",
  "tool": "fs.apply_patch",
  "resource": "/workspace/project/src/app.py",
  "decision": "require_approval",
  "policy_version": "2026-05-25.1",
  "matched_rules": ["require_approval_for_file_write"],
  "input_hash": "sha256:...",
  "redactions": ["patch"],
  "prev_event_hash": "sha256:...",
  "event_hash": "sha256:..."
}
```

## Event Types

- `agent.session.started`
- `tool.list.requested`
- `tool.call.proposed`
- `policy.evaluated`
- `approval.created`
- `approval.approved`
- `approval.denied`
- `tool.execution.started`
- `tool.execution.completed`
- `tool.execution.failed`
- `audit.exported`
- `policy.changed`

## Redaction Requirement

Audit events may include file paths, prompts, parameters, network destinations, and policy metadata. Add redaction hooks early and test them.


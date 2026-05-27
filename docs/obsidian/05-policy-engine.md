---
title: Policy Engine
tags: [ithildin, policy]
---

# Policy Engine

Use a typed policy input model from day one.

## Recommendation

| Phase | Recommendation |
| --- | --- |
| MVP | Simple YAML policy plus deterministic Python evaluator. |
| Near-term | OPA sidecar with generated policy bundles and decision logs. |
| Long-term | Optional Cedar/AWS Verified Permissions compatibility for enterprise alignment. |

Do not invent a full custom policy language in the MVP.

The runtime now defaults to `ITHILDIN_POLICY_ENGINE=yaml`. An optional OPA prototype can be
selected with `ITHILDIN_POLICY_ENGINE=opa`, `ITHILDIN_OPA_URL`, and
`ITHILDIN_OPA_DECISION_PATH`. OPA responses must return a JSON `result` object shaped like the
decision result below. If the sidecar is unavailable or returns malformed data, Ithildin returns a
deny decision with a fail-closed obligation.

OPA mode also verifies `ITHILDIN_OPA_BUNDLE_MANIFEST_PATH` before startup. The bundle manifest pins
the local Rego source hash and entrypoint; verified bundle evidence is surfaced in policy status and
used as the fallback policy version when OPA omits one.

## Policy Input Shape

```json
{
  "principal": {
    "type": "agent",
    "id": "agent:local-dev",
    "roles": ["AgentDeveloper"],
    "owner_user_id": "user:alice"
  },
  "tool": {
    "name": "fs.apply_patch",
    "risk": "write",
    "version": "1.0.0"
  },
  "resource": {
    "type": "file",
    "path": "/workspace/project/src/app.py",
    "workspace": "project-a"
  },
  "context": {
    "approval_id": null,
    "network": false,
    "session_id": "sess_123"
  }
}
```

## Decision Result

```json
{
  "decision": "allow",
  "reason": "read within assigned workspace",
  "policy_version": "2026-05-25.1",
  "matched_rules": ["allow_agent_read_workspace"],
  "obligations": {
    "audit_level": "full",
    "redact_fields": ["content", "token"],
    "max_execution_seconds": 30
  }
}
```

Decision values: `allow`, `deny`, `require_approval`.

## MVP Rules

- Read-only workspace access may be auto-allowed.
- Writes require approval.
- Deletes, shell, Docker, secret reads, and broad network access are denied.
- Unknown tools, unknown principals, invalid inputs, and out-of-scope resources are denied.

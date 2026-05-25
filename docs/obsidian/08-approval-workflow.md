---
title: Approval Workflow
tags: [ithildin, approval]
---

# Approval Workflow

Approval is a state machine, not a boolean.

## States

```text
created -> pending -> approved -> executing -> executed
                 \-> denied
                 \-> expired
                 \-> superseded
                 \-> failed
```

## Approval Record

```json
{
  "approval_id": "appr_01HY...",
  "request_id": "req_01HY...",
  "status": "pending",
  "principal": "agent:local-dev",
  "human_owner": "user:alice",
  "tool": "fs.apply_patch",
  "risk": "write",
  "resource": "/workspace/project/src/app.py",
  "summary": "Modify app.py",
  "diff_hash": "sha256:...",
  "policy_reason": "file writes require approval",
  "expires_at": "2026-05-25T10:45:00Z"
}
```

## UI Must Show

- agent identity;
- human user/session;
- tool name and version;
- resource/path;
- exact parameters or safe summary;
- diff for writes;
- network destination for HTTP/API tools;
- policy rule that triggered approval;
- one-time approval scope.

## MVP Rules

| Risk | Behavior |
| --- | --- |
| Read workspace file | Auto-allow if policy permits. |
| Read sensitive path | Deny. |
| Write file | Approval required. |
| Delete file | Deferred or deny. |
| External HTTP fetch | Approval or allowlist. |
| Shell command | Deferred. |
| Secret access | Deferred. |
| Docker/Kubernetes actions | Deferred. |

Avoid "approve all similar actions forever" in the MVP.


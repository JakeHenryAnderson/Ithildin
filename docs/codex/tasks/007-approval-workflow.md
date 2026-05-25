# Task 007 - Approval Workflow

## Goal

Implement one-time approvals bound to exact requests.

## Scope

- Create approval.
- Approve, deny, expire.
- Bind approval to request hash.
- Prevent replay.

## Acceptance Criteria

- Write calls can create pending approval requests.
- Approved requests can execute once.
- Modified requests after approval are denied.
- Expired or denied approvals cannot execute.
- Approval events are audited.


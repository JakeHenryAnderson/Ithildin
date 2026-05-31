# Patch Apply Source Review Checklist

Task 159 creates the source-review checklist for `fs.patch.apply`, Ithildin's only local-preview
write path. Use it with [source-review-runbook-v2.md](source-review-runbook-v2.md),
[source-file-inspection-packet.md](source-file-inspection-packet.md), and
[patch-apply-state-machine.md](patch-apply-state-machine.md).

## Files And Functions

Inspect:

- `apps/api/src/ithildin_api/patches.py`
  - `PatchProposalService.apply_approved`
  - `PatchProposalService.approval_scope`
  - `PatchProposalService.approval_review`
  - `PatchProposalService.patch_apply_diagnostics`
  - `PatchProposalService._prepare_apply`
  - `PatchProposalService._record_apply_failure`
  - `PatchProposalStore.create_apply_attempt`
  - `PatchProposalStore.set_apply_attempt_status`
  - `_apply_attempt_transition_allowed`
  - `_atomic_write_text`
- `apps/api/src/ithildin_api/approvals.py`
  - `ApprovalService.begin_execution`
  - `ApprovalService.complete_execution`
  - `ApprovalService.fail_execution`
- `apps/api/src/ithildin_api/tool_calls.py`
  - `GovernedToolCallService._execute_approved_patch`
  - `GovernedToolCallService.call_tool`

## Claims To Test

- `fs.patch.apply` is stored-proposal-only and cannot apply caller-supplied diff content directly.
- Approval scope binds proposal ID/hash, base file hash, target path, manifest hash/version, schema
  hash, policy evidence, requesting principal, request hash, expiry, and scope hash.
- Approval begin/consume is one-time and replay-resistant.
- Manifest, policy, schema, proposal, principal, request, path, and base-file drift fail closed before
  writing.
- The target file is re-read and base hash is checked immediately before replacement.
- Atomic replace uses a same-directory temporary file and does not broaden write capability.
- Failure before replacement leaves the target unchanged and records failed attempt evidence.
- Failure after replacement records `file_replaced` or `recovery_required` diagnostics without
  adding mutating repair.
- Diagnostics are read-only and do not expose diff text or file contents.
- Audit transition metadata is safe and does not include file contents, diff contents, admin tokens,
  private keys, or secrets.

## Evidence Commands

```sh
uv run pytest tests/test_governed_tool_calls.py tests/test_approval_workflow.py tests/test_security_regressions.py
uv run pytest tests/test_patch_proposals.py
make release-check
```

## Finding Prompts

For every issue, record:

- which state transition or approval binding failed;
- whether the issue is pre-write, post-replace/pre-completion, replay, stale-base, drift, or
  diagnostics exposure;
- whether it could modify files outside the reviewed stored proposal;
- whether it blocks external review, broader distribution, or any future capability expansion.

Use `ISR-###`, `SUB-###`, `AI-###`, or `EXT-###` finding IDs depending on reviewer type.

## Non-Goals

This checklist does not authorize broad writes, delete/move/chmod/archive operations, repair
endpoints, shell execution, Docker/Kubernetes/browser tools, or production custody claims.

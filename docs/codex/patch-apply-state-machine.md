# Patch Apply State Machine

This contract documents the local-preview state machine for `fs.patch.apply`. Patch apply remains
the only write path in the v0.1 local-preview runtime boundary. It applies only stored patch
proposals, only after one-time approval, and only after proposal, manifest, schema, policy,
principal, request, base-file, and target-path evidence still match.

## Approval States

Patch apply consumes an approval only when the approval is `approved`, unexpired, for
`fs.patch.apply`, and its request hash matches the approval record. `begin_execution` atomically
moves the approval to `executing` before file replacement. Successful completion moves it to
`executed`. Failures before replacement move it to `failed`. Failures after replacement leave it
non-replayable and diagnosable rather than pretending the operation cleanly failed.

Replay is denied for approvals that are pending, denied, expired, executing, executed, failed, for a
different tool, for a different proposal, or whose one-time scope no longer matches current
manifest, policy, schema, principal, proposal, or target evidence.

## Apply Attempt States

`patch_apply_attempts` records one attempt per approval ID:

| State | Meaning | Operator posture |
| --- | --- | --- |
| `prepared` | Approval was consumed and expected post-apply hash was computed before replacement completed. | Diagnose before retrying; target may still be base or may have been replaced if later state recording failed. |
| `file_replaced` | Atomic same-directory replacement completed before later state transitions completed. | Recovery diagnostics required; do not replay or repair automatically. |
| `completed` | File replacement, proposal status, approval completion, and attempt completion all succeeded. | Clean terminal state. |
| `failed` | Failure happened before replacement or before an apply attempt could become side-effectful. | Terminal failed state; no partial workspace write is expected. |
| `recovery_required` | Replacement appears to have happened but later database/audit/proposal/approval transitions did not all complete. | Read-only diagnostics only; manual operator review required. |

The diagnostics endpoint reports `clean`, `ambiguous`, or `recovery_required`. It never repairs,
rolls back, completes approvals, or exposes file contents or diff contents.

## Fault Injection Evidence

Task 117 adds named test-only fault-injection phases around proposal validation, approval execution,
apply preparation, attempt creation, atomic replacement, proposal completion, approval completion,
and final attempt completion. These hooks are not exposed through API or MCP; they exist so review
tests can deterministically prove pre-replacement failures leave files unchanged and
post-replacement failures require read-only recovery diagnostics.

## Failure Classes

- Attempt creation failure: approval is marked failed, no attempt is stored, and the target remains
  unchanged.
- Replacement failure before side effect: attempt is marked failed, approval is marked failed, and
  the target remains unchanged.
- Replacement succeeded but state recording failed: attempt remains `prepared` or becomes
  `recovery_required`; approval remains non-replayable; diagnostics compare current target hash to
  expected post-apply hash.
- Proposal, approval, or final attempt completion failure after replacement: diagnostics require
  manual review and the API returns a safe recovery-required denial.

## Non-Goals

This contract does not add repair, rollback, retry, broad filesystem writes, shell execution, or
production custody. Recovery remains read-only until external/source review determines whether a
mutating reconciliation flow is appropriate.

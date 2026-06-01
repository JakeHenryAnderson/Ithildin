# EXT-PA-003 Approval Expiry Transition

- Finding ID: EXT-PA-003
- Severity: low
- Area: patch-apply
- Affected files/functions: apps/api/src/ithildin_api/approvals.py; ApprovalStore.compare_and_set_status; ApprovalService.begin_execution
- Claim being tested: approval execution should not cross the expiry boundary between Python-side expiry checks and the status transition to `executing`.
- Observed behavior: The external source review noted that expiry was checked before the approval status compare-and-set, leaving a small boundary race if expiry happened between the check and transition.
- Risk: A narrowly expired approval could be consumed if the status transition did not also guard the expiry deadline.
- Recommended fix: Include expiry in the atomic execution transition or immediately re-check after transition and fail safely.
- Blocking status: later
- Disposition: fixed
- Verification notes: `ApprovalStore.compare_and_set_status()` now supports an `expires_after` guard, and `ApprovalService.begin_execution()` passes the current timestamp when moving an approval to `executing`. `test_begin_execution_uses_expiry_guard_in_atomic_transition` verifies the execution transition carries the expiry guard. GPT 5.5 Pro source-level recheck at commit `652c4c47ead00ed543b074f1caea80970c5421ef` found this closed for the v0.1 local-preview patch-apply lane.

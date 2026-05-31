# EXT-PA-001 Final Completion Audit State

- Finding ID: EXT-PA-001
- Severity: medium
- Area: patch-apply
- Affected files/functions: apps/api/src/ithildin_api/tool_calls.py; GovernedToolCallService._execute_approved_patch; apps/api/src/ithildin_api/patches.py; PatchProposalService.apply_approved; patch apply attempt state machine
- Claim being tested: successful patch apply evidence should remain recoverable if final audit writing fails after file replacement.
- Observed behavior: The external source review found that the successful `tool.execution.completed` audit event was written after `PatchProposalService.apply_approved()` returned, so an audit write failure could occur after the file, proposal, approval, and apply-attempt state were already terminal.
- Risk: Diagnostics could report a clean completed patch apply while the final successful execution audit event was missing.
- Recommended fix: Move or couple the final successful audit write into the recoverable apply state machine before the attempt reaches `completed`, or mark visible recovery state if that audit write fails.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `PatchProposalService.apply_approved()` now accepts a completion hook and executes the successful patch-apply audit before marking the apply attempt `completed`. If the hook fails after replacement, the attempt becomes `recovery_required` and diagnostics surface the post-apply hash state. `test_patch_apply_completed_audit_failure_is_diagnosable` covers the failure path; focused patch, approval, and security-regression tests pass.

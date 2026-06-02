# SUB-084 Patch Apply Missing Scope Approval

- Finding ID: SUB-084
- Severity: medium
- Area: review console/admin boundary
- Affected files/functions: apps/api/src/ithildin_api/app.py `approve_approval`; apps/api/src/ithildin_api/patches.py `approval_review`; tests/test_api_service.py
- Claim being tested: A patch-apply approval should be approved only after the API verifies complete immutable binding evidence for the stored proposal/action.
- Observed behavior: Internal proxy review found that `POST /approvals/{approval_id}/approve` re-ran patch-apply binding review only when `one_time_scope.proposal_id` was already a string. A malformed `fs.patch.apply` approval missing `proposal_id` could be marked approved, although runtime patch apply still failed closed later.
- Risk: Approval records could overstate review success for malformed patch-apply scopes, weakening approval evidence clarity even though file mutation remained gated.
- Recommended fix: Always run patch-apply binding review for `fs.patch.apply` approvals before approval state mutation, and reject missing or malformed proposal scope as a safe conflict.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `approve_approval` now runs `_patch_apply_approval_review` for every `fs.patch.apply` approval and normalizes patch proposal validation errors to a safe `409` binding-review failure. `test_patch_apply_approval_requires_valid_binding_scope_before_approval` verifies missing proposal scope cannot be approved. External/source review remains pending.

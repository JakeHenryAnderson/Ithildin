# SUB-078 Approval Review Drift

- Finding ID: SUB-078
- Severity: medium
- Area: review console/admin boundary
- Affected files/functions: apps/ui/src/App.tsx `decideApproval`; apps/api/src/ithildin_api/app.py `approve_approval`; apps/api/src/ithildin_api/patches.py `approval_review`
- Claim being tested: A patch-apply approval should be approved only when the currently reviewed binding evidence still matches the exact stored proposal/action.
- Observed behavior: The review console disabled approve controls when `/approvals/review` reported invalid binding evidence, but the API approval route did not re-run the patch-apply binding review immediately before marking an approval approved. Execution still denied stale approvals later, so file mutation remained gated, but stale approvals could be recorded as approved.
- Risk: Admin review evidence could become confusing after proposal/policy/manifest/principal drift, weakening approval traceability even though patch execution still failed closed.
- Recommended fix: Re-run patch-apply approval binding review server-side in `POST /approvals/{approval_id}/approve` and reject stale approvals before approval state mutation.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `approve_approval` now re-runs `_patch_apply_approval_review` for `fs.patch.apply` approvals before approval state mutation. `test_approve_patch_apply_rejects_stale_binding_review` verifies stale binding evidence returns `409` and leaves the approval pending. External/source review remains pending.

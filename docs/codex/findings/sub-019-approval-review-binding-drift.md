# SUB-019 Approval Review Binding Drift

- Finding ID: SUB-019
- Severity: high
- Area: review console/admin approval review
- Affected files/functions: apps/api/src/ithildin_api/patches.py; PatchProposalService.approval_review; apps/api/src/ithildin_api/app.py; list_approval_reviews
- Claim being tested: approval review evidence should mirror runtime patch-apply binding checks closely enough that the UI does not report invalid approvals as reviewable.
- Observed behavior: Approval review checked proposal/hash/base fields but did not check policy version, matched rules, requesting principal, or proposal status as explicit binding evidence.
- Risk: The review console could show `valid: true` for approval evidence that runtime patch apply would reject after approval.
- Recommended fix: Add approval-review checks for policy version, matched rules, requesting principal, and proposal status using the same scope fields runtime apply verifies.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Approval review now checks policy version, matched rules, requesting principal, and proposal status in addition to existing manifest/schema/proposal/base checks. API tests cover drift in policy version, matched rules, and requesting principal. External/source review remains pending.

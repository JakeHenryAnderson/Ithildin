# SUB-027 Approval Expiry Transition Race

- Finding ID: SUB-027
- Severity: medium
- Area: approval workflow
- Affected files/functions: apps/api/src/ithildin_api/approvals.py; ApprovalService.begin_execution; ApprovalStore.compare_and_set_status; tests/test_approval_workflow.py
- Claim being tested: An approval cannot transition from approved to executing after its expiry time, including the race window between service-level expiry checks and the SQLite compare-and-set transition.
- Observed behavior: Internal proxy review found that begin_execution captured a timestamp, checked expiry, and passed that same timestamp into the SQL transition guard. If an approval expired after the Python check but before the SQLite update, the SQL predicate could still compare against the stale timestamp and transition the approval to executing.
- Risk: An approval could be consumed just after its expiry boundary, weakening the one-time approval boundary for approval-gated patch apply.
- Recommended fix: Use the store's transition-time timestamp for the atomic SQL expiry predicate, and convert a failed approved-to-executing transition caused by expiry into an explicit expired status/error.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: ApprovalStore.compare_and_set_status now compares expires_at against a fresh transition-time timestamp generated inside the store. ApprovalService.begin_execution now marks an approval expired when the atomic transition misses because the approval expired during the transition window. Regression coverage is tests/test_approval_workflow.py::test_begin_execution_rejects_approval_expiring_during_atomic_transition.

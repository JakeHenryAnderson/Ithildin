# EXT-PA-002 Proposal Single-Use CAS

- Finding ID: EXT-PA-002
- Severity: medium
- Area: patch-apply
- Affected files/functions: apps/api/src/ithildin_api/patches.py; PatchProposalStore.set_status; PatchProposalStore.compare_and_set_status; PatchProposalService.apply_approved
- Claim being tested: a stored patch proposal should not be applied twice through two separately approved approvals.
- Observed behavior: The external source review found that proposal completion used an unconditional status update, while approval consumption was per approval rather than per proposal.
- Risk: Two approved approvals for the same stored proposal could race through validation before the proposal became `applied`, creating ambiguous duplicate execution evidence.
- Recommended fix: Add proposal-level compare-and-set or reservation semantics, such as `proposed` to `applying` to `applied`, or enforce one active approval per proposal.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Patch apply now reserves proposals with a `proposed` to `applying` compare-and-set before filesystem mutation and completes them with an `applying` to `applied` compare-and-set after replacement. Pre-replacement reservation failures fail safely and leave no write. `test_two_approved_apply_calls_for_same_proposal_mutate_once` verifies that two approved approvals for one proposal result in exactly one filesystem mutation.

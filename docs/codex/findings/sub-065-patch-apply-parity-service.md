# SUB-065 Patch Apply Parity Service

- Finding ID: SUB-065
- Severity: medium
- Area: policy preview/runtime parity
- Affected files/functions: apps/api/src/ithildin_api/policy_parity.py; policies/tests/parity.yaml; tests/test_policy_parity.py
- Claim being tested: Policy parity fixtures should compare preview with the real governed patch-apply path, not a placeholder missing patch proposal service behavior.
- Observed behavior: Internal proxy review found that the parity harness did not seed a real patch proposal service for `fs.patch.apply` parity.
- Risk: Preview/runtime parity could pass while runtime behavior differed because the executor path was unavailable or denied for the wrong reason.
- Recommended fix: Seed a real proposal in the parity harness and replace the fixture placeholder proposal ID at runtime.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The parity harness now initializes `PatchProposalStore`/`PatchProposalService`, seeds a real proposal, and expects `approval_required` for the write fixture. External/source review remains pending.

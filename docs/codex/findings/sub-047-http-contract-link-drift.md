# SUB-047 HTTP Contract Link Drift

- Finding ID: SUB-047
- Severity: low
- Area: source review runbook documentation
- Affected files/functions: docs/codex/source-review-runbook-v2.md; tests/test_release_readiness.py
- Claim being tested: Review-critical runbook links should resolve to existing contract documents.
- Observed behavior: Internal proxy review found that the runbook linked `http-fetch-executor-contract.md`, while the actual committed contract file is `http-executor-contract.md`.
- Risk: Reviewer navigation friction and stale packet pointers.
- Recommended fix: Correct the link and add a release-readiness assertion for the review-critical HTTP contract path.
- Blocking status: later
- Disposition: fixed
- Verification notes: The runbook now links to `http-executor-contract.md`, and release-readiness tests assert the corrected link exists. External/source review remains pending.

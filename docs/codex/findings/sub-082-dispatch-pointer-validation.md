# SUB-082 Dispatch Pointer Validation

- Finding ID: SUB-082
- Severity: medium
- Area: release automation/evidence gates
- Affected files/functions: scripts/external_review_dispatch_packets.py; tests/test_release_readiness.py
- Claim being tested: Focused external-review dispatch packets should only reference source and review-document paths that exist in the current repo.
- Observed behavior: The policy/registry dispatch packet referenced stale SUB-016/SUB-017 finding filenames even though the actual finding docs had clearer current names.
- Risk: Reviewers could lose time chasing missing documents or assume packet evidence was stale.
- Recommended fix: Correct stale finding paths and fail dispatch generation when any area references a missing source or review-document path.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The policy/registry dispatch paths now reference `sub-016-manifest-input-schema-validation.md` and `sub-017-policy-parity-resource-scope.md`. Dispatch generation validates all `source_files` and `review_docs` across every area before writing packets, and release-readiness tests assert every dispatch pointer exists. External/source review remains pending.

# SUB-077 Review Candidate Dispatch Freshness

- Finding ID: SUB-077
- Severity: medium
- Area: release automation/evidence gates
- Affected files/functions: Makefile; docs/codex/reviewer-reproduction-map.md; tests/test_release_readiness.py; scripts/external_review_dispatch_packets.py; docs/codex/source-review-closure-matrix.md
- Claim being tested: `make review-candidate` should refresh every review artifact that external reviewers are told to inspect.
- Observed behavior: `make review-candidate` regenerated the main review bundle and consolidated packet, but it did not run `make v06-review-dispatch-packets`, so the focused v0.6 dispatch packets could remain stale after a fresh one-command handoff run.
- Risk: Reviewers could inspect outdated lane-specific dispatch packets while the main bundle appears current, weakening traceability for source-review handoff evidence.
- Recommended fix: Add `make v06-review-dispatch-packets` to the `review-candidate` sequence, document the expected output in the reproduction map, and assert the command ordering in release-readiness tests.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `make review-candidate` now runs `make v06-review-dispatch-packets` before bundle/consolidated generation, the reproduction map names the focused dispatch packet output and hashes, and release-readiness tests assert the command is wired in sequence. External/source review remains pending.

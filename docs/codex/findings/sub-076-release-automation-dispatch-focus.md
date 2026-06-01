# SUB-076 Release Automation Dispatch Focus

- Finding ID: SUB-076
- Severity: medium
- Area: release automation/evidence gates
- Affected files/functions: scripts/external_review_dispatch_packets.py; tests/test_release_readiness.py; docs/codex/source-review-closure-matrix.md
- Claim being tested: release-automation dispatch packets should give external reviewers focused source, test, evidence, and finding pointers rather than broad directory references.
- Observed behavior: the release-automation packet referenced `scripts/` and `docs/codex/` as broad source roots and included only part of the release-automation finding trail.
- Risk: reviewers could miss the specific evidence gates, packet hash checks, redaction scanner, release-evidence validators, and finding records that need source-level review.
- Recommended fix: Replace broad directory pointers with focused scripts/tests/docs and include the relevant release automation findings from `SUB-022` through `SUB-026`, `SUB-054`, and `SUB-060` through `SUB-063`.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: the release-automation dispatch area now enumerates the focused release/evidence scripts, release-readiness tests, key release docs, and the full internal finding trail for this lane. Release-readiness tests assert the generated packet contains the focused sources, commands, and findings. External/source review remains pending.

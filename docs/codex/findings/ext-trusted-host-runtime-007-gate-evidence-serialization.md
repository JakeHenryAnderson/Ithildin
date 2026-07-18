# EXT-TRUSTED-HOST-RUNTIME-007 Gate Evidence Serialization

- Finding ID: EXT-TRUSTED-HOST-RUNTIME-007
- Severity: medium
- Area: trusted-host-promotion-runtime
- Affected files/functions: scripts/trusted_host_promotion_runtime_source_review_bundle.py; build_bundle; 05_TRUSTED_HOST_PROMOTION_RUNTIME_GATE_EVIDENCE.json; tests/test_release_readiness.py
- Claim being tested: A generated runtime source-review packet must embed gate evidence for that same newly generated packet and exact candidate, independent of any packet that existed before regeneration.
- Observed behavior: Exact-candidate re-review at commit 4dcf8ad26df4c3a6f4c2271d3fbe6c35566c67b6 found that the regenerated packet embedded the previous packet commit 63c7ffd47853ed2f5f132772ca1af264555456be and `commit_matches_head: false` while the embedded report still said `valid: true`.
- Risk: A contradictory handoff artifact could be treated as clean even though its embedded packet evidence described a prior candidate.
- Recommended fix: Generate the packet in two passes, replace pre-generation state with evidence computed from the newly written packet, refresh the artifact manifest, and run final exact-candidate self-validation.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: build_bundle now writes initial current-candidate evidence, computes evidence from the newly generated packet, rewrites the gate-evidence artifact and manifest, and performs final self-validation. Focused regression coverage rebuilds over a stale packet and requires embedded commit and artifact-hash evidence to match the live generated packet. Exact-candidate independent re-review remains required.

# SUB-072 Policy Registry Dispatch Coverage

- Finding ID: SUB-072
- Severity: medium
- Area: v0.6 external review packet traceability
- Affected files/functions: scripts/external_review_dispatch_packets.py; tests/test_release_readiness.py
- Claim being tested: The focused policy/registry external-review packet should include source/test pointers and commands for preview/runtime parity and fail-closed registry behavior.
- Observed behavior: Internal proxy review found that the policy/registry dispatch packet omitted several key source files, fixtures, tests, and current findings.
- Risk: A reviewer could miss the code paths that decide principal/resource normalization, schema validation, registry loading, and runtime audit parity.
- Recommended fix: Expand policy/registry packet source files, review docs, and commands with parity, governed-call, schema-validation, YAML-loader, registry, identity, workspace, API, and test pointers.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `policy-registry.md` dispatch generation now includes the focused source/test set, `SUB-015` through `SUB-017`, and `SUB-064` through `SUB-073`. External/source review remains pending.

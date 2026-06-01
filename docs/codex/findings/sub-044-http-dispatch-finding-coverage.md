# SUB-044 HTTP Dispatch Finding Coverage

- Finding ID: SUB-044
- Severity: medium
- Area: v0.6 external review packet traceability
- Affected files/functions: scripts/external_review_dispatch_packets.py; docs/codex/v0.6-external-review-assignment-matrix.md; tests/test_release_readiness.py
- Claim being tested: HTTP external review packets should carry the internal findings a reviewer needs to inspect remediation history.
- Observed behavior: Internal proxy review found that the HTTP dispatch packet included `SUB-001` but omitted later HTTP findings, even though the closure matrix knew about them.
- Risk: A reviewer could receive an incomplete HTTP handoff and miss known remediation history for safe errors, port parsing, audit resource redaction, preview parity, Unicode transport handling, and JSON parser handling.
- Recommended fix: Include all HTTP finding records in the HTTP dispatch packet and add a release-readiness assertion for the generated packet.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The HTTP dispatch packet now includes `SUB-001`, `SUB-007`, `SUB-008`, `SUB-009`, and `SUB-040` through `SUB-043`. Release-readiness tests assert generated `http-fetch.md` includes each record. External/source review remains pending.

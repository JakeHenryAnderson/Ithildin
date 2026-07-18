# EXT-TRUSTED-HOST-RUNTIME-006 Adversarial Coverage

- Finding ID: EXT-TRUSTED-HOST-RUNTIME-006
- Severity: medium
- Area: trusted-host-promotion-runtime
- Affected files/functions: tests/test_api_service.py; scripts/trusted_host_promotion_negative_transcripts.py; scripts/trusted_host_promotion_runtime_source_review_bundle.py; FOCUSED_TEST_COMMAND
- Claim being tested: The runtime handoff must include direct evidence for binding mismatch, concurrency, unsafe source object types, destination conflict, audit interruption, and governance drift.
- Observed behavior: Independent packet-and-source review at commit 63c7ffd47853ed2f5f132772ca1af264555456be found the focused tests and generated transcripts too narrow for the documented trust claims.
- Risk: Review could miss a replay, overwrite, object-race, incomplete-evidence, or governance-drift regression while relying on a nominal happy-path packet.
- Recommended fix: Expand focused API tests, observed negative transcripts, and the packet command to cover each adversarial category and retain safe output assertions.
- Blocking status: should-fix
- Disposition: deferred
- Verification notes: The remediation candidate adds route and copied-approval mismatch, concurrent apply, symlink, hardlink, directory, existing-destination, and completion-audit failure tests; the observed transcript generator now covers mismatch, symlink, hardlink, and destination conflict. Governance-drift evidence remains deferred with EXT-TRUSTED-HOST-RUNTIME-002 until those bindings exist, so this finding is not fully closed and exact-candidate independent re-review remains required.

# EXT-TRUSTED-HOST-RUNTIME-008 Interrupted Packet Generation

- Finding ID: EXT-TRUSTED-HOST-RUNTIME-008
- Severity: medium
- Area: trusted-host-promotion-runtime
- Affected files/functions: scripts/trusted_host_promotion_runtime_source_review_bundle.py; build_bundle; build_check_report; 05_TRUSTED_HOST_PROMOTION_RUNTIME_GATE_EVIDENCE.json; tests/test_release_readiness.py
- Claim being tested: The public packet checker must fail closed if generation stops after an internally hash-consistent intermediate packet is written but before final embedded gate evidence is synchronized.
- Observed behavior: Exact-candidate re-review at commit 8755a39585993fc057cfd30564cb867098cf7f52 reproduced an interruption after the initial artifact manifest but before the gate-evidence and manifest rewrite. The live checker reported `valid: true` even though the hash-consistent packet embedded `artifact_hashes_match_files: false`.
- Risk: An interrupted, contradictory handoff packet could pass the public checker and be mistaken for completed exact-candidate evidence.
- Recommended fix: Make the public checker parse the embedded gate-evidence artifact and require its `existing_packet` evidence to exactly match evidence computed from the live packet; reject missing, malformed, or mismatched embedded evidence.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: build_check_report now fails closed when embedded packet evidence is missing, malformed, or differs from live evidence. A focused regression creates the hash-consistent intermediate state, proves rejection, rebuilds it, and proves the completed packet is accepted. Exact-candidate independent re-review remains required.

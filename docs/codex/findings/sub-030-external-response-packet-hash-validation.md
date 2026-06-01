# SUB-030 External Response Packet Hash Validation

- Finding ID: SUB-030
- Severity: medium
- Area: release automation
- Affected files/functions: scripts/external_response_normalize.py; normalize_response; tests/test_release_readiness.py
- Claim being tested: Reviewed packet hashes in normalized external responses use the exact sha256:<64 lowercase hex> format documented for dispatch packet evidence.
- Observed behavior: Internal proxy review confirmed that sha256:not-a-real-digest was accepted because the normalizer only checked the sha256: prefix.
- Risk: Review intake could claim a packet hash without a real digest, weakening packet-to-response traceability.
- Recommended fix: Validate reviewed packet hashes with a strict sha256:[0-9a-f]{64} pattern.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The normalizer now enforces the full SHA-256 digest format. Regression coverage is tests/test_release_readiness.py::test_external_response_normalization_rejects_malformed_packet_hash.

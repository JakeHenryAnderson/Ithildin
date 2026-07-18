# EXT-TRUSTED-HOST-RUNTIME-005 Packet Freshness

- Finding ID: EXT-TRUSTED-HOST-RUNTIME-005
- Severity: medium
- Area: trusted-host-promotion-runtime
- Affected files/functions: scripts/trusted_host_promotion_runtime_source_review_bundle.py; build_check_report; _existing_packet_evidence; tests/test_release_readiness.py
- Claim being tested: A present runtime source-review packet must be bound to current HEAD, clean generation state, and the exact generated artifact bytes.
- Observed behavior: Independent packet-and-source review at commit 63c7ffd47853ed2f5f132772ca1af264555456be found that the packet checker validated source wiring but did not reject a stale generated packet.
- Risk: A reviewer could receive a packet whose commit labels or artifacts do not describe the current candidate even though the check reported valid.
- Recommended fix: Validate both packet commit labels against current HEAD, require clean-generation evidence, and compare the recorded artifact manifest with hashes computed from present packet files.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: build_check_report now validates a present packet while allowing a genuinely absent ignored packet in a fresh checkout. A focused regression mutates both packet commit labels, refreshes its internal hashes, and proves the public checker still rejects the stale binding. Exact-candidate independent re-review remains required.

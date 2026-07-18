# EXT-TRUSTED-HOST-RUNTIME-010 Packet Candidate Equivalence

- Finding ID: EXT-TRUSTED-HOST-RUNTIME-010
- Severity: medium
- Area: exact-candidate review evidence
- Affected files/functions: scripts/trusted_host_promotion_runtime_source_review_bundle.py; build_check_report; _candidate_digest_evidence_valid; _existing_packet_evidence; tests/test_release_readiness.py
- Claim being tested: The public trusted-host runtime packet checker proves that bundled source, tests, contracts, and the closed runtime inventory are exactly the reviewed clean commit rather than merely internally hash-consistent packet files.
- Observed behavior: Independent re-review of commit a56f51c27a7c4971ccd5510da60cc0e091a8a9ef showed that a copied packet remained publicly valid after weakening the bundled required-role constant and refreshing the unsigned artifact manifest. A second reproduction removed `workspaces/local.yaml` from the candidate inventory and recomputed internal digests while the public checker still returned valid.
- Risk: A reviewer could receive altered authority code or an incomplete candidate inventory while the handoff checker reports that the packet is valid, weakening the exact-candidate claim even though the packet generated at the reviewed commit was itself byte-exact.
- Recommended fix: Compare source, test, and contract bundles byte-for-byte with the live clean candidate; require the inventory path set and count to exactly match the closed runtime inventory; validate fixed evidence fields; and bind candidate identifiers and digests repeated in the index to the candidate evidence.
- Blocking status: blocking
- Disposition: fixed
- Verification notes: The checker now exposes and requires bundle-to-HEAD equality and index-to-candidate equality. Candidate validation requires the exact runtime path list and count, closed evidence fields, fixed schema/domain/path values, and the exact detached review packet. Regression tests refresh packet hashes after a bundled role weakening and recompute all internal candidate digests after omitting a runtime file; both cases must fail the public check. A regenerated clean exact-candidate packet and independent re-review remain required before closure.

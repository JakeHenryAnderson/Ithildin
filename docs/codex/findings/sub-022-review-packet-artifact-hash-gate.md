# SUB-022 Review Packet Artifact Hash Gate

- Finding ID: SUB-022
- Severity: high
- Area: release automation
- Affected files/functions: scripts/review_packet_diff.py; collect_packet_artifacts; _verify_listed_artifacts
- Claim being tested: review-packet diff gates should independently verify packet artifact integrity instead of trusting generated metadata.
- Observed behavior: The diff gate accepted `artifact-hashes.json` entries without recomputing artifact hashes and did not fail on unlisted packet files.
- Risk: A stale, tampered, or extra packet artifact could be handed to a reviewer while the gate still reported a clean packet comparison.
- Recommended fix: Recompute each listed artifact hash and byte count from disk, fail on missing or mismatched artifacts, fail on unlisted artifacts, and scan artifact contents for secret-like markers.
- Blocking status: blocking
- Disposition: fixed
- Verification notes: `review-packet-diff-gate` now verifies listed artifact digests, detects unlisted artifacts, and scans artifact contents for secret-like markers. Release-readiness tests cover hash mismatch and unlisted-artifact failures. External/source review remains pending.

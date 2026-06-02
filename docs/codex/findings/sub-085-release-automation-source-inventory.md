# SUB-085 Release Automation Source Inventory

- Finding ID: SUB-085
- Severity: medium
- Area: release automation/evidence gates
- Affected files/functions: scripts/external_review_dispatch_packets.py; scripts/review_packet_source_pointers.py; docs/codex/review-packet-source-pointers.md; tests/test_release_readiness.py
- Claim being tested: Release-automation handoff artifacts should point reviewers at the scripts that generate, hash, validate, and route review evidence.
- Observed behavior: Internal proxy review found that the release-automation dispatch packet and source-pointer map omitted several central lane scripts: `external_review_dispatch_packets.py`, `reviewer_artifact_manifest.py`, `source_review_transcript_packet.py`, `review_packet_source_pointers.py`, and `v06_lane_status.py`.
- Risk: A source reviewer using the focused packet could miss code that controls dispatch generation, artifact inventories, transcript sections, source-pointer validation, and lane status.
- Recommended fix: Add a release-automation area to the source-pointer map, include the omitted scripts in the release-automation dispatch source list, and pin that inventory in release-readiness tests.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The release-automation dispatch packet now includes the omitted scripts, `review_packet_source_pointers.py` validates a release-automation area, and release-readiness tests assert the inventory. External/source review remains pending.

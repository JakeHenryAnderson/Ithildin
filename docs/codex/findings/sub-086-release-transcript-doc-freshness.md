# SUB-086 Release Transcript Doc Freshness

- Finding ID: SUB-086
- Severity: low
- Area: release automation/evidence gates
- Affected files/functions: docs/codex/source-review-transcript-packet.md; tests/test_release_readiness.py
- Claim being tested: Documentation for the source-review transcript packet should match the generated transcript sections.
- Observed behavior: Internal proxy review found that the transcript generator already produced a dedicated `Release Automation` section, but the documentation's contents list still described only patch apply, filesystem, HTTP fetch, and a combined signed-evidence/policy/MCP/review-console section.
- Risk: Stale docs could cause reviewers to miss or underuse the dedicated release-automation transcript section.
- Recommended fix: Update the transcript-packet documentation to list the release-automation section and assert the wording in release-readiness tests.
- Blocking status: later
- Disposition: fixed
- Verification notes: `source-review-transcript-packet.md` now lists release automation as a generated transcript section, and `test_source_review_transcript_packet_is_wired` asserts the documentation remains aligned. External/source review remains pending.

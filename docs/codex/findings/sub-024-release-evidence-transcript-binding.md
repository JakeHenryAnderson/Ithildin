# SUB-024 Release Evidence Transcript Binding

- Finding ID: SUB-024
- Severity: medium
- Area: release automation
- Affected files/functions: scripts/release_evidence.py; validate_release_evidence_snapshot; _validate_release_check_transcript
- Claim being tested: release evidence claiming a passing attached release-check transcript should bind that claim to a readable same-commit transcript.
- Observed behavior: Release evidence validation checked the metadata shape but did not require a passing transcript claim to point to an existing transcript from the same commit.
- Risk: A review packet could claim a passing release gate without carrying the transcript needed to verify the claim.
- Recommended fix: Validate transcript existence, status, same-commit binding, path readability, and command return code when the attached transcript is marked passed.
- Blocking status: later
- Disposition: fixed
- Verification notes: Release evidence schema validation now rejects passing transcript claims without a readable transcript, same commit, or successful return code marker. Tests cover attached transcript metadata and minimal no-transcript snapshots. External/source review remains pending.

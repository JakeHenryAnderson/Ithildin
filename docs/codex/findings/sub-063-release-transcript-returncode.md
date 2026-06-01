# SUB-063 Release Transcript Returncode

- Finding ID: SUB-063
- Severity: low
- Area: release evidence validation
- Affected files/functions: scripts/release_evidence.py; tests/test_release_readiness.py
- Claim being tested: Release evidence should not accept a claimed passing transcript without explicit successful return-code evidence.
- Observed behavior: Internal proxy review found that a transcript containing the word `passed` could satisfy release evidence validation without an explicit `returncode=0` marker.
- Risk: A malformed or hand-edited transcript could be mistaken for a successful release gate.
- Recommended fix: Require readable same-commit transcripts with explicit `returncode=0` for claimed passing release-check evidence.
- Blocking status: later
- Disposition: fixed
- Verification notes: Release evidence validation now requires `returncode=0` in passing transcripts, and tests reject passing transcripts without it. External/source review remains pending.

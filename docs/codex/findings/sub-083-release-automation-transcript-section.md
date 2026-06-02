# SUB-083 Release Automation Transcript Section

- Finding ID: SUB-083
- Severity: low
- Area: release automation/evidence gates
- Affected files/functions: scripts/source_review_transcript_packet.py; tests/test_release_readiness.py
- Claim being tested: The source-review transcript skeleton should provide a dedicated place for release-automation reviewer notes.
- Observed behavior: The generated transcript packet had sections for patch apply, filesystem, HTTP fetch, and a combined signed-evidence/policy/MCP/review-console section, but not a dedicated release-automation section.
- Risk: Release/evidence automation review could be recorded inconsistently or merged into unrelated transcript sections.
- Recommended fix: Add a `Release Automation` transcript section naming the relevant evidence inputs: release evidence, redaction scan, artifact hashes, external response normalization, closure/capability gates, and dispatch packets.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The source-review transcript packet now includes a dedicated Release Automation section with required evidence inputs, and release-readiness tests assert the section remains generated. External/source review remains pending.

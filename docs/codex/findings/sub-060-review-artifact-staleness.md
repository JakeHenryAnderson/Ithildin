# SUB-060 Review Artifact Staleness

- Finding ID: SUB-060
- Severity: medium
- Area: review packet automation
- Affected files/functions: scripts/review_packet_bundle.py; Makefile review-candidate flow
- Claim being tested: Generated review bundles should be refreshed after remediation before external handoff.
- Observed behavior: Internal proxy review noted that generated review artifacts can become stale relative to HEAD after source or evidence changes.
- Risk: GPT 5.5 Pro or an external reviewer could receive an internally inconsistent packet.
- Recommended fix: Regenerate review-candidate artifacts after remediation and make generated packet metadata include the latest evidence and transcripts.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The review-candidate flow remains the required handoff gate, and final verification regenerates bundles after remediation. External/source review remains pending.

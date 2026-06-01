# SUB-061 Signed Demo Verification Transcript

- Finding ID: SUB-061
- Severity: medium
- Area: signed evidence review bundle
- Affected files/functions: scripts/review_packet_bundle.py; scripts/signed_evidence_demo_verify.py
- Claim being tested: The review bundle should carry durable evidence that the synthetic signed-evidence demo was verified.
- Observed behavior: Internal proxy review found that the signed-evidence demo summary could be copied into the packet without a durable verification transcript/result.
- Risk: Reviewers could see the demo summary but not know whether the verifier succeeded against the copied state.
- Recommended fix: Copy or generate a signed-evidence demo verification JSON and transcript in the review packet and hash both artifacts.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Review bundle generation now includes `signed-evidence-demo-verify.json` plus transcript metadata when the demo summary is present. Tests assert both artifacts are included and hashed. External/source review remains pending.

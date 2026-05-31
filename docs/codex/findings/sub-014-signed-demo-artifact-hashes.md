# SUB-014 Signed Demo Artifact Hashes

- Finding ID: SUB-014
- Severity: low
- Area: signed evidence demo
- Affected files/functions: scripts/signed_evidence_demo_verify.py; verify_demo
- Claim being tested: the synthetic locally signed evidence demo verifier should check the summary artifact hashes it reports to reviewers.
- Observed behavior: The verifier checked cryptographic verification outcomes but ignored `summary.json` artifact paths, byte counts, and SHA-256 values.
- Risk: A stale or confused demo summary could pass verification while the attached artifact metadata no longer matched the generated files.
- Recommended fix: Recompute and compare every recorded demo artifact path, byte count, and SHA-256 digest, and reject paths outside the demo root.
- Blocking status: later
- Disposition: fixed
- Verification notes: The standalone verifier now checks artifact metadata against files under the demo root and rejects digest mismatches. Tests cover tampered artifact digest metadata. External/source review remains pending.

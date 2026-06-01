# SUB-057 Signed Demo Custom Lock Path

- Finding ID: SUB-057
- Severity: low
- Area: signed evidence demo
- Affected files/functions: scripts/signed_evidence_demo.py; scripts/signed_evidence_demo_verify.py
- Claim being tested: Signed evidence demo verification should verify the lock file that the demo actually signed.
- Observed behavior: Internal proxy review found that `signed_evidence_demo.py --lock-path` could sign a custom lock path while the verifier used the default `tool-manifests.lock.json`.
- Risk: Demo verification could pass against the wrong lock path and weaken reviewer confidence in the fixture evidence.
- Recommended fix: Record the signed lock path in demo summary metadata and have the verifier use that path.
- Blocking status: later
- Disposition: fixed
- Verification notes: The demo summary now records `manifest_lock.lock_path`, and the verifier uses it when checking the signature. Tests cover custom lock-path verification. External/source review remains pending.

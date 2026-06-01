# SUB-055 System Status Signature Startup Evidence

- Finding ID: SUB-055
- Severity: medium
- Area: system status trust evidence
- Affected files/functions: apps/api/src/ithildin_api/app.py; create_app; system_status
- Claim being tested: `/system/status` should distinguish startup verification evidence from mutable current filesystem evidence.
- Observed behavior: Internal proxy review found that system status recomputed manifest-lock signature evidence from current files without exposing what was verified at startup.
- Risk: Operators could miss post-startup drift in signature, lock, or public-key files.
- Recommended fix: Persist startup manifest-lock signature status in app state and report both startup and current status with a drift indicator.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: App startup now records `manifest_lock_signature_startup`; `/system/status` reports startup status, current status, and `signature_drift`. External/source review remains pending.

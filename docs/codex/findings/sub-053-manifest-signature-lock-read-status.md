# SUB-053 Manifest Signature Lock Read Status

- Finding ID: SUB-053
- Severity: medium
- Area: signed manifest lock verification
- Affected files/functions: apps/api/src/ithildin_api/manifest_lock.py; verify_manifest_lock_signature; manifest_lock_signature_status
- Claim being tested: Optional manifest-lock signature status must report invalid evidence without leaking exceptions out of status paths.
- Observed behavior: Internal proxy review found that lock-read failures raised base `ManifestLockError` outside the verifier's status result path.
- Risk: Optional signed-lock status could fail noisily instead of reporting unsigned/unverified evidence, and release-evidence generation could become brittle.
- Recommended fix: Catch all manifest-lock verification errors in signature verification status paths and return secret-free invalid evidence.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `verify_manifest_lock_signature` now catches `ManifestLockError` and returns invalid status. Tests cover a missing lock path producing invalid status rather than an exception. External/source review remains pending.

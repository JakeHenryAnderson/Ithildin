# SUB-056 Manifest Signature Untrusted Key ID

- Finding ID: SUB-056
- Severity: low
- Area: signed manifest lock status
- Affected files/functions: apps/api/src/ithildin_api/manifest_lock.py; verify_manifest_lock_signature
- Claim being tested: Failed manifest-lock signature status should not surface untrusted key IDs as if they were verified evidence.
- Observed behavior: Internal proxy review found that failed signature verification could still return a key ID parsed from the untrusted bundle.
- Risk: Status output could make unverified signature material look like trustworthy key evidence.
- Recommended fix: Only return key IDs from manifest-lock signature verification when the signature is valid.
- Blocking status: later
- Disposition: fixed
- Verification notes: Invalid manifest-lock signature verification now returns `key_id=None`; status only carries a key ID on valid verification. External/source review remains pending.

# SUB-051 Signed Export Non-Object Bundle

- Finding ID: SUB-051
- Severity: low
- Area: signed audit export verification
- Affected files/functions: packages/audit-core/src/ithildin_audit_core/signing.py; verify_signed_audit_export_bundle; scripts/audit_signing.py
- Claim being tested: Offline verification should return structured invalid results for malformed bundle inputs.
- Observed behavior: Internal proxy review found that non-object JSON bundles could crash verification paths instead of returning a safe invalid result.
- Risk: Malformed reviewer artifacts could produce confusing tracebacks rather than deterministic evidence failure.
- Recommended fix: Require signed export bundles to be JSON objects at API and CLI verification boundaries.
- Blocking status: later
- Disposition: fixed
- Verification notes: `verify_signed_audit_export_bundle` now accepts `object` input and returns `valid=false` for non-object bundles; the CLI rejects non-object JSON with a safe error. External/source review remains pending.

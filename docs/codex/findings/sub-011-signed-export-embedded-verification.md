# SUB-011 Signed Export Embedded Verification

- Finding ID: SUB-011
- Severity: high
- Area: audit/signed evidence
- Affected files/functions: packages/audit-core/src/ithildin_audit_core/signing.py; verify_signed_audit_export_bundle
- Claim being tested: signed audit export verification should only be top-level valid when both the signature and embedded audit chain verify.
- Observed behavior: `verify_signed_audit_export_bundle` could return `valid: true` while `audit_verification.valid` was false.
- Risk: Offline verification could be interpreted as evidence validity even when the signed bundle contained a broken audit chain.
- Recommended fix: Make top-level signed-bundle validity require a valid embedded audit verification result.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Signed bundle verification now returns invalid with `audit verification failed` when embedded audit verification fails. The regression test was updated to require top-level invalid status for this case. External/source review remains pending.

# SUB-049 Signed Export Metadata Validation

- Finding ID: SUB-049
- Severity: medium
- Area: audit/signed evidence
- Affected files/functions: packages/audit-core/src/ithildin_audit_core/signing.py; verify_signed_audit_export_bundle; _metadata_matches_verification
- Claim being tested: Signed export verification must reject re-signed bundles whose nested export metadata no longer matches the exported event payload.
- Observed behavior: Internal proxy review found that a malicious local signer could alter nested export metadata fields not compared by verification, then re-sign the bundle.
- Risk: Offline verification could accept confusing metadata even though the signed event payload digest was intact.
- Recommended fix: Treat core nested export metadata as part of the evidence contract and require it to match the exported event verification result.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `_metadata_matches_verification` now checks export bundle type, format version, generated timestamp shape, diagnostics object, event count, head hash, and verification payload. Tests re-sign malformed nested metadata and expect verification failure. External/source review remains pending.

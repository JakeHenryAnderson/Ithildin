# SUB-050 Signed Export Trusted Key Docs

- Finding ID: SUB-050
- Severity: low
- Area: signed audit export operator docs
- Affected files/functions: docs/codex/signed-audit-exports.md; scripts/audit_signing.py
- Claim being tested: Offline signed export verification must be described as trusted-public-key verification, not embedded-key self-verification.
- Observed behavior: Internal proxy review found documentation and CLI behavior that could imply the embedded public key alone was sufficient verification evidence.
- Risk: Operators could mistake a self-contained signature bundle for an external trust-root check.
- Recommended fix: Require an explicit trusted public key for verification and clarify that embedded public-key metadata is not a trust root.
- Blocking status: later
- Disposition: fixed
- Verification notes: The CLI now requires `--public-key` for signed export verification, and the guide states that embedded public keys are metadata only. External/source review remains pending.

# EXT-PROD-IAM-STORAGE-001 Exact Issuer Binding

- Finding ID: EXT-PROD-IAM-STORAGE-001
- Severity: medium
- Area: production-identity-storage
- Affected files/functions: `docs/codex/production-identity-storage-architecture.md`; `scripts/production_identity_storage_architecture_check.py`
- Claim being tested: Future OIDC subject mappings must not merge equivalent-looking but distinct issuer identifiers.
- Observed behavior: The planning contract used security-significant `normalized issuer` wording without defining an exact comparison rule.
- Risk: A later implementation could alias issuer forms across provider configurations and bind a subject to the wrong authority domain.
- Recommended fix: Bind organization, provider configuration, exact configured/discovery/token issuer, and subject; reject alternate forms and keep normalization display-only.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The architecture contract now requires exact issuer equality and rejects case, slash, userinfo, Unicode/punycode, DNS alias, and equivalent-looking variants as authority.

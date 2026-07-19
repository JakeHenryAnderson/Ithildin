# EXT-PROD-IAM-STORAGE-002 Safe Session Evidence

- Finding ID: EXT-PROD-IAM-STORAGE-002
- Severity: medium
- Area: production-identity-storage
- Affected files/functions: `docs/codex/production-identity-storage-architecture.md` Evidence Contract; `scripts/production_identity_storage_architecture_check.py`
- Claim being tested: Future identity evidence must remain useful without exposing authentication handles or customer identity data.
- Observed behavior: The evidence allowlist named a session ID and subject/workspace labels without separating audit references from bearer handles and private customer identifiers.
- Risk: A later exporter could leak a cookie handle, session lookup digest, raw subject, or customer display name.
- Recommended fix: Use a random non-authenticating `session_audit_id`, privacy-safe references, and explicit data-class, retention, and redaction rules.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The architecture and embedded contract now distinguish the audit ID from cookie and digest material and forbid raw subject and display-name exports.

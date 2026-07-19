# EXT-PROD-IAM-STORAGE-005 Database Security Profile

- Finding ID: EXT-PROD-IAM-STORAGE-005
- Severity: medium
- Area: production-identity-storage
- Affected files/functions: `docs/codex/production-identity-storage-architecture.md`; `scripts/production_identity_storage_architecture_check.py`
- Claim being tested: PostgreSQL planning must define its transport, identity, role, credential, encryption, backup, and WAL trust boundaries before dependency or implementation decisions.
- Observed behavior: The packet selected PostgreSQL as the candidate backend but left these security controls implicit.
- Risk: A later adapter or deployment plan could centralize durable authority while using weak database identity, overprivileged roles, incomplete recovery data, or ambiguous encryption custody.
- Recommended fix: Freeze TLS server verification, separate least-privilege roles, external credential rotation, pool isolation, online encryption threat model, backup-key separation, encrypted complete WAL, restore verification, and fail-closed dependency handling.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The architecture and embedded contract require the database security profile before `PIS-002`; provider and dependency selection remain unapproved.

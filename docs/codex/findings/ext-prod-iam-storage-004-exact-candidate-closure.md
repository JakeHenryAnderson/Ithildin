# EXT-PROD-IAM-STORAGE-004 Exact Candidate Closure

- Finding ID: EXT-PROD-IAM-STORAGE-004
- Severity: medium
- Area: production-identity-storage
- Affected files/functions: `scripts/production_identity_storage_disposition_closure_check.py`; `scripts/production_identity_storage_response_dry_run.py`; `docs/codex/production-identity-storage-disposition-closure-gate.md`
- Claim being tested: Architecture disposition readiness must be bound to the exact commit and packet the reviewer inspected.
- Observed behavior: The closure gate accepted any syntactically valid packet digest and did not validate the reviewed commit.
- Risk: Stale or unrelated review evidence could be presented as readiness for a different architecture candidate.
- Recommended fix: Require a full reviewed commit equal to the packet prompt and a reviewed packet hash equal to the packet manifest digest; reject well-formed mismatches.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The closure gate computes both expected bindings locally, and the dry run covers malformed and well-formed wrong commit/hash values.

# EXT-PROD-IAM-STORAGE-003 Normalized Disposition

- Finding ID: EXT-PROD-IAM-STORAGE-003
- Severity: medium
- Area: production-identity-storage
- Affected files/functions: `scripts/external_response_normalize.py`; `scripts/production_identity_storage_response_dry_run.py`; `docs/codex/production-identity-storage-external-response-intake.md`
- Claim being tested: The documented normalization command must be able to produce every field the closure gate requires.
- Observed behavior: Dry-run fixtures hand-built `disposition_outcome`, but the normalizer could not emit it.
- Risk: Operators would have to edit normalized evidence manually, weakening reproducibility and provenance.
- Recommended fix: Add a typed disposition argument that must agree with an explicit standalone declaration in the raw response and cover the real path with an integration test.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: The normalizer now validates and emits the typed outcome; the PIS dry run passes normalized output through the real closure gate.

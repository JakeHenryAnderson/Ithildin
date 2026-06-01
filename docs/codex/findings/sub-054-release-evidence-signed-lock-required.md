# SUB-054 Release Evidence Signed Lock Required

- Finding ID: SUB-054
- Severity: high
- Area: release evidence
- Affected files/functions: scripts/release_evidence.py; ToolRegistry.load; validate_release_evidence_snapshot
- Claim being tested: Release evidence must fail closed when signed manifest-lock enforcement is configured but not verified.
- Observed behavior: Internal proxy review found that release evidence loaded the registry with only hash-lock enforcement and schema validation did not reject `signature.required=true` with `verified=false`.
- Risk: A review packet could claim signed-lock enforcement was required while attaching evidence where no valid signature was verified.
- Recommended fix: Bind registry loading and release evidence validation to signed-lock configuration and reject required-but-unverified signed lock evidence.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `release_evidence.py` now passes signed-lock settings to registry loading and validates signed-lock status. Tests cover required unverified signed lock rejection. External/source review remains pending.

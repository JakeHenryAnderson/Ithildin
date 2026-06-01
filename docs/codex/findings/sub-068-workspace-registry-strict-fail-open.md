# SUB-068 Workspace Registry Strict Fail-Open

- Finding ID: SUB-068
- Severity: high
- Area: registry fail-closed behavior
- Affected files/functions: apps/api/src/ithildin_api/workspaces.py; tests/test_workspaces.py; tests/test_api_service.py
- Claim being tested: Strict workspace-registry mode should fail closed when the configured registry file is missing.
- Observed behavior: Internal proxy review found that a missing default-like registry path could silently fall back to an overridden single workspace root even when strict mode was enabled.
- Risk: Runtime could bypass the committed workspace registry and operate with unreviewed workspace configuration.
- Recommended fix: Remove the strict-mode fallback bypass; allow fallback only when `require_registry` is false; update tests/helpers to use explicit temporary registries.
- Blocking status: blocking
- Disposition: fixed
- Verification notes: `WorkspaceRegistry.load` now raises on any missing strict registry and only generates fallback records when strict mode is disabled. Tests cover the strict default-like path case. External/source review remains pending.

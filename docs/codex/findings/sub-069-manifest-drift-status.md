# SUB-069 Manifest Drift Status

- Finding ID: SUB-069
- Severity: medium
- Area: registry fail-closed behavior
- Affected files/functions: apps/api/src/ithildin_api/app.py; tests/test_api_service.py
- Claim being tested: Runtime trust status should report whether the current manifest files still match the enforced manifest lock.
- Observed behavior: Internal proxy review found that startup enforced manifest locks, but `/system/status` did not report post-startup manifest drift.
- Risk: A reviewer or local operator could miss manifest file drift after startup when inspecting trust posture.
- Recommended fix: Add a current manifest-lock verification status to `/system/status` that safely reports drift without crashing the status endpoint.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `/system/status.manifest_lock.current` now reports required/verified/error, and a test mutates a manifest after startup to verify hash mismatch reporting. External/source review remains pending.

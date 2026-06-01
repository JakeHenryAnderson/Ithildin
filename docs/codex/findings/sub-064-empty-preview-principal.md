# SUB-064 Empty Preview Principal

- Finding ID: SUB-064
- Severity: medium
- Area: policy preview/runtime parity
- Affected files/functions: apps/api/src/ithildin_api/policy_preview.py; policies/tests/parity.yaml; tests/test_api_service.py; tests/test_policy_parity.py
- Claim being tested: `/policy/preview` should default to the local admin principal only when the caller omits `principal`, not when the caller supplies an empty object.
- Observed behavior: Internal proxy review found that `principal: {}` was treated like an omitted principal and became `admin:local-ui`.
- Risk: A malformed or stripped principal field could produce an overly privileged preview result that does not reflect trusted-principal runtime behavior.
- Recommended fix: Default only on `principal is None`; treat an explicit empty principal as a pre-policy denial and add parity coverage.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Policy preview now distinguishes omitted principal from an explicit empty object. Tests cover empty-principal preview denial and parity fixture `empty_principal_preview_matches_runtime`. External/source review remains pending.

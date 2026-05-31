# SUB-017 Policy Parity Resource Scope

- Finding ID: SUB-017
- Severity: medium
- Area: policy parity harness
- Affected files/functions: apps/api/src/ithildin_api/policy_parity.py; PolicyParityCase; _PolicyParityHarness.run_case; policies/tests/parity.yaml
- Claim being tested: policy parity fixtures should catch executor-denial masking of preview/runtime policy false positives.
- Observed behavior: The parity harness compared decisions and evidence but did not require resource-scope expectations for denied filesystem scope cases.
- Risk: A future regression could allow preview/runtime policy evidence to mark out-of-scope resources as allowed while the executor denies later.
- Recommended fix: Add explicit resource type/scope expectations to parity cases and include an out-of-scope filesystem fixture.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Policy parity fixtures now include an out-of-scope filesystem denial case plus resource type/scope expectations. The harness builds a fixture read executor so preview and runtime use the same path-scope contract. `make policy-parity` reports 8/8 passing. External/source review remains pending.

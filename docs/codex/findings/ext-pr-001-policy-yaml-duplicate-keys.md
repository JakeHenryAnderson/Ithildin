# EXT-PR-001 Policy YAML Duplicate Keys

- Finding ID: EXT-PR-001
- Severity: medium
- Area: policy-registry
- Affected files/functions: packages/policy-core/src/ithildin_policy_core/evaluator.py; PolicyEvaluator.load; apps/api/src/ithildin_api/policy_testing.py; load_policy_tests; tests/test_policy_evaluator.py; tests/test_policy_test_harness.py
- Claim being tested: trusted YAML policy documents and policy fixtures should fail closed on duplicate mapping keys rather than accepting parser overwrite behavior.
- Observed behavior: Internal source review found that runtime YAML policies and offline policy fixture files were loaded with `yaml.safe_load`, so duplicate keys were silently accepted with the later value.
- Risk: A reviewed policy or policy fixture could display one value while runtime or release gates used a later duplicate value, weakening policy review, policy fixture evidence, and the duplicate-key fail-closed contract.
- Recommended fix: Load runtime YAML policies and policy fixture files through duplicate-key rejecting YAML loaders, and add top-level and nested duplicate-key regression tests for both policy docs and fixture docs.
- Blocking status: blocking
- Disposition: fixed
- Verification notes: `PolicyEvaluator.load` now uses a duplicate-key rejecting SafeLoader in policy-core, and `load_policy_tests` now uses `safe_load_no_duplicate_keys`. Regression coverage includes top-level and nested duplicate-key rejection for policy docs and policy fixtures. Verified with `uv run pytest tests/test_policy_evaluator.py tests/test_policy_test_harness.py tests/test_policy_parity.py -q`, `make policy-test`, `make policy-parity`, `make test`, `make lint`, `make typecheck`, and `make release-check`.

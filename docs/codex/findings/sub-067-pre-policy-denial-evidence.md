# SUB-067 Pre-Policy Denial Evidence

- Finding ID: SUB-067
- Severity: low
- Area: policy preview/runtime parity
- Affected files/functions: apps/api/src/ithildin_api/policy_preview.py; tests/test_api_service.py
- Claim being tested: Preview denials before policy evaluation should not look like policy-engine decisions.
- Observed behavior: Internal proxy review found that unknown tools, invalid arguments, and principal/visibility denials still carried policy-version-like evidence.
- Risk: Reviewers could misread registry, argument-validation, or identity denials as evaluated policy decisions.
- Recommended fix: Add explicit `policy_evaluated` and `deny_source` fields and set `policy_version` to null for pre-policy preview denials.
- Blocking status: later
- Disposition: fixed
- Verification notes: Pre-policy preview denials now report `policy_evaluated: false`, a `deny_source`, no decision evidence, and null `policy_version`. External/source review remains pending.

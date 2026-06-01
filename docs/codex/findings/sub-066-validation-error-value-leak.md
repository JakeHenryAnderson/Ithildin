# SUB-066 Validation Error Value Leak

- Finding ID: SUB-066
- Severity: medium
- Area: policy preview/runtime parity
- Affected files/functions: apps/api/src/ithildin_api/schema_validation.py; apps/api/src/ithildin_api/policy_preview.py; apps/api/src/ithildin_api/tool_calls.py; tests/test_api_service.py; tests/test_governed_tool_calls.py
- Claim being tested: Schema validation failures should not echo caller-supplied argument values into API responses or audit metadata.
- Observed behavior: Internal proxy review found that raw JSON Schema exception messages could include invalid instance values.
- Risk: Secret-like input values submitted in invalid arguments could leak through preview responses or audit records.
- Recommended fix: Replace raw validation messages with deterministic path/schema summaries that omit instance values.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `safe_json_schema_error` now reports only instance path, validator, and schema path. Preview and governed-call tests assert secret values are absent from responses and audit metadata. External/source review remains pending.

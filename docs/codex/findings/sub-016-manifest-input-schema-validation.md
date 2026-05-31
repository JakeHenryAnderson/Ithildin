# SUB-016 Manifest Input Schema Validation

- Finding ID: SUB-016
- Severity: medium
- Area: tool registry
- Affected files/functions: apps/api/src/ithildin_api/registry.py; _load_manifest; apps/api/src/ithildin_api/policy_preview.py; PolicyPreviewService.preview; apps/api/src/ithildin_api/tool_calls.py; GovernedToolCallService.call_tool
- Claim being tested: trusted manifests should fail closed at load time when `input_schema` is not a valid JSON Schema.
- Observed behavior: Manifest `input_schema` objects were accepted by Pydantic but not checked as JSON Schema until request-time validation.
- Risk: Malformed trusted manifests could cause request-time `SchemaError` failures instead of fail-closed startup behavior.
- Recommended fix: Validate manifest `input_schema` with the JSON Schema validator at registry load and defensively handle request-time schema errors as safe denials.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Registry load now calls `Draft202012Validator.check_schema` and raises `InvalidToolManifest` for malformed input schemas. Preview and governed-call schema validation catch `SchemaError` defensively. Registry tests cover malformed JSON Schema failure. External/source review remains pending.

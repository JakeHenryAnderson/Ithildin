# SUB-041 HTTP Preview Schema Resource Order

- Finding ID: SUB-041
- Severity: low
- Area: policy preview/runtime parity
- Affected files/functions: apps/api/src/ithildin_api/policy_preview.py; PolicyPreviewService.preview; policies/tests/parity.yaml; tests/test_policy_parity.py
- Claim being tested: Policy preview should mirror the governed runtime order for schema validation and resource construction.
- Observed behavior: Internal proxy review found that policy preview constructed an HTTP network resource before JSON Schema validation, while runtime validates arguments before resource construction. Schema-invalid calls with extra HTTP fields could be denied while still showing an in-scope network resource.
- Risk: Reviewers could see misleading resource evidence for calls that runtime would reject before resource derivation.
- Recommended fix: Validate tool arguments before preview resource construction and add an invalid `http.fetch` parity fixture.
- Blocking status: later
- Disposition: fixed
- Verification notes: `PolicyPreviewService.preview` now returns a generic out-of-scope tool-call resource for schema-invalid arguments. The committed parity fixtures include schema-invalid `http.fetch`, and policy parity reports 9 passing cases. External/source review remains pending.

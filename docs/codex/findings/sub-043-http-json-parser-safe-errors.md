# SUB-043 HTTP JSON Parser Safe Errors

- Finding ID: SUB-043
- Severity: medium
- Area: http.fetch response processing
- Affected files/functions: apps/api/src/ithildin_api/http_tools.py; HttpFetchExecutor._result_from_response
- Claim being tested: Optional JSON response parsing should not let parser edge failures escape the safe, bounded HTTP result path.
- Observed behavior: Internal proxy review found that bounded `application/json` bodies could still cause raw parser exceptions such as `RecursionError` or integer-limit `ValueError`, while only `JSONDecodeError` was ignored.
- Risk: A remote response could turn a bounded fetch into a raw exception path rather than a safe result or safe denial.
- Recommended fix: Treat optional JSON parser failures as non-fatal and avoid echoing parser details.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Optional JSON parsing now ignores `JSONDecodeError`, `ValueError`, and `RecursionError`, returning bounded `body_text` without `body_json` when parsing fails. Tests inject a parser recursion failure and verify no raw exception escapes. External/source review remains pending.

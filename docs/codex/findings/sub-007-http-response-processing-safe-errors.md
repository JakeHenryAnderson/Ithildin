# SUB-007 HTTP Response Processing Safe Errors

- Finding ID: SUB-007
- Severity: medium
- Area: http.fetch safe error handling
- Affected files/functions: apps/api/src/ithildin_api/http_tools.py; HttpFetchExecutor.fetch; HttpFetchExecutor._result_from_response; _read_bounded
- Claim being tested: `http.fetch` returns safe bounded errors for transport and response-processing failures without leaking remote or backend details.
- Observed behavior: The existing executor wrapped open-time errors, but response body read failures and unknown charset decoding failures could raise raw exceptions after the response was opened.
- Risk: Raw exception details from a response object, transport, or decoder could leak into governed tool errors and audit metadata.
- Recommended fix: Wrap post-open response processing in safe exception translation, close responses on all result paths, and test read-time and charset failures.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `HttpFetchExecutor` now routes response handling through `_safe_result_from_response`, translates read/decode/HTTP exceptions to `HTTP fetch failed safely`, and closes responses after processing. Tests cover read-time timeout details and unknown charset details without leakage. External/source review remains pending.

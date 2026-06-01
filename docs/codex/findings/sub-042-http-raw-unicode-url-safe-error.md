# SUB-042 HTTP Raw Unicode URL Safe Error

- Finding ID: SUB-042
- Severity: medium
- Area: http.fetch URL and transport safety
- Affected files/functions: apps/api/src/ithildin_api/http_tools.py; parse_http_url; HttpFetchExecutor.fetch; _PinnedHttpOpener.open_pinned
- Claim being tested: `http.fetch` should reject or safely handle URL forms that the stdlib transport cannot encode without leaking raw backend exceptions.
- Observed behavior: Internal proxy review found that raw non-ASCII path or query characters could pass URL parsing and allowlist checks, then trigger a raw `UnicodeEncodeError` during transport handling.
- Risk: A raw transport or encoding exception could bypass normal `HttpFetchError` handling, producing unsafe caller errors or incomplete failure audit behavior.
- Recommended fix: Reject raw non-ASCII path/query input before opening a request and translate transport-time Unicode failures into the standard safe HTTP failure.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `parse_http_url` now rejects raw non-ASCII path/query characters, and open-time `UnicodeError` is translated to `HTTP fetch failed safely`. Tests cover raw Unicode path/query denial before open and transport Unicode errors without leaking backend detail. External/source review remains pending.

# SUB-008 HTTP Explicit Port Normalization

- Finding ID: SUB-008
- Severity: low
- Area: http.fetch URL and allowlist canonicalization
- Affected files/functions: apps/api/src/ithildin_api/http_tools.py; parse_http_url; _parse_allowlist_entry; _port_from_split
- Claim being tested: exact allowlist matching does not silently normalize malformed or invalid explicit ports.
- Observed behavior: Explicit zero ports and empty port syntax could be treated like a missing port because parsed ports were combined with default ports using truthiness.
- Risk: Ambiguous URL or allowlist syntax could be accepted in ways that are surprising to reviewers and operators.
- Recommended fix: Distinguish missing ports from explicit invalid ports, reject port zero and empty explicit ports, and add corpus/regression coverage.
- Blocking status: later
- Disposition: fixed
- Verification notes: URL parsing and allowlist parsing now reject explicit empty ports and ports less than or equal to zero. Tests and corpus cases cover `:0` and empty `:` ports. External/source review remains pending.

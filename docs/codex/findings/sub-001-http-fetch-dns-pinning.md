# SUB-001 HTTP Fetch Connect-Time DNS Pinning

- Finding ID: SUB-001
- Severity: high
- Area: http.fetch SSRF and DNS/IP validation
- Affected files/functions: apps/api/src/ithildin_api/http_tools.py; HttpFetchExecutor.fetch; HttpFetchExecutor._ensure_allowed_destination
- Claim being tested: http.fetch blocks private or otherwise non-global destinations even when DNS changes around request execution.
- Observed behavior: The executor resolves and validates the normalized URL twice before calling urllib opener.open, but the default stdlib opener performs its own socket connection afterward. A hostile resolver could return allowed public IPs during validation and a blocked/private IP during the actual connect.
- Risk: The current local-preview implementation reduces redirect and DNS rebinding risk but does not prove connect-time DNS pinning for the default transport.
- Recommended fix: Add a transport that connects to a validated IP while preserving Host/SNI semantics, or narrow the runtime claim and keep this as an explicit external-review blocker before broader network capability.
- Blocking status: should-fix
- Disposition: deferred
- Verification notes: Recorded during Wave 3 internal AI/subagent review. Contract wording now states pre-connect validation and does not claim socket-level DNS pinning.

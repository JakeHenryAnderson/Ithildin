# SUB-001 HTTP Fetch Connect-Time DNS Pinning

- Finding ID: SUB-001
- Severity: high
- Area: http.fetch SSRF and DNS/IP validation
- Affected files/functions: apps/api/src/ithildin_api/http_tools.py; HttpFetchExecutor.fetch; HttpFetchExecutor._ensure_allowed_destination
- Claim being tested: http.fetch blocks private or otherwise non-global destinations even when DNS changes around request execution.
- Observed behavior: The original executor resolved and validated the normalized URL twice before calling `urllib` `opener.open`, but the default stdlib opener performed its own socket connection afterward. A hostile resolver could return allowed public IPs during validation and a blocked/private IP during the actual connect.
- Risk: Without a pinned default transport, the local-preview implementation reduced redirect and DNS rebinding risk but did not prove connect-time DNS pinning for the default transport.
- Recommended fix: Add a transport that connects to a validated IP while preserving Host/SNI semantics, or narrow the runtime claim and keep this as an explicit external-review blocker before broader network capability.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: Remediated by replacing the default runtime opener with a pinned stdlib transport that connects to a validated IP while preserving normalized Host and HTTPS SNI/check-hostname semantics. Follow-up hardening now rejects custom transports that do not implement pinned-destination handoff and narrows scheme-less allowlist entries to exact default scheme/port semantics. Tests cover pinned transport handoff, unpinned transport rejection, redirect revalidation on response-status redirects, scheme-less allowlist exactness, and proxy-environment non-use. External/source review remains pending.

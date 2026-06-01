# SUB-040 HTTP Malformed URL Resource Redaction

- Finding ID: SUB-040
- Severity: medium
- Area: http.fetch audit resource evidence
- Affected files/functions: apps/api/src/ithildin_api/http_tools.py; http_resource_from_url; apps/api/src/ithildin_api/tool_calls.py; GovernedToolCallService.call_tool; apps/api/src/ithildin_api/policy_preview.py; PolicyPreviewService.preview
- Claim being tested: Network resource evidence for denied `http.fetch` calls must not persist caller-provided URL secrets.
- Observed behavior: Internal proxy review found that malformed URL parsing failures returned a network resource containing the raw caller URL. Inputs such as a leading-space URL with a query token could be denied but still written into policy/audit metadata or preview output.
- Risk: Query tokens, credentials, or other URL-embedded secrets could be persisted in audit evidence or returned in preview output even though the network call was safely denied.
- Recommended fix: Never store raw malformed URLs in network resources. Store a deterministic hash and safe denial reason instead, and add governed-call and preview tests for malformed URL secrets.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `http_resource_from_url` now records `raw_url_hash` instead of raw `url` on parse errors. Tests cover malformed query-token denial in governed-call audit and policy preview with no raw secret in JSON output. External/source review remains pending.

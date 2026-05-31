# SUB-009 HTTP Audit Query Redaction

- Finding ID: SUB-009
- Severity: medium
- Area: http.fetch audit resource evidence
- Affected files/functions: apps/api/src/ithildin_api/http_tools.py; http_resource_from_url; apps/api/src/ithildin_api/resources.py; GovernedToolCallService._audit_execution
- Claim being tested: audit resource evidence for network tools avoids recording caller-provided URL secrets.
- Observed behavior: The network resource object used by policy and audit included the normalized URL with the full query string.
- Risk: URL query parameters such as tokens could be persisted in policy/execution audit events even when response content redaction works correctly.
- Recommended fix: Keep execution behavior unchanged but represent network audit/policy resources with a queryless normalized URL plus scheme and host metadata.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `http_resource_from_url` now stores a queryless normalized resource URL while execution still fetches the caller-provided URL. Governed-call tests verify audit events do not contain query secrets and keep the sanitized resource URL. External/source review remains pending.

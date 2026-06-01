# MCP Ingress Bypass Audit

Task 098 records the v0.3-prep MCP ingress assurance check.
Task 137 expands the same assurance surface for v0.4 without changing MCP capabilities.

The stdio MCP adapter is intentionally thin. It must not perform independent policy logic, identity
upgrades, execution, approval mutation, or audit rewriting. Its responsibilities are limited to:

- listing registered tools that are marked `mcp.exposed: true`;
- filtering listed tools through the trusted local MCP principal when a principal registry is
  configured;
- forwarding tool calls to `GovernedToolCallService.call_tool`;
- using the fixed local MCP principal `agent:mcp-local`;
- using the fixed local MCP session `mcp-stdio`;
- returning safe MCP `structuredContent` and text content derived from the governed result.

## Bypass Claims Checked

Automated tests cover these ingress claims:

- MCP callers cannot spoof an admin principal through tool arguments; the policy audit event still
  records `agent:mcp-local`.
- MCP callers cannot provide their own session or request ID through tool arguments; policy evidence
  still records `mcp-stdio` and the governed pipeline creates the request ID.
- The MCP adapter call signature accepts only `tool_name` and `arguments`, so caller identity is not
  a public MCP adapter parameter.
- If the configured local principal registry does not contain an active `agent:mcp-local`, MCP tool
  execution fails closed instead of falling back to untrusted caller-supplied roles.
- Unknown tools called through MCP are denied by the shared governed pipeline and produce a
  `policy.evaluated` audit event.
- Registered tools that are not explicitly exposed over MCP are denied before execution and now
  produce safe `policy.evaluated` denial evidence with `deny_source: mcp_exposure`, manifest hash,
  and tool risk metadata.
- `tools/list` returns only MCP-exposed registered tools and respects role visibility for the local
  MCP principal.
- Tool calls route through the same policy, approval, redaction, execution, and audit services used
  by API/internal governed calls.

## Files and Tests

- Adapter implementation: `apps/mcp-server/src/ithildin_mcp_server/server.py`.
- Shared denial evidence: `apps/api/src/ithildin_api/tool_calls.py`.
- Focused tests: `tests/test_mcp_adapter.py`.
- Integration coverage: `tests/test_mcp_integration_flow.py`.
- Required release gate: `make release-check`.

## Non-Goals

This audit does not add a remote MCP transport, OAuth, session authorization, hosted MCP, or new
tool powers. If Ithildin later adds Streamable HTTP MCP or any remote MCP surface, that is a new
trust-boundary task requiring separate authorization, CORS/CSRF/session review, and external source
review.

For v0.4 local-preview, remote MCP remains deferred.

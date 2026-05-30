# MCP Ingress Bypass Audit

Task 098 records the v0.3-prep MCP ingress assurance check.

The stdio MCP adapter is intentionally thin. It must not perform independent policy logic, identity
upgrades, execution, approval mutation, or audit rewriting. Its responsibilities are limited to:

- listing registered tools that are marked `mcp.exposed: true`;
- filtering listed tools through the trusted local MCP principal when a principal registry is
  configured;
- forwarding tool calls to `GovernedToolCallService.call_tool`;
- using the fixed local MCP principal `agent:mcp-local`;
- returning safe MCP `structuredContent` and text content derived from the governed result.

## Bypass Claims Checked

Automated tests cover these ingress claims:

- MCP callers cannot spoof an admin principal through tool arguments; the policy audit event still
  records `agent:mcp-local`.
- Unknown tools called through MCP are denied by the shared governed pipeline and produce a
  `policy.evaluated` audit event.
- `tools/list` returns only MCP-exposed registered tools and respects role visibility for the local
  MCP principal.
- Tool calls route through the same policy, approval, redaction, execution, and audit services used
  by API/internal governed calls.

## Non-Goals

This audit does not add a remote MCP transport, OAuth, session authorization, hosted MCP, or new
tool powers. If Ithildin later adds Streamable HTTP MCP or any remote MCP surface, that is a new
trust-boundary task requiring separate authorization, CORS/CSRF/session review, and external source
review.

For v0.3-prep, remote MCP remains deferred.

# MCP Ingress Source Review Checklist

Task 164 creates the source-review checklist for Ithildin's stdio MCP ingress. Use it with
[source-review-runbook-v2.md](source-review-runbook-v2.md),
[source-file-inspection-packet.md](source-file-inspection-packet.md), and
[mcp-ingress-bypass-audit.md](mcp-ingress-bypass-audit.md).

## Files And Functions

Inspect:

- `apps/mcp-server/src/ithildin_mcp_server/server.py`
  - `IthildinMcpAdapter.list_tools`
  - `IthildinMcpAdapter.call_tool`
  - `create_adapter`
  - `create_mcp_server`
  - `run_stdio_server`
- `apps/api/src/ithildin_api/tool_calls.py`
  - `GovernedToolCallService.call_tool`
  - `GovernedToolCallService.deny_tool_call`
- `apps/api/src/ithildin_api/visibility.py`
- `apps/api/src/ithildin_api/identity.py`
- `tests/test_mcp_adapter.py`
- `tests/test_mcp_integration_flow.py`

## Claims To Test

- MCP remains stdio-only local ingress; remote/network MCP hosting remains deferred.
- The MCP adapter performs translation only and does not implement independent policy, approval,
  execution, redaction, or audit logic.
- `tools/list` uses trusted registry and role-aware visibility for the configured MCP principal.
- `tools/call` routes through `GovernedToolCallService.call_tool` for registry lookup, schema
  validation, principal resolution, resource construction, policy, approval, execution, redaction,
  and audit.
- Registered tools that are not exposed over MCP are denied before execution through the shared
  pre-policy denial audit helper rather than silently inside the adapter.
- Caller-supplied principal/session spoofing cannot override the configured trusted MCP principal.
- Unknown tools, unauthorized principals, invalid arguments, denied policy decisions, and
  approval-required write calls return safe MCP responses.
- MCP responses do not expose file contents, diffs, response bodies, private keys, admin tokens, or
  secrets beyond intended governed tool result content.
- MCP adapter startup enforces manifest lock, principal registry, workspace registry, and configured
  signed-lock requirements consistently with API startup.

## Evidence Commands

```sh
uv run pytest tests/test_mcp_adapter.py tests/test_mcp_integration_flow.py tests/test_governed_tool_calls.py -q
make release-check
```

## Finding Prompts

For every issue, record:

- whether the adapter bypasses the governed pipeline or duplicates policy/execution logic;
- whether principal/session data can be spoofed;
- whether role-filtered visibility differs from runtime call authorization;
- whether the issue requires a remote MCP, production auth, or transport-boundary decision.

## Non-Goals

This checklist does not add remote MCP hosting, OAuth/OIDC, HTTP MCP transport, sessions as auth,
browser automation, shell/Docker/Kubernetes tools, or new governed tool powers.

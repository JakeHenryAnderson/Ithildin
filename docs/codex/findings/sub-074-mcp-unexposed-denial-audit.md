# SUB-074 MCP Unexposed Denial Audit

- Finding ID: SUB-074
- Severity: medium
- Area: MCP ingress
- Affected files/functions: apps/mcp-server/src/ithildin_mcp_server/server.py; apps/api/src/ithildin_api/tool_calls.py; tests/test_mcp_adapter.py
- Claim being tested: MCP ingress guardrail denials should leave the same safe audit evidence operators expect from governed tool calls.
- Observed behavior: registered tools with `mcp.exposed` unset or false were denied by the MCP adapter, but the denial bypassed the shared audit path.
- Risk: an attempted call to a hidden registered tool could be invisible in `policy.evaluated` evidence, weakening operator diagnostics and external review traceability.
- Recommended fix: Add a shared pre-policy denial helper on `GovernedToolCallService` and use it for MCP exposure-gate denials with safe metadata.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `IthildinMcpAdapter.call_tool` now routes unexposed registered-tool denials through `GovernedToolCallService.deny_tool_call`, producing `policy.evaluated` denial evidence with `deny_source: mcp_exposure`, manifest hash, and tool risk metadata. Focused MCP tests assert the safe MCP denial response and matching audit event. External/source review remains pending.

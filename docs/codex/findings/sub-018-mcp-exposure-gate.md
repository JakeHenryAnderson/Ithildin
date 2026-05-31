# SUB-018 MCP Exposure Gate

- Finding ID: SUB-018
- Severity: medium
- Area: MCP ingress
- Affected files/functions: apps/mcp-server/src/ithildin_mcp_server/server.py; IthildinMcpAdapter.call_tool
- Claim being tested: MCP `tools/call` should only dispatch registered tools that are explicitly exposed over MCP.
- Observed behavior: `tools/list` filtered `manifest.mcp.exposed`, but `tools/call` could still route a registered unexposed tool through the governed pipeline.
- Risk: A client that guessed an internal registered tool name could invoke it through MCP despite it being intentionally hidden from MCP listing.
- Recommended fix: Add an MCP call-path exposure gate before governed dispatch.
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: `IthildinMcpAdapter.call_tool` now returns a safe denied MCP result for registered tools whose manifest does not set `mcp.exposed: true`. Tests cover unexposed registered tool denial and preserve audited unknown-tool behavior through the governed service. External/source review remains pending.

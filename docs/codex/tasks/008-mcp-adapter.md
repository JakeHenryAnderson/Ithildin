# Task 008 - MCP Adapter

## Goal

Expose governed tools to MCP-capable clients.

## Scope

- `tools/list`
- `tools/call`
- Map MCP calls to internal tool call API.
- Return safe approval-required responses.

## Acceptance Criteria

- MCP tool list only includes permitted tools.
- MCP calls go through schema validation, policy, approval, execution, and audit.
- Approval-required responses do not leak sensitive parameters.
- Integration tests exercise list, read, and write-requires-approval flows.


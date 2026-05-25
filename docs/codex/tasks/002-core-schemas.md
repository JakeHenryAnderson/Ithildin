# Task 002 - Core Schemas

## Goal

Define typed schemas shared by the API, policy engine, registry, approval workflow, and audit writer.

## Required Models

- `ToolManifest`
- `ToolCallRequest`
- `ToolCallResult`
- `PolicyInput`
- `PolicyDecision`
- `ApprovalRequest`
- `ApprovalDecision`
- `AuditEvent`

## Acceptance Criteria

- Schemas reject unknown fields by default where appropriate.
- Tool input schemas can be represented as JSON Schema.
- Policy decisions are limited to `allow`, `deny`, and `require_approval`.
- Approval records include request hash, expiry, and one-time scope.
- Audit events include previous event hash and event hash fields.
- Unit tests cover invalid types, missing required fields, and extra fields.


# Task 004 - Tool Registry

## Goal

Load trusted tool manifests and expose registered tools to the rest of the system.

## Scope

- Load manifests from `tool-manifests/`.
- Validate manifest schema.
- Expose `GET /tools`.
- Deny unknown or invalid tools.

## Acceptance Criteria

- Invalid manifests fail closed.
- Unknown tool calls are denied and audited.
- Tool list can be filtered by principal.
- Manifest version and hash are available to policy and audit events.


# ADR 0003 - Monorepo for MVP

## Status

Accepted

## Context

The MVP includes API, MCP adapter, UI, policy, audit, schemas, and tool implementations. Splitting these into multiple repositories would add coordination overhead before interfaces stabilize.

## Decision

Use a monorepo for the first 6-12 months.

## Consequences

- Shared schemas and tests can evolve quickly.
- Service boundaries can remain visible without release overhead.
- Repos can be split later if the Tool SDK, cloud control plane, or tool registry need independent release cadence.


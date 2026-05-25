# ADR 0002 - Deny-Default Policy

## Status

Accepted

## Context

LLM-originated tool calls are untrusted proposals. Unknown tools, resources, agents, and parameters must not succeed by accident.

## Decision

The policy engine returns `deny` by default. Only explicit rules can return `allow` or `require_approval`.

## Consequences

- Policy gaps fail closed.
- Tests must assert default deny behavior.
- Tool discovery must filter by principal and policy.
- Invalid policy or policy service unavailability blocks execution.


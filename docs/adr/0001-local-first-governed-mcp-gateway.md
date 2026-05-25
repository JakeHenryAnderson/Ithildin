# ADR 0001 - Local-First Governed MCP Gateway

## Status

Accepted

## Context

The project could become an autonomous agent platform, endpoint automation layer, or cloud governance platform. Those options are too broad for the first release and weaken the security claim.

## Decision

Build Ithildin first as a local-first governed MCP/tool gateway.

Ithildin mediates tool calls from AI agents, evaluates policy, requests approval when required, executes constrained tools, and writes audit evidence.

## Consequences

- The MVP remains feasible for a solo developer.
- The product claim is narrow and testable.
- Direct OS, shell, Docker, cloud, and secret access are outside MVP scope.
- Cloud control plane features are deferred until the local runtime proves governance.


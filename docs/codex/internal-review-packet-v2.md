# Internal Review Packet v2

Task 109 updates `make internal-review-packet` for the v0.3-prep assurance track. The command still
does not call an external model and does not close external/source review. It prepares local prompt
files for high-intelligence internal AI/subagent pressure testing.

## Output

```sh
make internal-review-packet
```

The packet is written under:

```text
var/review-packets/v0.3/internal-ai-review-packet/
```

## Prompt Areas

The v2 packet includes prompts for:

- patch apply approval binding and recovery evidence;
- filesystem workspace and race semantics;
- HTTP fetch SSRF and canonicalization;
- signed evidence and audit integrity;
- policy preview/runtime parity;
- manifest, principal, and workspace fail-closed registries;
- release evidence automation and guardrails;
- MCP ingress thinness;
- review console approval evidence.

Each prompt asks the internal reviewer to inspect concrete files/functions, test specific claims,
record findings with [reviewer-finding-template.md](reviewer-finding-template.md), and recommend a
follow-up task when needed.

## Boundary

Internal AI/subagent review is a continuous proxy and pressure test. It is not independent external validation,
not production readiness, and not permission to add shell, Docker, Kubernetes, browser,
broad network, broad filesystem write, hosted telemetry, production identity, runtime Postgres,
plugin SDK, or remote MCP capabilities.

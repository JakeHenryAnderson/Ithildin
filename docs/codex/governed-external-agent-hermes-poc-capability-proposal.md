# Governed External Agent POC: Hermes Capability Proposal

Status: proposal-only. The current implementation decision is `do_not_expand_runtime`.

Current governed tool count: `24`.

This proposal separates an executable compatibility POC from later external-agent control-plane
capabilities. It does not approve runtime expansion, mission orchestration, remote MCP, dynamic
identity, Docker control, sandbox orchestration, or new governed tools.

## Decision

- **Track A — allowed compatibility evidence:** connect an operator-started pinned Hermes runner to
  the existing stdio adapter and exercise only the current 24 tools against synthetic data.
- **Track B — blocked enforcement and orchestration:** add dynamic identity, a network node, mission
  dispatch, lifecycle control, or stronger non-bypass authority only after the capability expansion
  gate permits a separately reviewed implementation.

Track A adds no governed power. It must state that evidence records `agent:mcp-local` and
`mcp-stdio`, not a production Hermes identity or independently managed mission.

## Track A Allowed Changes

- synthetic fixtures and a pinned Hermes configuration;
- existing stdio MCP client wiring;
- deterministic prompts, expected outcomes, and secret-free transcripts;
- current-tool calls for reads, proposal/apply, HTTP denial, summaries, and bounded artifact writes;
- Command Center labels such as `operator-started`, `observed`, and `local preview`;
- validation of tool count, image digest, fixture hashes, and expected decisions.

## Track A Forbidden Changes

- changing MCP identity/session semantics;
- adding an API, MCP transport, manifest, executor, policy power, or approval mutation path;
- letting Command Center start, stop, pause, cancel, or retry Hermes;
- giving Hermes an admin token; the shared Track A workspace must be labeled as non-enforcing;
- mounting the Docker socket;
- arbitrary shell, browser, HTTP, filesystem write/delete/move, or container control through
  Ithildin;
- claiming all Hermes actions or its process/container were governed;
- real patient, client, employee, credential, or production data.

## Track B Candidate Capabilities

1. External-agent registration with closed runner/model/topology descriptors.
2. Principal-to-workspace assignment enforced by policy and resource derivation.
3. A mission state machine with authoritative-source labels.
4. Authenticated ingress deriving principal/session server-side.
5. A separately packaged enforcement node without Docker lifecycle authority.
6. A runner adapter that does not make runner state equivalent to Gateway truth.
7. Command Center controls that submit only through approved APIs.

The enforcement node is required before `fixture_access_path_constrained` can be claimed. The
current stdio child-process topology cannot establish that claim.

## Required Track B Implementation Gate

Before Track B code, the capability gate must report `capability_expansion_allowed: true`. The
selected slice also needs authority/data-flow contracts, API/schema review, transport authentication
and replay design, least-privilege credentials, policy parity, approval binding, audit/redaction and
reconstruction coverage, failure/restart/partition tests, source review, and an unchanged 24-tool
surface unless a separate tool proposal is approved.

## Required Threat Cases

- prompt injection requests a forbidden tool or out-of-root resource;
- Hermes retries a denial with altered arguments;
- a proposal is applied without approval;
- approval is replayed or used for another request;
- Hermes requests an unapproved network destination;
- Hermes restarts while approval is pending;
- Ithildin restarts after proposal or execution;
- evidence correlation is missing, mismatched, or stale;
- fixture/configuration digests drift;
- prompts, responses, secrets, raw paths, or synthetic record content leak into summaries.

## Explicit Non-Approvals

No production identity, remote MCP hosting, model proxying, chain-of-thought capture, endpoint
monitoring, SIEM integration, hosted telemetry, compliance automation, shell/Docker/browser tools,
broad filesystem powers, real regulated data, or public enterprise-security claims are approved.

## Current Gate Result

As of 2026-07-13:

```text
decision: blocked
capability_expansion_allowed: false
tool_count: 24
runtime_boundary: v0.1 local-preview
blocker: source-review closure matrix still has external_pending rows
```

This permits Track A planning and compatibility evidence only and blocks Track B runtime work.

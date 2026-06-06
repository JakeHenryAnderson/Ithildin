# Sandbox Workspace Boundary Contract

Status: design/evidence contract. This document does not add runtime behavior, API endpoints, MCP
tools, tool manifests, policy rules, executors, sandbox orchestration, SIEM adapters, or new
governed tool powers.

This contract defines how Ithildin should describe an operator-managed sandbox or workspace boundary
without claiming to create or enforce OS isolation itself.

## Boundary Model

Ithildin may record sandbox/workspace posture only when it is supplied by a trusted local
configuration source or a later reviewed integration. The operator or external platform remains
responsible for starting, stopping, isolating, mounting, and supervising any container, VM, or
workspace environment.

Ithildin does not:

- start containers or VMs;
- mount the Docker socket;
- run shell commands;
- manage Kubernetes;
- control browser automation;
- provide kernel isolation;
- prove activity outside Ithildin-mediated tools.

## Future Evidence Shape

Sandbox/workspace posture evidence should be secret-free and may include:

- `sandbox_id`;
- `workspace_id`;
- trusted config source;
- mount/root label;
- support status;
- warning state;
- operator notes;
- timestamp;
- correlation IDs for related run, audit, or export evidence.

This evidence should not include file contents, host secrets, mount credentials, environment
variables, container logs, shell output, prompts, model output, diffs, response bodies, package
script values, dependency names, or raw sensitive paths.

## Supported Current Posture

For local preview, Ithildin supports workspace mediation through the workspace registry and scoped
tools. A sandbox can exist around or beside Ithildin only as operator-managed infrastructure. The
current project does not add a sandbox lifecycle API, process-control endpoint, Docker/Kubernetes
integration, or sandbox repair workflow.

## Future Review Requirement

Any future implementation that records live sandbox posture, consumes sandbox lifecycle events, or
adds sandbox control behavior must receive a separate proposal, implementation plan, source-review
handoff, tests, and explicit implementation decision.

## Relationship To Agent Runs

Agent Run evidence may include an optional `sandbox_id` once supplied by trusted local
configuration. Until then, run timelines remain workspace/principal/session correlation records,
not proof of sandbox isolation.

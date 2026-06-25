# Sandbox/VM Worker Boundary Charter

Status: design-only boundary charter for a future operator-managed sandbox/VM worker proof of
concept.

This charter defines the minimum boundary evidence required before Ithildin may participate in a
real sandbox/VM worker demo. It does not add runtime behavior, API endpoints, MCP tools, tool
manifests, policy rules, executors, sandbox orchestration, VM/container lifecycle management,
Mission Control runtime behavior, local model invocation, SIEM adapters, production identity,
runtime Postgres, hosted telemetry, shell, Docker, Kubernetes, browser automation, arbitrary HTTP,
broad filesystem writes, compliance automation, trusted-host promotion, or new governed tool
powers.

Validate this charter with:

```sh
make sandbox-vm-worker-boundary-charter-check
```

## Role Separation

Future demos must keep these roles separate:

| Role | Allowed responsibility | Explicit non-authority |
| --- | --- | --- |
| Mission Control | Operator-facing mission display, handoff import, labels, warnings, and evidence links | No execution, policy, approval, audit, model, sandbox, or promotion authority |
| Ithildin | Governed tool mediation, policy, approval, redaction, execution, audit, and evidence export for registered tools | No VM/container lifecycle management or OS isolation claim |
| Sandbox/VM layer | Operator-managed isolation, mounts, process/network limits, lifecycle, and cleanup | Does not replace Ithildin policy/audit for mediated actions |
| Local model/client | Proposal generation inside a constrained client/workspace context | No default filesystem authority and no direct host writes |
| Operator | Explicit setup, approval, review, promotion decision, and cleanup | Cannot treat evidence as proof of activity outside mediated paths |

## Required Future Sandbox Profile

Before any real sandbox/VM proof of concept, an operator-supplied profile must define:

- `sandbox_id`;
- `sandbox_label`;
- `workspace_id`;
- `trusted_config_source`;
- sandbox working root label;
- host staging root label;
- approved-output root label, if used;
- support status such as `demo_only`, `unsupported`, or `review_required`;
- warning state such as `not_os_isolation_proof`;
- lifecycle owner;
- cleanup command label or manual cleanup note;
- network posture label;
- mount/root posture label;
- evidence output directory label.

The profile must not contain credentials, host secrets, environment values, private keys, raw
sensitive host paths, shell commands, Docker socket paths, package script values, dependency names,
model prompts, file contents, diffs, response bodies, or sandbox internals.

## Required Future Evidence

A real sandbox/VM worker demo must record secret-free evidence for:

- operator intent and mission ID;
- model/client label and proposal hash;
- sandbox profile ID and workspace ID;
- preflight posture result;
- governed request ID and tool name;
- policy decision hash and matched rules;
- approval ID, if a write is involved;
- artifact label and content hash;
- audit head and event count;
- run ID and correlation IDs;
- cleanup status;
- promotion status, which must remain `not_promoted` until a separate promotion lane exists.

## Minimum Future Negative Cases

Any implementation plan for a real sandbox/VM worker demo must include negative cases for:

- missing sandbox profile;
- unsupported platform;
- unsupported lifecycle owner;
- missing cleanup status;
- sandbox profile claiming Ithildin starts the VM/container;
- profile exposing raw host paths or credentials;
- local model request for shell, Docker, Kubernetes, browser automation, arbitrary HTTP, or broad
  filesystem writes;
- direct host write request without a trusted-host promotion lane;
- artifact hash mismatch between sandbox working area and host staging evidence;
- Mission Control handoff claiming execution, policy, approval, audit, local-model, sandbox, or
  promotion authority;
- any packet that hides required warning chips.

## Current Allowed State

The current project may generate design packets, metadata-only handoffs, observed Ithildin-mediated
Hello World evidence, and sandbox-labeled artifact evidence. It may not start a VM, manage a
container, call a local model, orchestrate a sandbox, promote artifacts to trusted host locations, or
claim OS isolation.

Current proof may say:

> Ithildin can mediate and record evidence for registered actions around an operator-managed
> workspace or sandbox label.

Current proof must not say:

> Ithildin controls the sandbox, proves OS isolation, manages a VM/container, or verifies all agent
> activity outside Ithildin-mediated actions.

## Implementation Gate

Future runtime work must receive a separate proposal, implementation plan, implementation gate,
source-review handoff, negative transcripts, and release/readiness update. Until then,
`make sandbox-vm-worker-boundary-charter-check` must continue reporting:

- runtime changes allowed: `false`;
- Mission Control runtime allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- trusted-host promotion allowed: `false`;
- new power classes allowed: `false`.

# Mission Control Display Integration Proposal

Status: design-only proposal for the next enterprise-readiness runway step.

This proposal generalizes the existing Hello World Mission Control handoff into a future
display/import integration between Mission Control and Ithildin. It does not add runtime behavior,
tool manifests, executors, policy rules, API endpoints, MCP transports, Mission Control execution
behavior, local model invocation, VM/container lifecycle management, sandbox orchestration,
trusted-host promotion, SIEM adapters, production IAM, runtime Postgres, hosted telemetry, shell,
Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes, compliance
automation, or public/security-product claims.

## Goal

Mission Control should be able to display Ithildin evidence as mission context without becoming the
executor, policy authority, approval authority, or audit authority.

The first supported shape should be a file/import contract, not a live integration:

1. Ithildin generates a metadata-only handoff packet.
2. Mission Control imports or links the packet as mission evidence.
3. Mission Control displays labels, hashes, warning chips, and evidence links.
4. Ithildin remains the authoritative governed gateway and evidence source.

## Source Seed

The current seed is:

- [Hello World Mission Control Handoff](hello-world-mission-control-handoff.md)
- generated packet: `var/review-packets/v3/hello-world-mission-control-handoff/`
- check: `make hello-world-mission-control-handoff-check`

That seed demonstrates a metadata-only handoff for `sandbox.artifact.write_text` evidence. The
proposal here does not expand what Mission Control may do; it defines how future Mission Control
display work should be planned and reviewed.

## Proposed Import Fields

Mission Control may display only secret-free fields from an Ithildin handoff packet:

| Field group | Allowed fields | Notes |
| --- | --- | --- |
| Mission identity | mission ID, operator intent label, local-preview status | Labels only; no raw prompts. |
| Agent/client | model/client label, run label, sandbox ID label if present | Labels only; no transcripts by default. |
| Ithildin evidence | run ID, request ID, approval ID, audit head hash, policy hash, manifest hash | Hashes and IDs only. |
| Artifact evidence | artifact label, byte count, SHA-256 hash, output zone label | No file contents or raw host paths. |
| Boundary state | local-preview warning, metadata-only warning, not-promoted state | Warning chips must stay visible. |
| Attachments | relative packet paths, artifact hashes, source packet digest | Import links only; no execution. |

Mission Control must preserve the following hard-coded warning states until a later reviewed lane
changes them:

- Mission Control runtime behavior: `false`.
- local model runtime behavior: `false`.
- real VM/container started: `false`.
- sandbox orchestration performed: `false`.
- shell execution performed: `false`.
- host promotion performed: `false`.

## Proposed Display States

Mission Control may render these display-only states:

- `handoff_imported`: packet was parsed and basic version/hash checks passed.
- `handoff_stale`: packet commit, timestamp, or artifact hashes no longer match operator context.
- `handoff_unsupported`: packet schema or version is not supported.
- `evidence_warning`: required warning chips are missing or incomplete.
- `evidence_linked`: packet remains external evidence and was not executed by Mission Control.

These states are UI/display states only. They do not authorize tool calls, approvals, promotion, or
runtime behavior.

## Negative Cases

Any future implementation must reject or visibly warn on:

- missing local-preview warning state;
- missing metadata-only warning state;
- missing `host_promotion_performed: false`;
- packet version mismatch;
- missing artifact hash manifest;
- mismatched artifact hash;
- stale commit or stale evidence timestamp;
- absolute host paths in display fields;
- raw prompts, file contents, diffs, response bodies, secrets, dependency names, package scripts, or
  raw sandbox internals;
- a packet claiming Mission Control execution, policy authority, approval authority, sandbox/VM
  lifecycle control, or trusted-host promotion.

## Required Before Implementation

A future implementation sprint must add:

- a Mission Control-side import/display contract;
- an Ithildin-side handoff schema contract;
- schema fixtures for accepted and rejected handoff packets;
- negative transcripts for stale, mismatched, unsupported, and overclaiming packets;
- source-review handoff covering both repositories if both are changed;
- release/readiness gates proving no new Ithildin tool powers were added.

## Explicit Non-Goals

This proposal does not approve:

- Mission Control execution authority;
- Mission Control policy authority;
- Mission Control approval authority;
- local model invocation;
- VM/container lifecycle control;
- sandbox orchestration;
- trusted-host promotion;
- shell execution;
- direct filesystem writes;
- API callbacks from Mission Control into Ithildin;
- remote MCP;
- SIEM adapters;
- production IAM;
- compliance automation;
- public/security-product positioning.

## Review Questions

Before implementation planning, a reviewer should answer:

1. Are the proposed fields sufficient for Mission Control to be useful as an evidence viewer?
2. Are any proposed fields too sensitive for display/import?
3. Are the negative cases complete enough to prevent overclaiming execution or authority?
4. Should the first implementation be file import only, or is a local read-only API acceptable?
5. Which parts belong in Mission Control, and which parts must remain in Ithildin?

## Current Decision

Design-only planning may continue. Runtime implementation remains blocked until a later explicit
implementation plan, implementation gate, source-review handoff, and release/readiness update.


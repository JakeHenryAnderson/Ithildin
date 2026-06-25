# Mission Control Display Importer Implementation Plan

Status: planning-only implementation packet for a future Mission Control display importer.

This plan translates Ithildin's display proposal, handoff schema contract, and negative fixture plan
into a future Mission Control implementation shape. It does not add runtime behavior, tool
manifests, executors, policy rules, API endpoints, MCP transports, Mission Control runtime behavior,
local model invocation, VM/container lifecycle management, sandbox orchestration, trusted-host
promotion, SIEM adapters, production IAM, runtime Postgres, hosted telemetry, shell,
Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes, compliance
automation, or public/security-product claims.

Current governed tool count: `24`.

Current selected capability: `not selected`.

## Scope

The first importer should be file/import display only:

1. Operator chooses an Ithildin handoff packet file or packet directory.
2. Mission Control parses the packet locally.
3. Mission Control validates schema version, authority flags, artifact hashes, attachment paths,
   warning chips, and packet freshness evidence.
4. Mission Control displays safe labels, IDs, hashes, relative links, warning chips, and review
   status.
5. Mission Control records display/import status in its own mission context without calling
   Ithildin, executing a model, approving an action, starting a VM/container, or promoting host
   artifacts.

## Required Input Contract

The future importer must accept only an operator-selected local packet source:

- packet directory path selected by the operator;
- optional explicit handoff JSON file path inside that directory;
- optional operator mission label;
- optional operator note.

It must not accept remote URLs, shell commands, glob patterns, callbacks into Ithildin, raw model
prompts, local model instructions, VM/container descriptors, or trusted-host destination paths.

## Required Validation Stages

The future importer should validate in this order:

1. **Packet source**: local path exists, is operator-selected, and does not rely on network access.
2. **Schema**: handoff payload has supported `schema_version`, `handoff_type`, and
   `status: metadata_only`.
3. **Authority flags**: all Mission Control runtime, local model, VM/container, sandbox,
   shell, and host-promotion booleans remain false; Ithildin remains policy authority.
4. **Display contract**: display allowlist, hidden-field denylist, and warning chips are present.
5. **Attachment links**: packet-relative paths only; no absolute paths, parent traversal, URLs, or
   runtime instructions.
6. **Artifact hashes**: referenced hash manifest exists and any imported artifact digest matches the
   packet metadata.
7. **Freshness**: commit, timestamp, packet version, and artifact digest status are rendered as
   current, stale, unsupported, or warning-required.
8. **Secret-free display**: no file contents, raw host paths, raw prompts, diffs, response bodies,
   secrets, dependency names, package script values, environment values, or raw sandbox internals are
   displayed.

## Display Model

The future importer may render:

- mission label and operator note;
- local-preview status;
- handoff schema and packet version;
- model/client label as metadata only;
- run ID, request ID, approval ID, execution status label, and audit status;
- artifact label, byte count, and SHA-256 digest;
- policy hash, manifest hash, and audit head hash;
- relative evidence links;
- warning chips for metadata-only, local model not invoked, VM/container not started, sandbox not
  orchestrated, host promotion not performed, and Ithildin remains policy authority.

The future importer must not render:

- raw prompts;
- file contents;
- diffs;
- response bodies;
- raw host paths;
- environment values;
- dependency names;
- package script values;
- tokens;
- private keys;
- raw sandbox internals;
- production/compliance conclusions.

## Import Status States

The future importer may use these display-only states:

- `not_imported`;
- `imported_valid`;
- `imported_with_warnings`;
- `unsupported_schema`;
- `stale_packet`;
- `hash_mismatch`;
- `unsafe_attachment`;
- `authority_overclaim`;
- `content_leak_rejected`.

These are Mission Control display states only. They do not create Ithildin approvals, mutate
Ithildin audit records, repair artifacts, replay actions, run local models, or promote outputs.

## Negative Fixture Coverage

The first implementation must cover the existing negative families from
[mission-control-handoff-negative-fixtures.md](mission-control-handoff-negative-fixtures.md):

- missing or unsupported schema;
- non-`metadata_only` status;
- Mission Control runtime behavior overclaim;
- host promotion overclaim;
- Ithildin policy authority disabled;
- absolute or parent-traversal attachment paths;
- missing display contract;
- incomplete hidden-field denylist;
- missing warning chips;
- executor-authority overclaim;
- raw file-content leak;
- raw prompt leak.

Additional Mission Control-side fixtures should cover stale commit/timestamp evidence, missing hash
manifest, mismatched artifact digest, unsupported packet family, and packet directory chosen outside
the operator-selected source.

## Evidence And Review Requirements

Before any Mission Control-side runtime importer ships, the implementation lane needs:

- Mission Control-side source-review packet;
- accepted/rejected fixture corpus;
- command evidence for valid import, stale packet, hash mismatch, unsafe attachment, authority
  overclaim, and content leak rejection;
- UI evidence showing warning chips remain visible;
- no-new-powers evidence from Ithildin;
- artifact-hash evidence for generated review packets;
- post-RC decision record updating `PRD-MC-DISPLAY-001`;
- explicit statement that Ithildin remains the policy, approval, execution, and audit authority.

## Explicit Non-Goals

This plan does not approve:

- Mission Control execution authority;
- Mission Control policy authority;
- Mission Control approval authority;
- Mission Control audit authority;
- callback APIs from Mission Control into Ithildin;
- live synchronization;
- local model invocation;
- VM/container lifecycle control;
- sandbox orchestration;
- trusted-host promotion;
- shell execution;
- direct filesystem mutation by Mission Control;
- remote MCP;
- SIEM adapters;
- production IAM;
- compliance automation;
- public/security-product positioning.

## Current Decision

Design-only planning may continue for `ERG-002` and `PRD-MC-DISPLAY-001`.
Runtime importer implementation remains blocked until a separate post-RC decision record, Mission
Control-side implementation plan, source-review handoff, and release/readiness update approve the
exact implementation slice.
The next implementation approval must include a Mission Control-side implementation plan for the
exact file/import display behavior.

## Validation

Run:

```sh
make mission-control-display-importer-plan-check
make mission-control-display-integration-proposal-check
make mission-control-handoff-schema-contract-check
make mission-control-handoff-negative-fixtures-check
```

# Mission Control-Side Display Importer Handoff Plan

Status: planning-only cross-repo handoff for a future Mission Control display/importer task.

This handoff translates Ithildin's Mission Control display integration proposal, importer
implementation plan, handoff schema contract, and negative fixture plan into a Mission Control-side
work order.

Mission Control-side work order: implement a display-only importer for Ithildin evidence packets
without claiming execution, policy, approval, audit, local-model, VM/container, sandbox, promotion,
SIEM, identity, or compliance authority.

It is meant to be pasted or copied into the Mission Control repository when that project is ready to
implement a file/import evidence viewer. It does not add runtime behavior to Ithildin or Mission
Control, and it does not approve Mission Control execution, policy, approval, audit, local model,
sandbox, host-promotion, SIEM, identity, or compliance authority.

Current governed tool count: `24`.

Current selected capability: `not selected`.

## Intended Mission Control Task

Implement a local file/import display surface for Ithildin evidence packets.

The future Mission Control implementation should:

1. Let an operator select a local Ithildin handoff packet directory or handoff JSON file.
2. Validate the packet schema, metadata-only status, authority flags, display allowlist,
   hidden-field denylist, packet-relative attachments, artifact hashes, freshness, and warning chips.
3. Render safe labels, IDs, short hashes, warning chips, relative evidence links, and import status.
4. Store only Mission Control-local display/import metadata in a mission context.
5. Refuse unsafe packets with explicit display states rather than trying to repair, execute, approve,
   replay, promote, or call back into Ithildin.

## Required Mission Control Inputs

The future importer should accept only:

- operator-selected local packet directory;
- optional operator-selected handoff JSON file inside that directory;
- optional mission label;
- optional operator note;
- optional display-only grouping label.

It must reject or ignore:

- remote URLs;
- shell commands;
- glob patterns;
- raw model prompts or model instructions;
- Ithildin callback URLs;
- API tokens;
- VM/container descriptors;
- trusted-host destination paths;
- host promotion instructions;
- SIEM destination configuration.

## Required Mission Control Validation

The future Mission Control implementation should use this validation order:

1. **Operator-selected source**: selected path exists and is local.
2. **Packet boundary**: imported files stay inside the selected packet directory.
3. **Schema**: supported schema version, handoff type, and `metadata_only` status are present.
4. **Authority flags**: Mission Control execution, policy, approval, audit, model, VM/container,
   sandbox, shell, and host-promotion authority flags remain false.
5. **Display contract**: display allowlist, hidden-field denylist, and warning chips are present.
6. **Attachment paths**: attachments are packet-relative; absolute paths, parent traversal, URLs,
   and runtime instructions are rejected.
7. **Artifact hashes**: referenced digest evidence is present and mismatches produce warnings or
   rejection states.
8. **Freshness**: commit, timestamp, packet version, schema version, and digest status are rendered
   as valid, stale, unsupported, or warning-required.
9. **Secret-free display**: content fields, prompts, diffs, response bodies, raw host paths,
   environment values, dependency names, package scripts, tokens, private keys, and raw sandbox
   internals are never rendered.

## Display States

The future Mission Control side should preserve Ithildin's display-only states:

- `not_imported`;
- `imported_valid`;
- `imported_with_warnings`;
- `unsupported_schema`;
- `stale_packet`;
- `hash_mismatch`;
- `unsafe_attachment`;
- `authority_overclaim`;
- `content_leak_rejected`.

These states are display/import states only. They do not mutate Ithildin, create approvals, replay
actions, run models, inspect live VMs, repair artifacts, promote outputs, or change policy.

## Required Mission Control Tests

The first Mission Control implementation task should include tests or fixture checks for:

- valid metadata-only handoff import;
- unsupported schema rejection;
- non-`metadata_only` status rejection;
- Mission Control execution-authority overclaim rejection;
- Mission Control policy/approval/audit-authority overclaim rejection;
- local model, VM/container, sandbox, shell, and host-promotion overclaim rejection;
- absolute attachment path rejection;
- parent-traversal attachment path rejection;
- URL attachment rejection;
- missing display allowlist rejection;
- missing hidden-field denylist rejection;
- missing warning chips rejection;
- raw prompt/content/diff/response-body display rejection;
- stale packet warning;
- artifact-hash mismatch warning or rejection;
- unsupported packet-family rejection.

## Required Mission Control Evidence

The Mission Control-side implementation should produce:

- source-review handoff packet;
- valid import transcript;
- stale packet transcript;
- hash mismatch transcript;
- unsafe attachment transcript;
- authority overclaim transcript;
- content leak rejection transcript;
- UI evidence showing warning chips remain visible;
- artifact hashes for generated review packets;
- no-new-authority evidence showing Mission Control remains display/import only.

## Explicit Non-Goals

This handoff does not approve:

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
- runtime Postgres;
- hosted telemetry;
- compliance automation;
- public/security-product positioning.

## Stop Conditions For Mission Control Work

Stop the Mission Control-side task and return for design review if implementation requires:

- executing an action rather than displaying evidence;
- accepting remote packet sources;
- writing outside Mission Control-local display metadata;
- calling Ithildin APIs;
- changing Ithildin policy, approval, audit, or execution state;
- showing raw prompts, file contents, diffs, response bodies, host paths, environment values, tokens,
  dependency names, or package scripts;
- treating Mission Control as a trusted host or sandbox controller;
- making production security, compliance, custody, SIEM, or identity claims.

## Current Decision

Mission Control-side implementation planning may continue for `ERG-002` and `PRD-MC-DISPLAY-001`.
Runtime importer implementation remains blocked until a separate post-RC decision record, Mission Control repository implementation plan, source-review handoff, fixture evidence, and readiness update approve the exact Mission Control-side display/import slice.

## Validation

Run from the Ithildin repository:

```sh
make mission-control-side-handoff-plan-check
make mission-control-display-importer-plan-check
make mission-control-display-review-packet-check
```

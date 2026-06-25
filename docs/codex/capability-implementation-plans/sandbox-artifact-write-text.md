# Implementation-Planning Packet: sandbox.artifact.write_text

Status: implementation-planning only. Implementation is blocked until a later explicit
implementation decision.

This document converts the design-only
[sandbox.artifact.write_text](../capability-proposals/sandbox-artifact-write-text.md) proposal into
a future implementation checklist for the Hello World sandbox demo. It does not add a tool
manifest, executor, policy rule, API/MCP behavior, Mission Control runtime behavior, VM lifecycle
control, approval mutation, audit mutation, UI behavior, or runtime write behavior.

No manifest is added in this planning sprint.

## Future Manifest Sketch

If explicitly approved later, the manifest would define:

- name: `sandbox.artifact.write_text`;
- risk: `write`;
- category: `sandbox`;
- MCP exposure: governed path only;
- input schema: closed object with `workspace_id`, `sandbox_id`, `root`, `relative_path`,
  `content`, `create_parent_directories`, `overwrite`, and `idempotency_key`;
- output schema: artifact labels, content hash, byte count, parent-created flag, approval evidence,
  truncation/limit state, and output-policy flags.

The manifest must not be added before an implementation-boundary sprint explicitly approves this
new write-adjacent power class.

## Future Input Contract

Future inputs must be tightly bounded:

- `workspace_id`: known enabled workspace;
- `sandbox_id`: known enabled operator-managed sandbox/staging profile;
- `root`: relative sandbox/staging root label only, default `.`;
- `relative_path`: relative artifact path only;
- `content`: UTF-8 text only, capped by byte and line limits;
- `create_parent_directories`: boolean, default false unless approved by the operator action;
- `overwrite`: boolean, default false and allowed only with explicit approval semantics;
- `idempotency_key`: bounded caller-provided action correlation key.

The schema must use `additionalProperties: false` and reject malformed, oversized, traversal,
absolute, encoded-ambiguous, control-character, hidden/sensitive, `.git`, symlink, hardlink, and
host-root inputs.

## Future Output Contract

The future output must contain only safe evidence:

- status label such as `created`, `already_exists`, `denied`, or `requires_approval`;
- workspace ID;
- sandbox ID;
- artifact label such as `sandbox://hello-demo/hello.txt`;
- parent-created flag;
- bytes written;
- `content_sha256`;
- created artifact ID;
- approval ID when required;
- output-policy flags.

The response must not include raw host paths, file contents, prompts, chain-of-thought, secrets,
environment values, shell output, VM logs, directory listings, or unrelated sandbox contents.

## Future Filesystem Contract

Future implementation must preserve the local-preview filesystem posture:

- operator-managed sandbox/staging roots only;
- relative roots and artifact paths only;
- no broad recursive listing output;
- same-directory temporary file and atomic replace only when overwrite is explicitly approved;
- no overwrite by default;
- no delete, move, chmod, archive extraction, or recursive write;
- deny `.git`, hidden/sensitive paths, symlinks, hardlinks, unsupported file types, unsupported
  encodings, binary/NUL content, oversized content, and ambiguous Unicode/control-character paths;
- record safe skipped/denied counts rather than raw paths.

## Future Policy / Approval Requirements

This capability is write-adjacent and must require a separate implementation decision before any
runtime work. That later decision must define:

- policy preview/runtime parity for a `sandbox_artifact` resource;
- approval requirements for artifact creation and any parent-directory creation;
- approval binding for `workspace_id`, `sandbox_id`, normalized artifact label, content hash,
  overwrite flag, parent-created flag, policy hash, manifest hash, schema hash, principal ID,
  request hash, and expiry;
- replay denial and idempotency behavior;
- diagnostics for incomplete writes without automatic repair.

## Future Audit Metadata

Audit metadata should record only safe evidence:

- tool name;
- principal ID;
- workspace ID;
- sandbox ID;
- resource type `sandbox_artifact`;
- artifact label;
- proposal/action hash;
- content hash;
- byte count;
- parent-created flag;
- overwrite flag;
- approval ID;
- policy hash;
- manifest hash;
- request hash;
- output-policy keys.

Audit metadata must not include file contents, raw host paths, prompts, secrets, environment values,
response bodies, shell output, VM logs, or unrelated directory listings.

## Future Mission Control / Agent Run Evidence

The Hello World demo must correlate:

- Mission Control mission ID;
- local model/client label;
- agent run ID;
- proposed action hash;
- approval ID;
- Ithildin audit event IDs;
- sandbox artifact ID and content hash;
- promotion evidence ID if host promotion is later approved.

Mission Control remains the operator surface and evidence viewer. Ithildin remains the governed
gateway. This plan does not give Mission Control independent write authority.

## Future Negative Tests

Future tests must cover:

- traversal denial;
- absolute path denial;
- encoded ambiguity denial;
- control-character denial;
- hidden/sensitive path denial;
- `.git` denial;
- symlink denial;
- hardlink denial;
- missing sandbox profile;
- disabled workspace;
- unknown/disabled principal;
- oversized content;
- unsupported encoding;
- binary/NUL content;
- overwrite denied by default;
- parent-directory creation denied without approval;
- host write denied without promotion;
- replayed approval denied;
- stale approval denied;
- Mission Control metadata-only evidence remains separate from Ithildin execution evidence.

## Source Review And Implementation Decision Requirement

Actual implementation remains blocked. A future implementation-boundary sprint must add an
implementation decision document, manifest, manifest-lock update, executor tests, policy parity
fixtures, approval binding tests, audit/evidence tests, negative transcripts, source-review bundle,
and release/readiness updates before `sandbox.artifact.write_text` can be considered for
local-preview runtime use.

The future implementation must preserve the strict non-goals: no shell execution, no Docker socket
access, no Kubernetes tools, no browser automation, no arbitrary HTTP, no broad filesystem
writes/deletes/moves/chmod/archive extraction, no VM/container lifecycle control, no automatic host
promotion, no production identity, no runtime Postgres, no hosted telemetry, no remote MCP hosting,
no plugin SDK behavior, no SIEM adapter, no compliance automation, and no public/security-product
positioning.

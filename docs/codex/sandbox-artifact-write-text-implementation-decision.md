# sandbox.artifact.write_text Implementation Decision

Status: implementation boundary approved for a later bounded local-preview sprint.
Runtime implementation remains absent.

This decision authorizes only a future implementation sprint for `sandbox.artifact.write_text` under
the conditions below. It does not add a manifest, executor, policy rule, API/MCP behavior,
Mission Control runtime behavior, VM lifecycle control, UI runtime behavior, approval mutation,
audit mutation, or runtime write behavior.

## Approved Future Boundary

The future implementation may create a single governed tool only if it preserves this boundary:

- tool name: `sandbox.artifact.write_text`;
- risk: `write`;
- category: `sandbox`;
- resource type: `sandbox_artifact`;
- transport: existing governed API/MCP path only;
- input: closed schema with `workspace_id`, `sandbox_id`, `root`, `relative_path`, `content`,
  `create_parent_directories`, `overwrite`, and `idempotency_key`;
- output: artifact label, content hash, byte count, approval evidence, and output-policy flags;
- first demo target: `hello-demo/hello.txt` containing `Hello World`.

## Required Runtime Constraints

The future implementation must:

- write only under an operator-approved sandbox or staging profile;
- deny direct trusted-host writes;
- deny host promotion unless a separate promotion lane is later approved;
- deny overwrite by default;
- require approval for non-idempotent creation, parent-directory creation, and any future overwrite;
- reject traversal, absolute paths, encoded ambiguity, control characters, hidden/sensitive paths,
  `.git`, symlinks, hardlinks, unsupported encodings, binary/NUL content, oversized content, and
  missing sandbox profiles;
- use atomic write behavior appropriate to the approved path and operation;
- record recovery/diagnostic evidence for incomplete attempts without automatic repair.

## Required Evidence

The future implementation must bind approval and audit evidence to:

- workspace ID;
- sandbox ID;
- normalized artifact label;
- content hash;
- byte count;
- overwrite flag;
- parent-created flag;
- policy hash;
- manifest hash;
- schema hash;
- principal ID;
- request hash;
- expiry;
- idempotency key.

Responses, audit metadata, diagnostics, and Mission Control handoffs must not include file
contents, raw host paths, prompts, chain-of-thought, secrets, environment values, shell output,
VM logs, unrelated listings, sandbox root internals, production identity claims, or compliance
claims.

## Required Gates Before Runtime Acceptance

A future implementation sprint must add and pass:

- manifest and manifest-lock update;
- policy preview/runtime parity for `sandbox_artifact`;
- approval binding and replay tests;
- executor tests for all fixture scenarios;
- negative transcript generation;
- audit/redaction tests;
- MCP list/call tests through the governed path;
- source-review handoff bundle;
- `make release-check`.

## Explicit Non-Goals

This decision does not approve shell execution, Docker socket access, Kubernetes tools, browser
automation, arbitrary HTTP, broad filesystem writes/deletes/moves/chmod/archive extraction,
VM/container lifecycle control, automatic host promotion, production identity, runtime Postgres,
hosted telemetry, remote MCP hosting, plugin SDK behavior, SIEM adapters, compliance automation, or
public/security-product positioning.

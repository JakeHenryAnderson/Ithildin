# Agent Run Evidence Export Implementation Plan

Status: historical implementation-planning packet; later advanced through the approved bounded
read-only Agent Run evidence export endpoint recorded in
[agent-run-evidence-export-implementation.md](agent-run-evidence-export-implementation.md).

Original status: implementation-planning only.

Original marker: Status: implementation-planning only.

Historical invariant: this document does not add runtime behavior, API endpoints, MCP tools,
executors, policy rules, UI controls, SIEM adapters, sandbox controls, production identity, runtime
Postgres, hosted telemetry, shell, Docker, Kubernetes, browser automation, arbitrary HTTP, broad
filesystem writes, or plugin SDK work.

Original implementation state: blocked until a later explicit implementation decision, focused
source review, and green implementation gates.

Original marker: Implementation state: blocked.

## Proposed Endpoint

Future endpoint sketch:

- method/path: `GET /runs/{run_id}/evidence-export`;
- protection: admin bearer token only;
- behavior: read-only export of one existing Agent Run evidence bundle;
- input: path parameter `run_id` only, plus optional safe query fields after separate review;
- output: JSON object with `schema_version`, `export_id`, `exported_at`, `run`, `timeline`,
  `approvals`, `patch_diagnostics`, `signed_export_references`, `evidence_hashes`,
  `redaction_summary`, and `warnings`;
- non-goal: no mutation, repair, replay, approval creation, audit rewrites, SIEM forwarding,
  sandbox control, or run-control behavior.

The first implementation should reject unknown query parameters until a later reviewed task adds
filtering or format controls.

## JSON Schema Plan

Future schema validation must use `additionalProperties: false` at every object level.

Allowed top-level output fields:

- `schema_version`;
- `export_id`;
- `exported_at`;
- `run`;
- `timeline`;
- `approvals`;
- `patch_diagnostics`;
- `signed_export_references`;
- `evidence_hashes`;
- `redaction_summary`;
- `warnings`.

Allowed `run` fields:

- `run_id`;
- `principal_id`;
- `workspace_id`;
- `sandbox_id`;
- `session_id`;
- `model_client_label`;
- `status`;
- `policy_hash`;
- `manifest_lock_hash`;
- `tool_call_count`;
- `created_at`;
- `updated_at`.

Allowed `timeline` fields:

- `event_id`;
- `run_id`;
- `timestamp`;
- `category`;
- `status`;
- `correlation_id`;
- `tool_name`;
- `approval_id`;
- `audit_event_id`;
- `policy_hash`;
- `manifest_hash`;
- `metadata`.

The `metadata` object must be secret-free and bounded. Future implementation tests must reject or
redact prompts, model output, model reasoning, raw tool arguments, file contents, diffs, response
bodies, secrets, bearer tokens, cookies, package script values, dependency names, raw sensitive
paths, private key material, local environment files, runtime SQLite database content, and raw audit
JSONL payloads.

## Fixture Plan

Future implementation tests should include these fixture export bundles:

- clean run: one allowed read-only tool call with policy and audit correlation;
- approval-required run: patch proposal/apply lifecycle with approval evidence and safe binding
  metadata;
- denied action run: denial evidence without executor output or rejected sensitive input values;
- patch-diagnostic run: `recovery_required` or incomplete patch apply attempt represented without
  file contents or diffs;
- signed-export-referenced run: local signed audit export metadata referenced by key ID, digest, and
  verification status only.

Fixture files should be deterministic, committed only if secret-free, and small enough for review
packets. Runtime databases, raw audit logs, local signing keys, and generated signatures must remain
ignored unless a later reviewed fixture explicitly creates synthetic non-secret material.

## Negative Case Plan

Future implementation tests must cover:

- missing admin token denies;
- wrong admin token denies;
- unknown `run_id` returns a safe not-found response;
- malformed `run_id` fails before store lookup;
- unknown query parameter rejects;
- missing audit correlation records a warning instead of fabricating evidence;
- missing approval correlation records a warning instead of fabricating evidence;
- oversized timeline fails safely or truncates with explicit `warnings`;
- absent signed evidence is reported as unavailable, not as a verification failure;
- corrupt signed export reference fails verification when verification is requested later;
- redaction boundary excludes prompts, raw tool arguments, file contents, diffs, response bodies,
  and secrets.

## Review Prompt

Internal xhigh or external source review should answer:

- Is the endpoint read-only and admin-only?
- Are schema fields bounded and secret-free?
- Are missing correlations represented honestly?
- Are signed export references local evidence only, not notarization or SIEM custody?
- Are warnings sufficient for incident reconstruction of mediated actions only?
- Is implementation safe to plan without adding new governed tool powers?

Finding IDs should use `EXT-RUN-EXPORT-###` for external/source review findings.

## Required Future Gates

Before implementation can start, a later task must add or update:

- endpoint authorization tests;
- JSON schema validation tests;
- fixture export bundle tests;
- negative case tests;
- redaction and size-limit tests;
- signed-export reference tests;
- review-console display expectations if UI support is included;
- source-review packet with implementation files and focused command evidence.

Run `make agent-run-evidence-export-plan-check` to validate this planning packet. Passing this gate
does not approve implementation.

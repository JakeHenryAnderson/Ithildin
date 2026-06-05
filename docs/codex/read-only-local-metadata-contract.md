# Read-Only Local Metadata Capability Contract

Status: capability-expansion preparation. This contract does not add a tool manifest, executor,
policy rule, MCP exposure, API behavior, UI behavior, approval behavior, or runtime behavior.

This contract defines the shared floor for future read-only local developer metadata tools. A future
capability may be planned only if it stays inside this contract or records an explicit exception and
stops for review.

## Scope

Allowed capability family:

- read-only;
- local-first;
- metadata-only;
- workspace-scoped;
- schema-validated;
- fixed-parser and fixed-argv where a subprocess is unavoidable;
- policy-preview/runtime comparable;
- audit-evidence producing;
- bounded by count, byte, and runtime limits.

Examples that may fit this family after separate planning:

- local Git metadata summaries;
- dependency manifest summaries;
- project metadata summaries;
- package-lock or requirements metadata summaries.

## Shared Requirements

Every future read-only local metadata capability must define:

- exact tool name, category, risk, and intended resource shape;
- strict JSON Schema with `additionalProperties: false` at every object level;
- exact accepted input fields and enum values;
- exact output fields and redaction/truncation fields;
- executor contract with no shell interpretation;
- policy fixture expectations;
- audit evidence fields;
- negative transcript or test cases;
- resource limits;
- source-review packet surface;
- no-new-powers analysis;
- accepted-risk impact.

## Executor Contract

Executors must:

- resolve workspace IDs through the trusted workspace registry;
- verify all local filesystem/repository roots are inside the selected workspace;
- avoid shell execution entirely;
- avoid caller-controlled argv, flags, format strings, pathspecs, globs, environment, or command
  fragments;
- use fixed argv and fixed parser contracts;
- use structured APIs where available and fixed local commands only where necessary;
- suppress remote/network behavior by construction;
- enforce timeouts, output-byte limits, item-count limits, and text-length limits;
- fail closed on malformed input, unsupported platform profiles, ambiguous parsing, or unsafe
  metadata;
- return safe errors without raw stderr, secrets, file contents, diffs, patch hunks, credentials,
  environment values, or terminal-control text.

## Output Contract

Outputs must be bounded metadata only. They must not include:

- file contents;
- raw diffs or patch hunks;
- shell output;
- remote URLs unless explicitly reviewed and redacted;
- credentials, tokens, cookies, private keys, or secret-like values;
- arbitrary user-controlled command output;
- unbounded repository-controlled text;
- raw names that the metadata privacy policy classifies as sensitive by default.

Every output schema must include redaction/truncation/limit evidence where relevant. Every object
schema must be explicit about allowed fields and must reject or omit unknown fields.

## Policy And Audit Contract

Policy preview and runtime execution must construct comparable resources. Each capability must
document:

- normalized principal source;
- workspace ID and in-scope evidence;
- metadata selector kind;
- tool risk and manifest hash/version once a manifest exists;
- policy engine/version/hash;
- matched rules and obligations;
- denial behavior for unknown/disabled principals and workspaces.

Audit records must include safe decision and execution metadata, not raw sensitive values. Audit
evidence should record counts, truncation, redaction modes, selector kinds, and safe error reasons.

## Review Requirements

Before implementation, a capability must pass:

- proposal check;
- implementation-plan check;
- internal xhigh review of proposal/plan;
- no-new-powers guardrail;
- tool-surface invariant planning evidence;
- source-review handoff plan.

Before runtime implementation can be committed, it must have:

- manifest and lock update plan;
- executor source review;
- focused tests and negative transcripts;
- policy fixture/parity evidence;
- MCP exposure evidence;
- UI/tool-list evidence where applicable;
- explicit implementation decision for that one capability only.

## Non-Goals

This contract does not approve:

- shell execution;
- Docker socket access;
- Kubernetes tools;
- browser automation;
- arbitrary HTTP methods, caller-supplied headers, request bodies, cookies, or broad network access;
- broad filesystem writes, deletes, moves, chmod, archive extraction, or secrets-manager tools;
- plugin SDK or marketplace;
- remote hosted MCP gateway;
- production identity integrations;
- runtime Postgres;
- hosted telemetry collectors;
- managed model serving or LLM proxy workflows.

Any future capability that needs one of these surfaces is outside this contract and must stop for a
separate product-risk decision and external/human review.

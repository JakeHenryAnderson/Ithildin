# Implementation-Planning Packet: git.show.commit_metadata

Status: implementation-planning only. This document does not add a tool manifest, executor, policy
rule, MCP exposure, approval behavior, API behavior, or runtime behavior. It converts the accepted
v0.9 design proposal into an implementation checklist for a later explicit implementation decision.

## Planning Decision

- Capability: `git.show.commit_metadata`.
- Planning state: ready for implementation-planning review.
- Implementation state: blocked.
- Future implementation may be planned only after this packet passes
  `make git-commit-metadata-implementation-plan-check`.
- Actual implementation remains blocked until a later GPT 5.5 Pro / human external/source review and
  implementation go decision.

## Boundary

This planning packet must not create or modify:

- `tool-manifests/` files or `tool-manifests.lock.json`;
- executor code or governed tool dispatch;
- API or MCP runtime behavior;
- policy rules or approval behavior;
- registry behavior, principal behavior, workspace behavior, or audit storage behavior.

It may describe future work, proposed contracts, expected tests, and required evidence.

## Future Manifest Sketch

If implementation is later approved, the future manifest should be a read-only Git metadata tool:

- name: `git.show.commit_metadata`;
- risk: `read`;
- category: `git`;
- MCP exposure: yes only after explicit implementation approval;
- input schema: structured selector, no arbitrary Git revision strings, no caller format strings;
- output schema: bounded metadata only, no file contents, no raw diffs, no raw Git stderr.

This is a sketch only. No manifest is added in this planning sprint.

## Proposed Input Contract

The future input schema should include:

- `workspace_id`: optional configured workspace ID.
- `ref`: required selector object, one of:
  - `{"kind":"object_id","value":"<40-or-64-hex-commit-id>"}`;
  - `{"kind":"branch","value":"<local-branch-name>"}`;
  - `{"kind":"tag","value":"<local-tag-name>"}`.
- `include_body`: optional boolean, default `false`.
- `include_emails`: optional boolean, default `false`.
- `include_diffstat`: optional boolean, default `true`.

It must reject empty refs, option-like refs, whitespace/control characters, arbitrary revision
syntax, remote-tracking refs, pathspecs, reflog selectors, commit-message search selectors, and
caller-supplied format strings.

## Executor Contract Checklist

A future executor, if approved, must:

- run only inside a workspace root accepted by the workspace registry and Git safety layer;
- avoid shell interpretation entirely;
- use fixed argv only;
- construct `refs/heads/<name>` or `refs/tags/<name>` internally for branch/tag selectors;
- use `--end-of-options` where Git argv could otherwise parse user-like values as options;
- verify the resolved object is a commit before reading metadata;
- use fixed metadata formatting controlled by Ithildin;
- parse NUL-delimited changed-file metadata rather than ad hoc line splitting;
- suppress proxy/network behavior by construction by using local Git read operations only;
- enforce command timeout, output-byte, subject, body, and changed-file limits;
- return safe errors without raw Git stderr, file contents, patch contents, environment, or
  credentials.

## Ref Resolution Test Plan

Future tests must cover:

- full object ID resolution to a commit;
- local branch selector resolved through `refs/heads/<name>`;
- local tag selector resolved through `refs/tags/<name>`;
- non-commit object rejection;
- unknown object/ref safe error;
- option-like ref beginning with `-`;
- arbitrary revision syntax such as `HEAD~1`, `HEAD@{1}`, `:/message`, `main:path`, and ranges;
- remote-tracking refs such as `origin/main` and `refs/remotes/origin/main`;
- ambiguous short hashes rejected unless a later review approves a separate ambiguity policy.

## Metadata Parsing Plan

Future parsing should use controlled Git output and structured parsing:

- fixed commit identity/parent/timestamp fields;
- bounded subject and optional bounded body;
- NUL-delimited `--name-status -z` and `--numstat -z` style changed-file metadata;
- rename/copy entries with old and new path handling;
- submodule/gitlink entries as metadata only;
- symlink paths as path metadata only, never target contents;
- binary numstat markers such as `-`/`-`.

The parser must not return raw diff hunks, blob contents, file contents, symlink targets, raw stderr,
or terminal-control sequences.

## Redaction And Sensitive Metadata Plan

Future implementation must treat Git metadata as potentially sensitive:

- `include_emails=false` by default and omits email values from agent output.
- `include_emails=true` may return emails only after redaction.
- `include_body=false` by default and body text is labeled untrusted Git metadata when returned.
- commit body output is capped, redacted, and flagged with truncation/redaction metadata.
- changed-file paths pass a sensitive-path classifier before return.
- hidden paths, `.git` internals, `.env`, private-key names, credential/config key files, invalid
  UTF-8, control characters, terminal-control sequences, and traversal-like path text are denied or
  redacted by default.
- no `include_sensitive_paths` escape hatch is allowed in the first implementation plan.

Audit records must record redaction/truncation summaries, not raw omitted email values, raw redacted
paths, raw Git stderr, file contents, or patch contents.

## Policy Fixture Plan

Future policy fixtures must prove:

- read-capable principal and in-scope workspace metadata returns `allow`;
- read-only/auditor principal remains read-only under the existing role matrix;
- unknown, disabled, or spoofed principals deny before execution;
- disabled or unknown workspace denies before execution;
- out-of-scope workspace/root denies before execution;
- write/network/destructive obligations are not introduced;
- policy preview and runtime resource evidence are comparable.

No policy rule is added in this planning sprint.

## Audit Evidence Plan

Future audit metadata should include:

- tool name, manifest hash/version, and schema version;
- normalized principal and session ID;
- workspace ID and in-scope repository evidence;
- requested selector kind and safe requested value hash/redaction;
- resolved commit hash;
- parent count and changed-file count;
- body/email/path redaction and truncation summary;
- timeout and limit status;
- safe error reason when denied or failed.

It must not include raw omitted emails, raw redacted paths, raw Git stderr, file contents, patch
contents, environment variables, credentials, or command output beyond bounded returned metadata.

## UI And Policy Preview Plan

Future UI/review behavior should:

- show the tool in registered-tools only after a manifest is intentionally added later;
- show read risk, Git category, workspace scope, and bounded-output warnings;
- show policy preview evidence for principal, workspace, selector kind, resource scope, decision,
  matched rules, obligations, and redaction/limit expectations;
- label optional body output as untrusted Git metadata;
- expose no execution controls beyond the existing governed tool path.

## Negative Transcript Plan

Future negative transcripts or tests must cover:

- option-like ref denial;
- revision-expression denial;
- remote-tracking ref denial;
- unknown object/ref safe error;
- non-commit object denial;
- disabled/unknown workspace denial;
- unknown/disabled/spoofed principal denial;
- `include_emails=false` omitting raw emails;
- sensitive changed path redaction;
- oversized body truncation;
- oversized changed-file list truncation or safe limit error;
- binary change metadata-only output;
- safe error output with no raw stderr, contents, credentials, or environment.

## Resource Limits

Initial planning limits:

- max subject bytes: 512;
- max body bytes: 4096;
- max changed files: 500;
- max command output bytes: 131072;
- max command runtime: 5 seconds;
- no binary/content-bearing output by construction.

These are planning defaults and must be revalidated during implementation review.

## GPT 5.5 Pro / Human External Source Review Requirement

Before implementation begins, GPT 5.5 Pro / human external/source review must approve a later
implementation decision. That later implementation sprint must produce source-level review artifacts
for:

- manifest and lock update;
- executor implementation;
- schema validation;
- policy preview/runtime parity;
- audit evidence;
- MCP exposure;
- UI/tool-list evidence;
- negative transcripts and focused tests.

Actual implementation remains blocked until that later GPT 5.5 Pro / human external/source
review and implementation decision are explicitly approved.

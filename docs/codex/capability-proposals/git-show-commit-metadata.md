# Capability Proposal: git.show.commit_metadata

Status: design-only proposal. This document does not add a tool manifest, executor, policy rule,
MCP exposure, approval behavior, or runtime behavior.

## Purpose

`git.show.commit_metadata` would let an agent inspect bounded metadata for one commit in a configured
local workspace repository. It is intended to support code-review orientation without exposing file
contents, patch contents, remote Git state, shell execution, or write authority.

## Proposed Interface

Proposed input:

- `workspace_id`: optional workspace ID, defaulting to the configured default workspace.
- `ref`: required full object ID or explicit local ref selector to resolve to exactly one commit.
- `include_body`: optional boolean, default `false`.
- `include_diffstat`: optional boolean, default `true`.

Proposed output:

- `workspace_id` and repository-relative status.
- requested `ref` and resolved full commit hash.
- parent commit hashes.
- author and committer names/emails as Git metadata, with redaction applied before agent return.
- author and committer timestamps.
- subject, capped to 512 characters.
- body text only when `include_body=true`, capped to 4096 characters.
- changed-file summary with path, status code, and optional additions/deletions counts.
- truncation flags for body and changed-file summary.

## Ref Resolution Policy

This proposal deliberately constrains `ref` more tightly than normal Git revision syntax. The future
input schema should either accept a full object ID or an explicit selector object:

- `{"kind": "object_id", "value": "<40-or-64-hex-commit-id>"}`;
- `{"kind": "branch", "value": "<local-branch-name>"}`;
- `{"kind": "tag", "value": "<local-tag-name>"}`.

The future executor must reject:

- empty refs, refs longer than 128 bytes, whitespace/control characters, and values starting with
  `-`;
- arbitrary revision expressions such as `HEAD~1`, `main^2`, `HEAD@{1}`, `:/message`, `main:path`,
  ref ranges, pathspecs, and remote-tracking refs;
- caller-supplied `refs/remotes/*`, `origin/*`, or any syntax requiring remote state;
- ambiguous short hashes unless the design is later revised with a separate ambiguity policy.

Local branch and tag names must pass Git ref validation for `refs/heads/<value>` or
`refs/tags/<value>` and must be resolved with fixed argv using `--end-of-options` or an equivalent
safe Git API. The resolved object must be verified as a commit object before any metadata is read.

## Executor Contract Sketch

The future executor, if approved later, must use fixed Git argv only and no shell interpretation:

- resolve the ref with fixed argv using `--end-of-options` or an equivalent safe Git API;
- reject arbitrary Git revision syntax rather than passing caller input directly to Git revision
  parsing;
- read metadata with fixed formatting controlled by Ithildin, not caller-supplied format strings;
- collect changed-file summary with fixed read-only Git commands;
- run only inside a workspace root already accepted by the workspace registry and Git safety layer;
- apply command timeout and output-size limits;
- return safe errors for unknown refs, non-repository paths, oversized output, invalid encodings,
  weird filenames, and Git command failures.

## Changed-File Summary Contract

Changed-file summary must be non-content metadata. A future implementation should prefer fixed,
NUL-delimited Git output such as a controlled `--name-status -z` and `--numstat -z` shape, parsed by
Ithildin rather than by ad hoc line splitting.

The parser contract must account for:

- rename/copy records that contain old and new paths;
- submodules/gitlinks as metadata entries only;
- symlink paths as path metadata only, never target contents;
- binary `numstat` values such as `-`/`-`;
- path redaction/escaping for control characters and invalid UTF-8;
- truncation when the changed-file count or byte limit is exceeded.

The returned summary must not include raw diff hunks, blob contents, file contents, symlink targets,
or raw Git stderr.

## Policy And Resource Evidence

Proposed manifest risk would be `read` and category `git` if implementation is later approved.
Policy fixtures should treat the resource as local Git metadata scoped to one workspace and resolved
commit hash. Runtime policy and preview evidence should include:

- tool name and manifest hash/version;
- workspace ID and in-scope repository root;
- requested ref and resolved commit hash;
- risk `read`;
- matched rule and obligations;
- normalized principal from the local principal registry.

## Audit Fields

Audit metadata should include only safe structured evidence:

- requested ref;
- resolved commit hash;
- workspace ID;
- command argv shape without environment or secrets;
- output truncation flags;
- changed-file count;
- timeout/limit status;
- redaction summary.

Audit events must not include commit body beyond the bounded returned output, file contents, patch
contents, environment variables, credentials, or raw Git stderr.

## Resource Limits

Suggested initial limits for a future implementation:

- max subject bytes: 512;
- max body bytes: 4096;
- max changed files: 500;
- max command output bytes: 131072;
- max command runtime: 5 seconds;
- deny binary/content-bearing output by construction.

These values are proposal defaults only and must be reviewed before implementation.

## Negative Cases

The design-review packet should require tests or fixtures for:

- unknown ref and ambiguous ref;
- option-like ref beginning with `-`;
- arbitrary revision expressions such as `HEAD~1`, `HEAD@{1}`, `:/message`, `main:path`, and ref
  ranges;
- remote-tracking refs such as `origin/main` or `refs/remotes/origin/main`;
- ref resolving outside a commit object;
- non-repository workspace;
- disabled or unknown workspace;
- path traversal-like filenames in Git metadata;
- control-character or invalid-UTF-8 filenames;
- very large commit body;
- commits with more changed files than the limit;
- binary changes;
- Git command timeout;
- caller attempts to request arbitrary format strings, raw diff, file contents, checkout, branch
  mutation, remote fetch, or credentials.

## Negative Transcript Sketches

These are design transcripts, not runtime transcripts. They define the expected safe behavior if a
future implementation is approved.

| Scenario | Caller input | Expected response | Policy/audit evidence | Must not expose |
| --- | --- | --- | --- | --- |
| Option-like ref | `{"ref":{"kind":"branch","value":"--help"}}` | safe denial: invalid ref syntax | `deny_source: schema_or_executor_validation`; no command execution | Git help text, stderr, environment |
| Revision expression | `{"ref":{"kind":"branch","value":"HEAD~1"}}` | safe denial: revision expressions unsupported | requested ref hash/redacted value, no resolved commit | parent metadata, file contents, stderr |
| Remote-tracking ref | `{"ref":{"kind":"branch","value":"origin/main"}}` | safe denial: remote-tracking refs unsupported | workspace ID, validation reason | remote URLs, credentials |
| Unknown commit | `{"ref":{"kind":"object_id","value":"0000000000000000000000000000000000000000"}}` | safe not-found error | fixed argv shape, no raw stderr | raw Git stderr, repository internals |
| Oversized changed-file list | valid commit with more than limit | bounded success or safe limit error with truncation flag | changed-file limit and truncation status | paths beyond limit, diff hunks |
| Binary change | valid commit touching binary file | metadata-only entry with binary count marker | status code and binary marker | binary bytes, patch contents |

## UI And Review Evidence

No approval should be required for this read-only metadata tool under the current role/risk model if
implementation is later approved. The review console should display the tool in the registered-tools
surface only after a manifest is intentionally added in a later implementation sprint. Policy preview
should show read risk, workspace scope, resolved commit hash when runtime can resolve it, and no
write/network obligations.

## Accepted-Risk Impact

This proposal does not close or weaken accepted-deferred risks:

- `AR-001`: Ithildin remains a mediation layer, not a sandbox or host-compromise boundary.
- `AR-002`: local principals remain labels, not production identity.
- `AR-003`: audit remains local tamper-evident evidence, not custody-grade or notarized.
- `AR-009`: SQLite remains the runtime store; this proposal adds no storage backend.
- `AR-010`: redaction remains best-effort and the tool must not claim secret-safe output.

## No-New-Powers Analysis

The proposal stays close to existing read-only Git surfaces. It must not become:

- shell execution;
- broad filesystem reads;
- patch or file-content access;
- branch mutation or checkout;
- remote fetch or network access;
- credential or secrets-manager access;
- plugin SDK work.

## External Review Requirement

Implementation remains blocked. Before any manifest, executor, policy rule, MCP exposure, or runtime
behavior is added, GPT 5.5 Pro / human external review must review this design packet and produce an
explicit implementation-planning go/no-go decision.

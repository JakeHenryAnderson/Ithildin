# Implementation-Planning Packet: project.manifest.summary

Status: implementation-planning only. This document does not add a tool manifest, executor, policy
rule, MCP exposure, approval behavior, API behavior, UI behavior, or runtime behavior. It converts
the accepted design-only proposal into an implementation checklist for a later explicit
implementation decision.

## Planning Decision

- Capability: `project.manifest.summary`.
- Planning state: ready for implementation-planning review.
- Implementation state: blocked.
- Future implementation may be planned only after this packet passes
  `make project-manifest-summary-implementation-plan-check`.
- Actual implementation remains blocked until a later internal source-review or external/source
  review decision explicitly approves the bounded read-only implementation.

## Boundary

This planning packet must not create or modify:

- `tool-manifests/` files or `tool-manifests.lock.json`;
- executor code or governed tool dispatch;
- API or MCP runtime behavior;
- policy rules or approval behavior;
- registry behavior, principal behavior, workspace behavior, or audit storage behavior.

It may describe future work, proposed contracts, expected tests, and required evidence.

## Future Manifest Sketch

If implementation is later approved, the future manifest should be a read-only local metadata tool:

- name: `project.manifest.summary`;
- risk: `read`;
- category: `project`;
- MCP exposure: yes only after explicit implementation approval;
- input schema: workspace-relative root, allowlisted manifest basenames, and bounded limit only;
- output schema: structured manifest metadata only.

This is a sketch only. No manifest is added in this planning sprint.

## Proposed Input Contract

The future input schema should include:

- `workspace_id`: optional configured workspace ID.
- `root`: optional workspace-relative directory, default `"."`.
- `manifest_kinds`: optional array of allowlisted manifest basenames.
- `limit`: optional integer, default `20`, maximum `20`.

It must reject absolute paths, parent traversal, control characters, non-NFC path text, hidden or
sensitive path segments, `.git` internals, caller-controlled glob patterns, recursive scan depth,
arbitrary filenames, package-manager commands, parser options, network options, registry URLs,
include flags for raw contents, include flags for dependency names, and include flags for package
script values.

## Strict Schema Contract

Future schema validation must use `additionalProperties: false` at every object level.

Allowed top-level input fields:

- `workspace_id`;
- `root`;
- `manifest_kinds`;
- `limit`.

No other request fields are allowed. In particular, the first implementation must reject
`include_file_contents`, `include_dependency_names`, `include_script_values`, `glob`,
`recursive`, `registry_url`, `command`, `argv`, and `parser_options`.

## Manifest Allowlist And Selection

The first implementation may inspect only these exact manifest basenames at the selected root:

- `package.json`;
- `pyproject.toml`;
- `go.mod`;
- `Cargo.toml`;
- `pom.xml`;
- `build.gradle`;
- `requirements.txt`;
- `Gemfile`;
- `composer.json`.

The executor must not accept caller-supplied filenames outside this allowlist. It must not perform
recursive discovery. It may detect lockfile presence as count or boolean metadata only, but must not
return lockfile contents, dependency names, integrity hashes, registry URLs, resolved package source
URLs, or package-manager output.

## Parser Contract Checklist

A future executor, if approved, must:

- resolve the workspace through the existing workspace registry;
- resolve `root` as a relative path confined inside the workspace root;
- use the existing filesystem path-safety rules for traversal, symlink, hardlink, hidden path,
  sensitive path, `.git`, control-character, and Unicode normalization denial;
- inspect only allowlisted manifest basenames at the selected root;
- open files through the existing read-tool safety layer or an equivalent reviewed safe-open helper;
- reject binary data, invalid UTF-8, oversized files, and ambiguous encodings;
- enforce file-size, total parsed bytes, manifest count, and output-size limits before return;
- parse only count-oriented metadata with structured parsers or tiny fixed parsers;
- treat all manifest values as untrusted repository-controlled metadata;
- return safe parse failure reasons without echoing file contents.

The executor must never use shell execution, package-manager commands, registry/network access,
caller-controlled argv, caller-controlled parser options, broad filesystem search, package lifecycle
scripts, or arbitrary manifest filenames.

## Proposed Output Contract

Future output schema validation must use `additionalProperties: false` at every object level.

Allowed top-level output fields:

- `workspace_id`;
- `root`;
- `manifest_count`;
- `truncated`;
- `manifests`;
- `output_policy`;
- `limits`;

Allowed manifest entry fields:

- `manifest_id`;
- `kind`;
- `ecosystem`;
- `path_role`;
- `size_bytes`;
- `sha256`;
- `dependency_section_counts`;
- `script_count`;
- `lockfile_presence`;
- `parse_status`;
- `parse_error_reason`;
- `dependency_names_included`;
- `script_values_included`;
- `file_contents_included`;

No other manifest entry fields are allowed in the first implementation. Output must include no file
contents, no package script values, no dependency names by default, no package version constraints
by default, no registry URLs, no repository URLs, no maintainer or author fields, no license text
values, no package-manager stdout/stderr, no shell output, no environment values, and no
credentials.

## Ecosystem Parser Plan

Future parser behavior should be deliberately shallow:

- `package.json`: count dependency sections such as `dependencies`, `devDependencies`,
  `peerDependencies`, and `optionalDependencies`; count script keys; do not return script names,
  script values, package names, dependency names, dependency version constraints, repository URLs,
  registry URLs, maintainers, or authors.
- `pyproject.toml`: count dependency arrays and dependency group entries when parseable; do not
  return project names, dependency names, version constraints, repository URLs, authors, or scripts.
- `go.mod`: count required module lines when parseable; do not return module path or dependency
  module names.
- `Cargo.toml`: count dependency table entries when parseable; do not return crate names, version
  constraints, repository URLs, authors, or build-script values.
- `pom.xml`: count dependency elements when parseable; do not return group IDs, artifact IDs,
  versions, repositories, plugin coordinates, or XML text.
- `build.gradle`: report parse status only or shallow count evidence if a deliberately tiny parser is
  approved; do not execute Gradle, evaluate scripts, or return dependency coordinates.
- `requirements.txt`: count non-comment requirement-like lines only; do not return package names,
  version constraints, URLs, or index options.
- `Gemfile`: count requirement-like lines only; do not return gem names, version constraints, source
  URLs, or group names.
- `composer.json`: count dependency section keys only; do not return package names, version
  constraints, repository URLs, author fields, or script values.

Malformed manifests must return safe parse status or safe failure without echoing raw manifest text.

## Privacy And Redaction Plan

Project manifest metadata can leak internal package names, private services, customer names, private
registry URLs, repository URLs, install scripts, maintainer identities, and dependency-vulnerability
context. The first implementation must therefore be count-oriented.

Required privacy choices:

- no file contents;
- no package script names or values;
- no dependency names;
- no package version constraints;
- no registry URLs;
- no repository URLs;
- no maintainer, author, project, module, group, artifact, crate, gem, or package name fields;
- no stable cross-response package identifiers;
- no manifest text excerpts;
- no raw parse errors that echo source text.

If a later reviewed mode wants dependency names, script names, repository URLs, package identifiers,
or stable package hashes, it must define a separate privacy contract, source-review packet, UI
warning model, audit wording, and accepted-risk update.

## Policy Fixture Plan

Future policy fixtures must prove:

- read-capable principal and in-scope workspace manifest metadata returns `allow`;
- read-only/auditor principal remains read-only under the existing role matrix;
- unknown, disabled, or spoofed principals deny before execution;
- disabled, unknown, or out-of-scope workspaces deny before execution;
- traversal or hidden/sensitive roots deny before policy execution when appropriate;
- write, network, destructive, approval, and patch proposal obligations are not introduced;
- policy preview and runtime resource evidence are comparable.

No policy rule is added in this planning sprint.

## Audit Evidence Plan

Future audit metadata should include:

- tool name, manifest hash/version, and schema version;
- normalized principal and session ID;
- workspace ID and normalized root resource evidence;
- requested manifest kinds and effective manifest kinds;
- manifest count and truncation flag;
- manifest kind counts;
- parser success/failure counts and safe failure reasons;
- output-policy flags for file contents, dependency names, script names, script values, registry
  access, network access, and package-manager execution;
- size limit, file count limit, and runtime limit status;
- policy version/hash, matched rules, and obligations.

It must not include raw manifest file contents, dependency names, package names, script names,
script values, registry URLs, repository URLs, package-manager output, parse text excerpts,
environment values, credentials, or command output.

## UI And Policy Preview Plan

Future UI/review behavior should:

- show the tool in registered tools only after a manifest is intentionally added later;
- show read risk, project category, workspace scope, and bounded-output warnings;
- show policy preview evidence for principal, workspace, root, manifest kinds, resource scope,
  decision, matched rules, obligations, and output-policy expectations;
- display output-policy flags that raw contents, dependency names, script names, script values, and
  registry/network access are not included;
- expose no package-manager controls, registry controls, execution controls, or broad scan controls.

## Negative Transcript Plan

Future negative transcripts or tests must cover:

- parent traversal root denial;
- absolute root denial;
- hidden/sensitive root denial;
- symlinked root or manifest denial;
- hardlinked manifest denial where the filesystem contract requires it;
- arbitrary manifest filename denial;
- recursive glob denial;
- `include_file_contents` denial;
- `include_script_values` denial;
- `include_dependency_names` denial;
- `registry_url` denial;
- `command` or `argv` denial;
- oversized manifest safe failure;
- malformed JSON/TOML/XML safe failure;
- binary or invalid UTF-8 manifest safe failure;
- private registry URL field not returned;
- dependency names not returned;
- script values not returned;
- safe error output with no file contents, credentials, environment, raw parser excerpts, or
  package-manager output.

## Resource Limits

Initial planning limits:

- maximum manifest summaries returned: `20`;
- maximum manifest file size parsed: `131072` bytes;
- maximum total parsed bytes: `262144` bytes;
- maximum output bytes: `131072`;
- maximum executor runtime: `5` seconds;
- no binary/content-bearing output by construction;
- no recursive directory traversal.

These are planning defaults and must be revalidated during implementation review.

## Source Review And Implementation Decision Requirement

Before implementation begins, a later source review must approve an implementation decision. That
later implementation sprint must produce source-level review artifacts for:

- manifest and lock update;
- executor implementation;
- schema validation;
- parser behavior;
- policy preview/runtime parity;
- audit evidence;
- MCP exposure;
- UI/tool-list evidence;
- negative transcripts and focused tests;
- no-new-powers evidence;
- tool-surface evidence.

Actual implementation remains blocked until that later source review and implementation decision are
explicitly approved.

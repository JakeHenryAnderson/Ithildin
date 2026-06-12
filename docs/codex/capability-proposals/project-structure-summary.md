# Capability Proposal: project.structure.summary

Status: design-only proposal. This document does not add a tool manifest, does not add an
executor, does not add policy rules, does not add MCP exposure, does not add API behavior, does not
add UI behavior, and does not add runtime behavior.

Boundary shorthand: does not add an executor; does not add UI behavior.

`project.structure.summary` is the next proposed narrow read-only metadata capability after the
consolidated four-tool project intelligence slice. It would summarize bounded workspace structure
without exposing file contents, raw recursive listings, dependency names, package names, package
versions, package script names or values, lockfile contents, registry URLs, source code, or raw
sensitive paths.

Design boundary: structural counts and allowlisted labels only.

## Intended Behavior

The proposed tool would inspect a trusted workspace root or a bounded workspace-relative root using
the existing filesystem safety contract. It would return aggregate structural metadata only.

Proposed output categories:

- total visible directory count and file count within configured depth and item limits;
- top-level safe directory category counts, such as source, tests, docs, config, build output,
  generated, vendor, and unknown;
- safe extension or file-kind counts using allowlisted labels, such as markdown, Python,
  TypeScript, JSON, TOML, YAML, lockfile-present, and unknown;
- ignored/denied/skipped counts for hidden paths, sensitive paths, `.git`, symlinks, hardlinks,
  binary or unsupported entries, oversized traversal, depth limits, and item limits;
- truncation and capability evidence;
- output policy booleans proving file contents, raw directory listings, dependency names, script
  values, registry URLs, and network access were not included.

## Non-Goals

The proposal explicitly preserves:

- no file contents;
- no raw recursive listing;
- no raw sensitive paths;
- no stable cross-response path identifiers;
- no dependency names;
- no package names;
- no package version constraints;
- no package script names or values;
- no lockfile contents;
- no code search;
- no symbol extraction;
- no package-manager execution;
- no registry or network access;
- no shell;
- no broad filesystem writes, deletes, moves, chmod, or archive extraction;
- no sandbox, SIEM, compliance, SBOM, vulnerability, or license claims.

If a later review concludes raw filenames, source snippets, symbol names, package names, dependency
names, package-manager execution, or network-backed metadata are necessary for usefulness,
implementation must stop and a different proposal must be written.

## Proposed Input Shape

A future implementation plan may propose:

- `workspace_id`: optional trusted workspace selector;
- `root`: optional workspace-relative root, subject to existing path-safety rules;
- `max_depth`: bounded integer using a strict configured maximum;
- `limit`: bounded maximum entries to inspect;
- `include_categories`: optional allowlist of safe categories.

The future schema must use `additionalProperties: false`, reject caller-controlled globs or regexes,
reject absolute paths, reject path traversal, reject URL-encoded path ambiguity, reject control
characters, reject symlink or hardlink traversal, and preserve the existing workspace-root
confinement model.

## Proposed Output Shape

A future output schema may include:

- `tool_name`;
- `workspace_id`;
- `root_label`;
- `summary`: safe counts only;
- `directory_categories`;
- `file_kind_counts`;
- `skipped_counts`;
- `limits`;
- `truncated`;
- `output_policy`.

The output must not include raw source paths beyond already-reviewed resource labels, file
contents, raw dependency names, package names, script names or values, registry URLs, raw exception
messages, or raw filesystem errors.

## Policy And Audit Evidence

The proposed resource type is `project_structure`, with read risk and project category. Runtime and
policy preview must construct the same normalized resource shape before policy evaluation.

Audit evidence must be safe count-only metadata: workspace ID, normalized resource, requested root
label, max depth, limit, directory category keys, file-kind keys, skipped count keys, truncation
state, output policy booleans, policy hash, manifest hash, and request hash. It must not include
file contents, raw recursive listings, raw sensitive paths, raw file names, dependency names,
versions, script values, registry URLs, or environment values.

## UI/review evidence

If implemented later, the review console may show compact structural counts and skipped/truncated
warnings. It must not render raw recursive listings, raw sensitive paths, file contents, source
snippets, dependency names, package names, or package script values.

## Negative Transcripts

A later implementation packet must include denial or safe-output transcripts for:

- traversal and absolute paths;
- hidden/sensitive paths and `.git`;
- symlink and hardlink entries;
- control-character and Unicode-normalization path ambiguity;
- binary or unsupported entries;
- oversized/deep directory trees;
- broad recursive listing requests;
- caller-provided globs or regexes;
- attempts to request file contents, package names, dependency names, scripts, or network metadata.

## Resource limits

A future implementation must define hard limits for:

- maximum depth;
- maximum inspected entries;
- maximum output categories;
- maximum output bytes;
- timeout;
- skipped-entry evidence.

The executor must fail closed or return truncated safe counts without leaking raw file contents or
raw sensitive paths.

## Accepted-risk impact

This proposal does not close accepted deferred risks and does not approve public/security-product
positioning. It adds planning pressure to the metadata privacy policy because even directory and
file-kind metadata can reveal project intent. A future implementation decision must explicitly
record that residual local-preview risk.

## No-new-powers analysis

The proposal remains inside the read-only local metadata contract. It does not add shell execution,
Docker socket access, Kubernetes tools, browser automation, arbitrary HTTP, broad filesystem
writes, package-manager execution, registry/network access, remote MCP, production identity,
runtime Postgres, hosted telemetry, plugin SDK work, or sandbox orchestration.

## Review Requirements

Before implementation, this capability needs:

- implementation-planning packet;
- filesystem traversal and output-category contract;
- policy fixtures and parity evidence;
- audit fields;
- UI/review evidence;
- negative transcripts;
- resource limits;
- accepted-risk impact;
- no-new-powers analysis;
- focused source-review handoff;
- explicit implementation decision.

External/source Review Requirement: a source reviewer must verify that any future implementation is
still count-only, local, read-only, workspace-confined, safe-error-only, and free of shell,
package-manager execution, network access, file contents, and raw recursive listing exposure before
the lane can close.

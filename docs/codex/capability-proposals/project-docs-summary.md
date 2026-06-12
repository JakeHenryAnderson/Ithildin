# Capability Proposal: project.docs.summary

Status: design-only proposal. This document does not add a tool manifest, does not add an
executor, does not add policy rules, does not add MCP exposure, does not add API behavior, does not
add UI behavior, and does not add runtime behavior.

Boundary shorthand: count-only documentation metadata and allowlisted labels only.

`project.docs.summary` is the next proposed narrow read-only project-intelligence capability after
`project.structure.summary`. It would summarize bounded documentation-related workspace structure without
exposing documentation file names, raw paths, file contents, documentation bodies, package scripts, dependency names,
package names, coverage data, pass/fail state, command output, registry URLs, or network-derived
metadata.

## Intended Behavior

The proposed tool would inspect a trusted workspace root or bounded workspace-relative root using
the existing filesystem safety contract. It would infer broad documentation metadata from safe path and
extension categories only, never by executing documentation or reading documentation file contents.

Proposed output categories:

- total visible documentation-like directory count and documentation-like file count within configured depth and item
  limits;
- allowlisted documentation-type counts, such as `reference_docs`, `api_docs`,
  `tutorial_docs`, `how_to_docs`, `changelog_docs`, `license_docs`,
  `contributing_docs`, and `unknown_docs`;
- allowlisted documentation-location counts, such as `dedicated_docs_directory`, `source_adjacent_docs`,
  `documentation_example`, and `unknown_location`;
- safe extension or language-family counts;
- skipped counts for hidden paths, sensitive paths, `.git`, symlinks, hardlinks, binary or
  unsupported entries, depth limits, item limits, and safe errors;
- truncation, resource-limit, and output-policy evidence.

## Non-Goals

The proposal explicitly preserves:

- no documentation file names;
- no raw paths;
- no raw recursive listing;
- no stable cross-response path identifiers;
- no file contents;
- no documentation headings;
- no source snippets;
- no dependency names;
- no package names;
- no package script names or values;
- no coverage data;
- no documentation pass/fail claims;
- no documentation build execution;
- no command discovery;
- no package-manager execution;
- no registry or network access;
- no shell;
- no broad filesystem writes, deletes, moves, chmod, or archive extraction;
- no sandbox, SIEM, compliance, SBOM, vulnerability, or license claims.

If a later review concludes raw filenames, documentation headings, file contents, package scripts, dependency
names, command execution, package-manager execution, or network-backed metadata are necessary for
usefulness, implementation must stop and a different proposal must be written.

## Proposed Input Shape

A future implementation plan may propose:

- `workspace_id`: optional trusted workspace selector;
- `root`: optional workspace-relative root, subject to existing path-safety rules;
- `max_depth`: bounded integer using a strict configured maximum;
- `limit`: bounded maximum entries to inspect;
- `include_categories`: optional allowlist of safe output categories.

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
- `documentation_type_counts`;
- `documentation_location_counts`;
- `language_family_counts`;
- `skipped_counts`;
- `limits`;
- `truncated`;
- `output_policy`.

The output must not include documentation file names, raw paths, file contents, documentation headings, source
snippets, dependency names, package names, script names or values, registry URLs, raw exception
messages, or raw filesystem errors.

## Policy And Audit Evidence

The proposed resource type is `project_docs`, with read risk and project category. Runtime and
policy preview must construct the same normalized resource shape before policy evaluation.

Audit evidence must be safe count-only metadata: workspace ID, normalized resource, requested root
label, max depth, limit, documentation-type keys, documentation-location keys, language-family keys, skipped
count keys, truncation state, output-policy booleans, policy hash, manifest hash, and request hash.
It must not include raw paths, filenames, file contents, documentation headings, dependency names, package
names, package scripts, coverage data, command output, registry URLs, environment values, or raw
filesystem errors.

## UI/review evidence

If implemented later, the review console may show compact documentation-summary counts and
skipped/truncated warnings. It must not render raw paths, filenames, documentation headings, file contents,
source snippets, dependency names, package names, package script values, command output, coverage
results, or pass/fail claims.

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
- attempts to request file names, file contents, documentation headings, package names, dependency names,
  scripts, coverage, execution, or network metadata.

## Resource limits

A future implementation must define hard limits for:

- maximum depth;
- maximum inspected entries;
- maximum output categories;
- maximum output bytes;
- timeout;
- skipped-entry evidence.

The executor must fail closed or return truncated safe counts without leaking raw paths, filenames,
file contents, documentation headings, command output, or raw sensitive paths.

## Accepted-risk impact

This proposal does not close accepted deferred risks and does not approve public/security-product
positioning. It adds planning pressure to the metadata privacy policy because even count-only docs
metadata can reveal project maturity, language family, or development workflow. A future
implementation decision must explicitly record that residual local-preview risk.

## No-new-powers analysis

The proposal remains inside the read-only local metadata contract. It does not add shell execution,
Docker socket access, Kubernetes tools, browser automation, arbitrary HTTP, broad filesystem
writes, package-manager execution, registry/network access, remote MCP, production identity,
runtime Postgres, hosted telemetry, plugin SDK work, sandbox orchestration, documentation build execution, or
coverage collection.

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
package-manager execution, network access, documentation build execution, file contents, documentation headings, raw paths,
and raw recursive listing exposure before the lane can close.

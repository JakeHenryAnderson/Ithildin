# Implementation-Planning Packet: project.structure.summary

Status: implementation-planning only. This planning packet does not add a tool manifest, does not
add an executor, does not add policy rules, does not add MCP exposure, does not add API behavior,
does not add UI behavior, and does not add runtime behavior. Implementation state: blocked.

## Future Manifest Sketch

A future manifest may define `project.structure.summary` as `risk: read`, category `project`, and
MCP-exposed only after a separate implementation decision. The future input schema must keep
`additionalProperties: false` and may include only bounded fields such as `workspace_id`, `root`,
`max_depth`, `limit`, and `include_categories`.

## Proposed Input Contract

Inputs must resolve through the workspace registry and existing filesystem path-safety rules. The
future executor must reject traversal, absolute paths, URL-encoded path ambiguity, control
characters, symlink traversal, hardlink ambiguity, hidden/sensitive paths, `.git` internals,
caller-controlled globs, caller-controlled regexes, broad recursive listing requests, unsupported
platform profiles, and roots outside the selected workspace.

## Proposed Output Contract

Output remains structural counts and allowlisted labels only:

- total visible directory and file counts within configured depth and item limits;
- directory category counts, such as source, tests, docs, config, generated, vendor, build output,
  and unknown;
- file-kind or extension category counts using allowlisted labels;
- skipped count keys for hidden/sensitive paths, `.git`, symlinks, hardlinks, unsupported entries,
  depth limits, item limits, and traversal denials;
- truncation and output policy booleans for excluded sensitive categories.

It must include no file contents, no raw recursive listing, no raw sensitive paths, no raw file
names, no stable cross-response path identifiers, no dependency names, no package names, no package
version constraints, no package script names or values, no lockfile contents, no code search, no
symbol extraction, no package-manager stdout/stderr, no registry URLs, no package-manager
execution, and no network access.

Boundary shorthand: no raw file names; no package-manager execution.

## Filesystem Traversal Contract

Future traversal code must reuse the existing filesystem executor contract: workspace-root
confinement, relative paths only, hidden/sensitive path denial, `.git` denial, symlink denial,
hardlink denial, UTF-8-safe metadata handling, bounded directory walking, deterministic skipped
counts, same safe-error behavior, and macOS/Linux local-preview support only.

The executor must not follow symlinks, must not cross workspace roots, must not inspect file
contents to infer project structure, and must not expose raw filesystem errors.

## Category And Extension Allowlist

Future implementation must define a fixed category map before runtime work begins. The map should
be conservative and reviewable:

- directory categories: source, tests, docs, config, generated, vendor, build output, unknown;
- file-kind categories: markdown, Python, TypeScript, JavaScript, JSON, TOML, YAML, lockfile
  present, config, unknown.

Unknown categories must aggregate as `unknown`; they must not create caller- or repository-derived
output keys that reveal raw names.

## Policy Fixture Plan

Add fixtures for allowed in-scope read principals, denied out-of-scope resources, denied unknown or
disabled principals, schema failures before policy, and parity between policy preview and runtime
resource construction for resource type `project_structure`.

## Audit Evidence Plan

Audit fields should record only safe metadata: tool name, workspace ID, resource type, root label,
max depth, limit, category keys, file-kind keys, skipped count keys, truncation state, output
policy booleans, policy hash, manifest hash, schema hash, request hash, and principal ID. No file
contents, raw recursive listings, raw sensitive paths, raw file names, dependency names, package
names, scripts, registry URLs, environment values, or raw filesystem errors may be audited.

## UI And Policy Preview Plan

Review-console display may show compact count summaries and skipped/truncated warnings only. It
must not add mutation controls, recursive browsing, file-content preview, source-code search,
package lookup, dependency browsing, vulnerability claims, compliance conclusions, sandbox
controls, or SIEM controls.

Policy preview must use the same normalized resource fields as runtime and must fail safely on
schema or principal/workspace denials without leaking raw requested paths.

## Negative Transcript Plan

Future negative transcripts should cover traversal, absolute paths, hidden/sensitive paths, `.git`,
symlink entries, hardlink entries, control-character paths, Unicode-normalization ambiguity,
unsupported platform profile, broad recursive listing request, caller-provided glob, caller-provided
regex, oversized/deep directory tree, raw file-name request, file-content request, dependency-name
request, package script request, package-manager execution request, registry/network request, and
unknown principal.

## Resource Limits

The future implementation must define maximum depth, maximum inspected entries, maximum output
categories, maximum output bytes, timeout, skipped-entry evidence, and truncation behavior before
runtime work begins.

## Source Review And Implementation Decision Requirement

Actual implementation remains blocked until this plan is approved by the capability proposal gates,
a focused source-review handoff is generated, no-new-powers evidence remains clean, and an explicit
implementation decision is recorded for this one bounded read-only structure-summary capability.

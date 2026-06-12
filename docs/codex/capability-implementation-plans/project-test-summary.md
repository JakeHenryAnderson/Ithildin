# Implementation-Planning Packet: project.test.summary

Status: implementation-planning only. This planning packet does not add a tool manifest, does not
add an executor, does not add policy rules, does not add MCP exposure, does not add API behavior,
does not add UI behavior, and does not add runtime behavior. Implementation state: blocked.

## Future Manifest Sketch

A future manifest may define `project.test.summary` as `risk: read`, category `project`, and
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

Output remains count-only test metadata and allowlisted labels only:

- visible test-like directory and file counts within configured depth and item limits;
- framework hint counts, such as Python pytest, Python unittest, JavaScript, TypeScript, Go, Rust,
  Java, and unknown;
- test-location counts, such as dedicated test directory, source-adjacent test, documentation
  example, and unknown location;
- language-family counts using allowlisted labels;
- skipped count keys for hidden/sensitive paths, `.git`, symlinks, hardlinks, unsupported entries,
  depth limits, item limits, and traversal denials;
- truncation and output policy booleans for excluded sensitive categories.

It must include no test file names, no raw paths, no raw recursive listing, no stable
cross-response path identifiers, no file contents, no test case names, no source snippets, no
dependency names, no package names, no package script names or values, no coverage data, no
pass/fail claims, no command output, no package-manager stdout/stderr, no registry URLs, no
package-manager execution, no test execution, and no network access.

Boundary shorthand: no test file names; no dependency names; no test execution; no package-manager execution.

## Filesystem Traversal Contract

Future traversal code must reuse the existing filesystem executor contract: workspace-root
confinement, relative paths only, hidden/sensitive path denial, `.git` denial, symlink denial,
hardlink denial, UTF-8-safe metadata handling, bounded directory walking, deterministic skipped
counts, same safe-error behavior, and macOS/Linux local-preview support only.

The executor must not follow symlinks, must not cross workspace roots, must not inspect file
contents to infer test metadata, must not execute tests, and must not expose raw filesystem errors.

## Category And Extension Allowlist

Future implementation must define fixed category maps before runtime work begins. The maps should
be conservative and reviewable:

- framework hints: `python_pytest_hint`, `python_unittest_hint`, `javascript_test_hint`,
  `typescript_test_hint`, `go_test_hint`, `rust_test_hint`, `java_test_hint`, and
  `unknown_test_hint`;
- test locations: `dedicated_test_directory`, `source_adjacent_test`, `documentation_example`, and
  `unknown_location`;
- language families: `python`, `typescript`, `javascript`, `go`, `rust`, `java`, `shell`,
  `markdown`, and `unknown`.

Unknown categories must aggregate as `unknown` or `unknown_*`; they must not create caller- or
repository-derived output keys that reveal raw names.

## Policy Fixture Plan

Add fixtures for allowed in-scope read principals, denied out-of-scope resources, denied unknown or
disabled principals, schema failures before policy, and parity between policy preview and runtime
resource construction for resource type `project_tests`.

## Audit Evidence Plan

Audit fields should record only safe metadata: tool name, workspace ID, resource type, root label,
max depth, limit, framework hint keys, test-location keys, language-family keys, skipped count
keys, truncation state, output policy booleans, policy hash, manifest hash, schema hash, request
hash, and principal ID. No raw paths, file names, file contents, test names, dependency names,
package names, scripts, command output, coverage data, registry URLs, environment values, or raw
filesystem errors may be audited.

## UI And Policy Preview Plan

Review-console display may show compact count summaries and skipped/truncated warnings only. It
must not add mutation controls, test execution controls, recursive browsing, file-content preview,
test-name display, source-code search, package lookup, dependency browsing, vulnerability claims,
coverage claims, compliance conclusions, sandbox controls, or SIEM controls.

Policy preview must use the same normalized resource fields as runtime and must fail safely on
schema or principal/workspace denials without leaking raw requested paths.

## Negative Transcript Plan

Future negative transcripts should cover traversal, absolute paths, hidden/sensitive paths, `.git`,
symlink entries, hardlink entries, control-character paths, Unicode-normalization ambiguity,
unsupported platform profile, broad recursive listing request, caller-provided glob, caller-provided
regex, oversized/deep directory tree, raw file-name request, file-content request, test-name
request, package script request, package-manager execution request, test execution request,
coverage request, registry/network request, and unknown principal.

## Resource Limits

The future implementation must define maximum depth, maximum inspected entries, maximum output
categories, maximum output bytes, timeout, skipped-entry evidence, and truncation behavior before
runtime work begins.

## Source Review And Implementation Decision Requirement

Actual implementation remains blocked until this plan is approved by the capability proposal gates,
a focused source-review handoff is generated, no-new-powers evidence remains clean, and an explicit
implementation decision is recorded for this one bounded read-only test-summary capability.

# Implementation-Planning Packet: project.release.summary

Status: implementation-planning only. This document does not add a tool manifest, executor,
policy rule, API/MCP behavior, approval behavior, UI behavior, or runtime behavior. It converts
the accepted design-only proposal into an implementation checklist for a later explicit
implementation decision.

This planning sprint does not add a manifest.

Implementation state: blocked.
Policy preview/runtime resource parity remains a later gating requirement.

## Future Manifest Sketch

If approved later, the manifest would define:

- name: `project.release.summary`;
- risk: `read`;
- category: `project`;
- MCP exposure: read-only, governed path only;
- input schema: closed object with `workspace_id`, `root`, `max_depth`, `limit`, and optional safe
  category filters;
- output schema: count-only release posture labels, skipped counts, limit metadata, and
  output-policy flags.

No manifest is added in this planning sprint.

## Proposed Input Contract

Future inputs should be bounded:

- `workspace_id`: known enabled workspace;
- `root`: relative path only, default `.`;
- `max_depth`: small bounded integer;
- `limit`: small bounded integer;
- `include_categories`: optional allowlist of safe aggregate sections such as `artifact`,
  `changelog`, `version_marker`, `automation`, and `location`.

The schema must use `additionalProperties: false` and reject malformed, oversized, traversal,
absolute, encoded-ambiguous, hidden/sensitive, symlink, and hardlink inputs through the same
workspace-confined project metadata patterns.

## Proposed Output Contract

The future output must contain only safe counts and allowlisted labels:

- release artifact and config counts;
- release-note and changelog counts by coarse category;
- version-marker counts by coarse source category;
- release automation/config counts;
- location-bucket counts;
- skipped counts;
- limits/truncation metadata;
- output-policy flags.

It must not include release names, version strings that reveal product/customer cadence, changelog
contents, tag names, branch names, package names, dependency names, author/maintainer names, raw
paths, file contents, shell output, Git output, package-manager output, registry URLs, raw parser
errors, or CI output.

## Future Traversal Contract

Future traversal must stay workspace-confined and use the existing project metadata safety
posture:

- relative roots only;
- no broad recursive listing output;
- deny `.git`, hidden/sensitive paths, symlinks, hardlinks, unsupported file types, binary/NUL
  content, oversized files, and unsupported encodings;
- respect `max_depth`, `limit`, and output-size caps;
- inspect only candidate release config files and directories by allowlisted location/name
  patterns;
- never execute files, Git commands, package managers, CI tools, shell commands, or network
  requests.

## Future Category Allowlist

Category labels should be coarse and non-sensitive:

- release artifact categories: `release_config`, `release_manifest`, `unknown_release_artifact`;
- changelog categories: `release_note`, `unknown_changelog`;
- version-marker categories: `source_version_marker`, `unknown_version_marker`;
- automation/config categories: `release_automation`, `release_config`, `unknown_release_config`;
- location buckets: `release_directory`, `changelog_directory`, `config_directory`,
  `source_adjacent`, `unknown_location`.

Any future structural parsing must avoid release names, version strings, tag names, branch names,
package names, dependency names, author/maintainer names, raw paths, and content emission.

## Future Skipped-Count Behavior

Skipped counts should distinguish safe rejection or truncation reasons such as:

- hidden or sensitive path;
- `.git`;
- symlink;
- hardlink;
- unsupported file type;
- binary or NUL content;
- invalid or unsupported encoding;
- depth limit;
- item limit;
- parse or normalize failure;
- safe error;
- output truncation.

Skipped counts must remain count-only and must not echo release names, file contents, paths, or
command output.

## Policy Preview / Runtime Resource Parity

Policy fixtures must prove:

- read-capable principals can preview/call `project.release.summary` on an in-scope workspace;
- unknown, disabled, or out-of-scope principals are denied safely;
- policy preview and runtime construct matching `project_release` resources;
- dangerous, destructive, and default-deny policy behavior remains unchanged.

## Future Audit Metadata

Audit fields should record only safe metadata: tool name, workspace ID, resource type, selected
root label, selected categories, release artifact counts, release-note counts, version-marker
counts, automation/config counts, skipped counts, truncation state, limit metadata, policy hash,
manifest hash, request hash, principal ID, and output-policy booleans.

No release names, version strings, changelog contents, tag names, branch names, package names,
dependency names, author/maintainer names, raw paths, file contents, or registry/network values
may be audited.

## Future MCP Exposure Expectations

MCP exposure must remain read-only through the governed path only after the later implementation
decision. The tool must not add shell access, package-manager access, Git execution, CI execution,
network access, or any broader API surface.

## Future Source-Review Bundle Requirements

A later source-review bundle must include:

- implementation decision record;
- focused source files;
- focused tests;
- policy parity fixtures;
- audit evidence;
- negative transcripts;
- no-new-powers evidence;
- release/readiness gate outputs;
- command evidence for proposal and implementation-plan checks.

## Future Negative Tests

The future test plan should cover traversal denial, absolute-root denial, hidden/sensitive path
denial, `.git` denial, symlink/hardlink denial, malformed input denial, oversized input denial,
depth/item limit truncation, unsupported shapes returning safe unknown labels, release names not
emitted, version strings not emitted when they reveal cadence, changelog contents not emitted,
unauthorized principals, and output-policy flags proving suppressed categories stay suppressed.

## Resource Limits

The future implementation must set explicit bounds for:

- maximum depth;
- maximum candidate files;
- maximum inspected bytes per candidate;
- maximum output sections;
- maximum output bytes;
- timeout or inspection budget where applicable.

Limit failures and truncation must be safe and must not leak raw paths, file contents, release
names, version strings, changelog text, tag names, branch names, package names, dependency names,
author/maintainer names, parser stack traces, or filesystem errors.

## Source Review And Implementation Decision Requirement

Actual implementation remains blocked. A future implementation-boundary sprint must add an
implementation decision document, update the manifest lock, implement tests, update policy parity
fixtures, produce negative transcripts, generate a source-review bundle, and pass release/readiness
gates before the tool can be considered for local-preview runtime use.

The future implementation must preserve the strict non-goals: no release names, no release version strings when they reveal product/customer cadence, no changelog contents, no tag names, no branch names, no package names, no dependency names, no author or maintainer names, no raw paths, no file contents, no Git execution, no shell, no package-manager execution, no CI execution, no registry or network access, no deployment-readiness claims, no legal claims, no compliance claims, and no broad recursive listings.

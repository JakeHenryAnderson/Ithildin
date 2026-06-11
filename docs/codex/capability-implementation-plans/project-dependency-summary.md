# Implementation-Planning Packet: project.dependency.summary

Status: implementation-planning only. This planning packet does not add a tool manifest, does not
add an executor, does not add policy rules, does not add MCP exposure, does not add API behavior,
does not add UI behavior, and does not add runtime behavior. Implementation state: blocked.

## Future Manifest Sketch

A future manifest may define `project.dependency.summary` as `risk: read`, category `project`, and
MCP-exposed only after a separate implementation decision. The future input schema must keep
`additionalProperties: false` and may include only bounded fields such as `workspace_id`, `root`,
`manifest_kinds`, and `limit`.

## Proposed Input Contract

Inputs must resolve through the workspace registry and existing filesystem path-safety rules.
The future executor must reject traversal, absolute paths, symlinks, hardlinks, hidden/sensitive
paths, unsupported encodings, oversized manifests, arbitrary manifest filenames, caller-controlled
parser choices, and recursive discovery outside the reviewed selection model.

## Proposed Output Contract

Output remains count-only:

- direct dependency counts grouped by manifest kind, ecosystem, and dependency section;
- manifest parser status counts;
- truncation and unsupported-manifest evidence;
- output policy booleans for excluded sensitive categories.

It must include no file contents, no dependency names, no package names, no package version
constraints, no package script names or values, no lockfile contents, no registry URLs, no repository
URLs, no package-manager stdout/stderr, and no stable cross-response package identifiers. It must
preserve no package version constraints, no package-manager execution, and no network access.

## Parser Contract Checklist

Future parser code must be deterministic, stdlib or already-approved dependency only, bounded by
byte and manifest-count limits, and safe on malformed manifests. It must not execute package
managers, run lifecycle scripts, invoke shell, resolve transitive dependencies, contact registries,
fetch remotes, or infer license/vulnerability/compliance status.

## Policy Fixture Plan

Add fixtures for allowed in-scope read principals, denied out-of-scope resources, denied unknown or
disabled principals, schema failures before policy, and parity between policy preview and runtime
resource construction.

## Audit Evidence Plan

Audit fields should record only safe metadata: tool name, workspace ID, resource type, manifest kind
counts, dependency section keys, truncation state, parser status counts, policy hash, manifest hash,
schema hash, request hash, principal ID, and output policy booleans. No dependency names, versions,
scripts, raw manifest content, or registry URLs may be audited.

## UI And Policy Preview Plan

Review-console display may show aggregate counts and warnings only. It must not add mutation
controls, dependency browsing, package lookup, vulnerability claims, or compliance conclusions.

## Negative Transcript Plan

Future negative transcripts should cover unsupported manifest kind, malformed manifest, oversized
manifest, hidden/sensitive path, symlink/hardlink path, traversal, lockfile body request, dependency
name request, package-manager execution request, registry/network request, and unknown principal.

## Resource Limits

The future implementation must define manifest count, total bytes, per-file bytes, section count,
and output-size caps before runtime work begins.

## Source Review And Implementation Decision Requirement

Actual implementation remains blocked until this plan is approved by the capability proposal gates,
a focused source-review handoff is generated, no-new-powers evidence remains clean, and an explicit
implementation decision is recorded for this one bounded read-only count-only capability.

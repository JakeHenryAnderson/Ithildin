# Capability Proposal: project.dependency.summary

Status: design-only proposal. This document does not add a tool manifest, does not add an
executor, does not add policy rules, does not add MCP exposure, does not add API behavior, does not
add UI behavior, and does not add runtime behavior. It does not add an executor. It does not add UI
behavior. It does not add UI behavior.

`project.dependency.summary` is the next proposed narrow read-only metadata capability after
`project.manifest.summary`. It would summarize direct dependency counts from reviewed project
manifest files without exposing package names, dependency names, versions, script values, lockfile
contents, registry URLs, repository URLs, or source files.

Design boundary: direct dependency counts only.

## Intended Behavior

The proposed tool would inspect only allowlisted manifest kinds already covered by the
project-manifest lane, such as `package.json`, `pyproject.toml`, `requirements.txt`, `go.mod`,
`Cargo.toml`, `pom.xml`, `build.gradle`, `Gemfile`, and `composer.json`. It would return count-only
metadata grouped by manifest kind, ecosystem, and dependency section.

Proposed output categories:

- manifest count and parser status count;
- ecosystem count;
- direct dependency count by section, such as runtime, development, optional, peer, build, and test;
- truncation, unsupported-manifest, malformed-manifest, and limit evidence;
- output policy booleans proving dependency names, versions, script values, lockfile bodies,
  registry URLs, and network access were not included.

## Non-Goals

The proposal explicitly preserves:

- no dependency names;
- no package names;
- no package version constraints;
- no package script names or values;
- no file contents;
- no lockfile contents;
- no transitive dependency resolution;
- no license, vulnerability, SBOM, or compliance claims;
- no package-manager execution;
- no registry or network access;
- no shell;
- no recursive discovery beyond the future reviewed manifest-selection contract;
- no stable cross-response package identifiers.

If a later review concludes dependency names, versions, lockfile parsing, package-manager execution,
network access, or license/vulnerability analysis are necessary for usefulness, implementation must
stop and a different proposal must be written.

## Proposed Input Shape

A future implementation plan may propose:

- `workspace_id`: optional trusted workspace selector;
- `root`: optional workspace-relative root, subject to existing path-safety rules;
- `manifest_kinds`: optional allowlist filter;
- `limit`: bounded maximum manifests to summarize.

The future schema must use `additionalProperties: false`, reject caller-controlled parsers, reject
arbitrary manifest filenames, reject lockfile body requests, and preserve the existing
workspace-root confinement model.

## Policy And Audit Evidence

The proposed resource type is `project_dependencies`, with read risk and project category. Runtime
and policy preview must construct the same normalized resource shape before policy evaluation.

Audit evidence must be safe count-only metadata: workspace ID, normalized resource, manifest kind
counts, dependency section count keys, truncation state, parser status counts, output policy
booleans, policy hash, manifest hash, and request hash. It must not include dependency names,
versions, script values, file contents, raw paths beyond already-reviewed resource labels, or
registry URLs.

## Review Requirements

Before implementation, this capability needs:

- implementation-planning packet;
- parser contract and manifest allowlist;
- policy fixtures and parity evidence;
- audit fields;
- UI/review evidence;
- negative transcripts;
- resource limits;
- accepted-risk impact;
- no-new-powers analysis;
- focused source-review handoff;
- explicit implementation decision.

External/source Review Requirement: a source reviewer must verify that the implementation is still
count-only, manifest-derived, local, read-only, and free of package-manager execution or network
access before the lane can close.

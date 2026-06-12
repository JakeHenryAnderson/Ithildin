# Read-Only Project Intelligence

Status: consolidated local-preview product slice. This document does not add runtime behavior,
tool manifests, policy rules, MCP exposure, API behavior, UI behavior, or new governed tool powers.

Read-only project intelligence is Ithildin's current safe orientation layer for local agent work. It
lets an agent learn bounded, policy-mediated facts about a workspace without receiving shell access,
package-manager execution, broad filesystem writes, raw diffs, dependency names, package names,
package versions, package script names or values, file contents, lockfile contents, registry output,
or network-derived package metadata.

No file contents, no dependency names, no package-manager execution, and no registry/network access
are part of this product slice.

## Current Tool Family

| Tool | Purpose | Boundary |
| --- | --- | --- |
| `git.show.commit_metadata` | Read one local commit/ref's bounded metadata. | No checkout, remote fetch, arbitrary Git command, raw diff, or file contents. |
| `git.show.ref_summary` | Summarize local branches/tags using safe counts and response-local IDs. | No ref names in output by default, no remote refs, no checkout, and no arbitrary Git command. |
| `project.manifest.summary` | Summarize root project manifests with count-oriented metadata. | No file contents, dependency names, package names, script names or values, package-manager execution, registry/network access, recursive discovery, or arbitrary manifest filenames. |
| `project.dependency.summary` | Summarize direct dependency counts from allowlisted root manifests. | No dependency names, dependency versions, package names, script names or values, lockfile contents, transitive resolution, package-manager execution, registry/network access, SBOM, vulnerability, license, or compliance claims. |

## Evidence Model

Every tool in this family must preserve:

- `risk: read`;
- strict JSON Schema with `additionalProperties: false`;
- role-aware visibility through the existing principal registry;
- policy preview/runtime parity for the normalized resource;
- audit metadata limited to safe counts, hashes, parser status, resource type, and output-policy
  booleans;
- MCP exposure only through the governed pipeline;
- focused implementation gate and source-review handoff bundle;
- release-check coverage through `make read-only-project-intelligence`.

## Current Position

- Tool count: `14`.
- Approved read-only project intelligence tools: `git.show.commit_metadata`,
  `git.show.ref_summary`, `project.manifest.summary`, and `project.dependency.summary`.
- Next candidate: `project.structure.summary`.
- Next candidate status: design-only selected.
- Broader capability expansion remains blocked.
- New powerful tool classes remain blocked.

## Non-Goals

This slice is not a code-search engine, package analyzer, dependency scanner, SBOM generator,
vulnerability scanner, compliance engine, shell replacement, project build runner, network package
inspector, plugin SDK, sandbox, SIEM, production identity system, or public/security-product claim.

The next selected candidate is design-only
[project.structure.summary](capability-proposals/project-structure-summary.md). It remains
implementation-blocked. Future read-only metadata tools must start again from a design-only
candidate, proposal, implementation plan, explicit implementation decision, source-review handoff,
policy fixtures, negative transcripts, no-new-powers evidence, and release gates.

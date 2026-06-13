# Read-Only Project Intelligence

Status: consolidated local-preview product slice. This document does not add runtime behavior,
tool manifests, policy rules, MCP exposure, API behavior, UI behavior, or new governed tool powers.

Read-only project intelligence is Ithildin's current safe orientation layer for local agent work. It
lets an agent learn bounded, policy-mediated facts about a workspace without receiving shell access,
package-manager execution, broad filesystem writes, raw diffs, dependency names, package names,
package versions, package script names or values, file contents, lockfile contents, registry output,
language detector execution, config parser execution, CI execution, or network-derived package
metadata.

No file contents, no dependency names, no language detector execution, no config parser execution,
no CI execution, no package-manager execution, and no registry/network access are part of this
product slice.

## Current Tool Family

| Tool | Purpose | Boundary |
| --- | --- | --- |
| `git.show.commit_metadata` | Read one local commit/ref's bounded metadata. | No checkout, remote fetch, arbitrary Git command, raw diff, or file contents. |
| `git.show.ref_summary` | Summarize local branches/tags using safe counts and response-local IDs. | No ref names in output by default, no remote refs, no checkout, and no arbitrary Git command. |
| `git.show.tag_metadata` | Summarize local tag metadata using safe counts and response-local IDs. | No raw tag names, messages, signatures, remotes, checkout, arbitrary Git command, raw diff, or file contents. |
| `project.manifest.summary` | Summarize root project manifests with count-oriented metadata. | No file contents, dependency names, package names, script names or values, package-manager execution, registry/network access, recursive discovery, or arbitrary manifest filenames. |
| `project.dependency.summary` | Summarize direct dependency counts from allowlisted root manifests. | No dependency names, dependency versions, package names, script names or values, lockfile contents, transitive resolution, package-manager execution, registry/network access, SBOM, vulnerability, license, or compliance claims. |
| `project.structure.summary` | Summarize bounded workspace structure using counts and allowlisted labels. | No raw recursive listings, raw file names, raw sensitive paths, file contents, package-manager execution, registry/network access, or broad filesystem powers. |
| `project.test.summary` | Summarize bounded test-layout signals using counts and allowlisted labels. | No test file names, test case names, raw paths, file contents, coverage data, command output, package-manager execution, registry/network access, or test execution. |
| `project.docs.summary` | Summarize bounded documentation-layout signals using counts and allowlisted labels. | No documentation file names, headings, raw paths, file contents, build execution, package-manager execution, registry/network access, or broad filesystem powers. |
| `project.language.summary` | Summarize bounded language-family signals using counts and allowlisted labels. | No language file names, raw extensions, raw paths, file contents, detector execution, package-manager execution, registry/network access, or dependency metadata. |
| `project.config.summary` | Summarize bounded configuration posture using counts and allowlisted labels. | No config file names, raw paths, file contents, config contents, config values, environment names or values, config parser execution, package-manager execution, registry/network access, or deployment claims. |
| `project.ci.summary` | Summarize bounded CI posture using counts and allowlisted labels. | No workflow names, job names, raw paths, file contents, command/script values, environment names or values, CI execution, package-manager execution, registry/network access, deployment claims, or compliance claims. |

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

- Tool count: `21`.
- Approved read-only project intelligence tools: `git.show.commit_metadata`,
  `git.show.ref_summary`, `git.show.tag_metadata`, `project.manifest.summary`,
  `project.dependency.summary`, `project.structure.summary`, `project.test.summary`,
  `project.docs.summary`, `project.language.summary`, `project.config.summary`, and
  `project.ci.summary`.
- Next candidate: `not selected`.
- Next candidate status: pending selection.
- Broader capability expansion remains blocked.
- New powerful tool classes remain blocked.

## Non-Goals

This slice is not a code-search engine, package analyzer, dependency scanner, SBOM generator,
vulnerability scanner, compliance engine, shell replacement, project build runner, network package
inspector, plugin SDK, sandbox, SIEM, production identity system, or public/security-product claim.

The most recent project metadata candidate,
[project.ci.summary](capability-proposals/project-ci-summary.md), has advanced through its approved
implementation boundary as a bounded read-only metadata tool. No next design-only candidate is
currently selected. Future read-only metadata tools must start again from a design-only
candidate, proposal, implementation plan, explicit implementation decision, source-review handoff,
policy fixtures, negative transcripts, no-new-powers evidence, and release gates.

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
| `project.release.summary` | Summarize bounded release posture using counts and allowlisted labels. | No release names, version strings, changelog contents, tag names, branch names, raw paths, file contents, command/script values, Git execution, CI execution, package-manager execution, registry/network access, deployment-readiness claims, legal claims, or compliance claims. |
| `project.risk.summary` | Summarize bounded risk-posture signals using counts and allowlisted labels. | No filenames, raw paths, file contents, dependency names, package names, CVE IDs, advisory IDs, secret names or values, scanner output, vulnerability findings, compliance findings, or security assurance claims. |

Release-summary review handoff work is recorded separately in
`make project-release-summary-review-handoff-check` and
`make project-release-summary-source-review-bundle`; those commands package the implemented
bounded read-only source-review lane without claiming external closure.

## Operator Reading Guide

For demos and handoffs, read this family as orientation evidence, not as execution evidence. The
tools are useful because they let an operator or reviewer understand the shape of a local workspace
without giving the agent a shell, package manager, network registry lookup, language detector,
config parser, CI runner, or broad file-content view.

Expected operator interpretation:

- Git metadata tools answer which local Git shape was inspected, using bounded metadata and
  response-local handles instead of arbitrary Git commands or raw diffs.
- Project metadata tools answer how many allowlisted signals exist in a bounded workspace slice,
  using counts, labels, skip counts, truncation, and output-policy booleans instead of names,
  contents, command output, or externally derived facts.
- Source-review handoffs answer whether a specific bounded lane is reviewable; they are not
  production hardening claims, compliance evidence, vulnerability scans, dependency scans, or
  public/security-product positioning.
- `read-only-capability-inventory.md` is the closure map for gates, source-review bundles, policy
  resources, and current lane status across the full 24-tool surface.

In the operator workbench story, the family should appear as a quiet inspection layer: a reviewer
can see registered tools, policy/audit evidence, and safe summaries, then follow each lane's
source-review bundle when they need implementation source, tests, policy parity, and artifact
hashes.

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

- Tool count: `24`.
- Approved read-only project intelligence tools: `git.show.commit_metadata`,
  `git.show.ref_summary`, `git.show.tag_metadata`, `project.manifest.summary`,
  `project.dependency.summary`, `project.structure.summary`, `project.test.summary`,
  `project.docs.summary`, `project.language.summary`, `project.config.summary`,
  `project.ci.summary`, `project.release.summary`, and `project.risk.summary`.
- Selected candidate: not selected.
- Selected candidate status: pending selection.
- Most recent implementation: `project.risk.summary`, approved bounded read-only runtime.
- explicit implementation decision recorded for `project.risk.summary`.
- Broader capability expansion remains blocked.
- New powerful tool classes remain blocked.

## Non-Goals

This slice is not a code-search engine, package analyzer, dependency scanner, SBOM generator,
vulnerability scanner, compliance engine, shell replacement, project build runner, network package
inspector, plugin SDK, sandbox, SIEM, production identity system, or public/security-product claim.

The most recent project metadata candidate,
[project.risk.summary](capability-proposals/project-risk-summary.md), is now implemented as one
bounded read-only metadata tool. Its fixture/test contract is
[project.risk.summary Fixture Plan](project-risk-summary-fixture-plan.md), its source-review
handoff is [v3 project.risk.summary Source Review Handoff](v3-project-risk-summary-source-review.md),
and the negative transcript plan is
[project.risk.summary Negative Transcript Plan](project-risk-summary-negative-transcripts.md).
Future read-only metadata tools must start again from a design-only candidate, proposal,
implementation plan, explicit implementation decision, source-review handoff, policy fixtures,
negative transcripts, no-new-powers evidence, and release gates.

No next design-only candidate is selected. `project.risk.summary` is risk-signal count metadata only.
It is not a vulnerability scanner, dependency scanner, compliance engine, security assurance
mechanism, scanner runner, registry/network tool, or shell/package-manager execution path.

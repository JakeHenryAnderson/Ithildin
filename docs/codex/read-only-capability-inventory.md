# Read-Only Capability Inventory

Status: approved read-only metadata inventory. This document records the bounded v0.9 metadata
capabilities that have moved beyond design-only planning through explicit implementation gates and
source-review handoff artifacts.

The governed tool surface has tool count `22`. The inventory below distinguishes the original
local-preview filesystem/Git/HTTP tools from the later bounded metadata additions so reviewers can
see which closure evidence applies to each surface. It authorizes no shell, no broad filesystem
writes, no arbitrary Git command execution, no remote fetch, no browser automation, no
Docker/Kubernetes tools, no production identity, no runtime Postgres, no hosted telemetry, no remote
MCP, no plugin SDK work, no arbitrary HTTP, and no future governed tool powers. Broader capability
expansion remains blocked until a separate proposal, implementation plan, source-review handoff,
explicit implementation decision, and release gates are recorded.

This map intentionally keeps the guardrail phrases `no broad filesystem writes` and `Broader capability expansion remains blocked` visible for review-gate checks.

## 22-Tool Surface Context

This table is a review map, not a new approval. The original local-preview tools remain governed by
their existing lane docs and release gates. The metadata additions have per-tool implementation
gates and source-review bundle targets in the next section.

| Tool | Family | Risk | Policy resource | Closure evidence |
| --- | --- | --- | --- | --- |
| `fs.list` | filesystem | `read` | `file` | filesystem/platform lane; `make filesystem-source-review-bundle` |
| `fs.read` | filesystem | `read` | `file` | filesystem/platform lane; `make filesystem-source-review-bundle` |
| `fs.search` | filesystem | `read` | `file` | filesystem/platform lane; `make filesystem-source-review-bundle` |
| `fs.stat` | filesystem | `read` | `file` | filesystem/platform lane; `make filesystem-source-review-bundle` |
| `fs.patch.propose` | filesystem | `write-proposal` | `file` | patch proposal/apply lane; `make v06-patch-apply-review-packet` |
| `fs.patch.apply` | filesystem | `write` | approved patch/proposal | patch proposal/apply lane; `make v06-patch-apply-review-packet` |
| `git.status` | git | `read` | workspace Git/file scope | original local-preview Git lane; `make review-candidate` |
| `git.log` | git | `read` | workspace Git/file scope | original local-preview Git lane; `make review-candidate` |
| `git.diff` | git | `read` | workspace Git/file scope | original local-preview Git lane; `make review-candidate` |
| `http.fetch` | network | `network` | `network` | HTTP fetch lane; `make http-fetch-source-review-bundle` |
| `git.show.commit_metadata` | Git metadata | `read` | `git_commit` | `make git-commit-metadata-implementation-gate`; `make git-commit-metadata-source-review-bundle` |
| `git.show.ref_summary` | Git metadata | `read` | `git_refs` | `make git-ref-summary-implementation-gate`; `make git-ref-summary-source-review-bundle` |
| `git.show.tag_metadata` | Git metadata | `read` | `git_tags` | `make git-tag-metadata-implementation-gate`; `make git-tag-metadata-source-review-bundle` |
| `project.manifest.summary` | project metadata | `read` | `project_manifest` | `make project-manifest-summary-implementation-gate`; `make project-manifest-summary-source-review-bundle` |
| `project.dependency.summary` | project metadata | `read` | `project_dependencies` | `make project-dependency-summary-implementation-gate`; `make project-dependency-summary-source-review-bundle` |
| `project.structure.summary` | project metadata | `read` | `project_structure` | `make project-structure-summary-implementation-gate`; `make project-structure-summary-source-review-bundle` |
| `project.test.summary` | project metadata | `read` | `project_tests` | `make project-test-summary-implementation-gate`; `make project-test-summary-source-review-bundle` |
| `project.docs.summary` | project metadata | `read` | `project_docs` | `make project-docs-summary-implementation-gate`; `make project-docs-summary-source-review-bundle` |
| `project.language.summary` | project metadata | `read` | `project_language` | `make project-language-summary-implementation-gate`; `make project-language-summary-source-review-bundle` |
| `project.config.summary` | project metadata | `read` | `project_config` | `make project-config-summary-implementation-gate`; `make project-config-summary-source-review-bundle` |
| `project.ci.summary` | project metadata | `read` | `project_ci` | `make project-ci-summary-implementation-gate`; `make project-ci-summary-source-review-bundle` |
| `project.release.summary` | project metadata | `read` | `project_release` | `make project-release-summary-implementation-gate`; `make project-release-summary-source-review-bundle` |

## Approved Read-Only Metadata Tools

| Tool | Boundary | Resource | Gate | Source Review Handoff | Closure Status |
| --- | --- | --- | --- | --- | --- |
| `git.show.commit_metadata` | bounded read-only Git commit metadata | `git_commit` | `make git-commit-metadata-implementation-gate` | `make git-commit-metadata-source-review-bundle` | internally xhigh-reviewed; external/source disposition optional/deferred |
| `git.show.ref_summary` | bounded read-only Git ref metadata | `git_refs` | `make git-ref-summary-implementation-gate` | `make git-ref-summary-source-review-bundle` | internally xhigh-reviewed; external/source disposition optional/deferred |
| `git.show.tag_metadata` | bounded read-only Git tag metadata | `git_tags` | `make git-tag-metadata-implementation-gate` | `make git-tag-metadata-source-review-bundle` | internally reviewed; external/source disposition optional/deferred |
| `project.manifest.summary` | bounded read-only project manifest metadata | `project_manifest` | `make project-manifest-summary-implementation-gate` | `make project-manifest-summary-source-review-bundle` | locally reviewed; external/source disposition optional/deferred |
| `project.dependency.summary` | bounded read-only direct dependency count metadata | `project_dependencies` | `make project-dependency-summary-implementation-gate` | `make project-dependency-summary-source-review-bundle` | source-review handoff prepared |
| `project.structure.summary` | bounded read-only project structure count metadata | `project_structure` | `make project-structure-summary-implementation-gate` | `make project-structure-summary-source-review-bundle` | source-review handoff prepared |
| `project.test.summary` | bounded read-only project test-layout count metadata | `project_tests` | `make project-test-summary-implementation-gate` | `make project-test-summary-source-review-bundle` | source-review handoff prepared |
| `project.docs.summary` | bounded read-only project documentation count metadata | `project_docs` | `make project-docs-summary-implementation-gate` | `make project-docs-summary-source-review-bundle` | source-review handoff prepared |
| `project.language.summary` | bounded read-only project language count metadata | `project_language` | `make project-language-summary-implementation-gate` | `make project-language-summary-source-review-bundle` | source-review handoff prepared |
| `project.config.summary` | bounded read-only project config posture count metadata | `project_config` | `make project-config-summary-implementation-gate` | `make project-config-summary-source-review-bundle` | source-review handoff prepared |
| `project.ci.summary` | bounded read-only project CI posture count metadata | `project_ci` | `make project-ci-summary-implementation-gate` | `make project-ci-summary-source-review-bundle` | source-review handoff refreshed; reviewer intake still required for `EXT-CI-###` closure |
| `project.release.summary` | bounded read-only project release posture count metadata | `project_release` | `make project-release-summary-implementation-gate` | `make project-release-summary-source-review-bundle` | internally reviewed; reviewer intake still required for `EXT-REL-###` closure |

## Shared Boundary

Every approved capability in this inventory must preserve:

- `risk: read` and the reviewed category for the tool;
- strict JSON Schema with `additionalProperties: false`;
- fixed internal Git argv and no shell;
- no caller-controlled Git argv, format strings, refspecs, pathspecs, remotes, or revisions beyond
  the reviewed structured input contract for that tool;
- no package-manager execution, registry/network access, dependency names, dependency versions,
  package names, package script names or values, lockfile contents, or recursive manifest discovery
  for project metadata;
- no file contents, raw diffs, patch hunks, raw stderr, credentials, or broad filesystem access;
- policy preview/runtime parity for the normalized resource;
- safe audit metadata without raw sensitive values;
- focused source-review bundle and internal xhigh review before continued local-preview use.

## Gate

Run:

```bash
make read-only-capability-inventory-gate
```

The gate validates the inventory document, approved manifests, review-doc inclusion, docs-site
inclusion, implementation gates, source-review bundle targets, tool-surface invariant, no-new-powers
guardrail, and `release-check` wiring.

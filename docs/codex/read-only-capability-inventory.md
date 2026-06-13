# Read-Only Capability Inventory

Status: approved read-only metadata inventory. This document records the bounded v0.9 metadata
capabilities that have moved beyond design-only planning through explicit implementation gates and
source-review handoff artifacts.

The inventory has tool count `21` and includes only local read-only developer metadata additions.
It authorizes no shell, no broad filesystem writes, no arbitrary Git command execution, no remote
fetch, no browser automation, no Docker/Kubernetes tools, no production identity, no runtime
Postgres, no hosted telemetry, no remote MCP, no plugin SDK work, no arbitrary HTTP, and no future
governed tool powers. Broader capability expansion remains blocked until a separate proposal,
implementation plan,
source-review handoff, explicit implementation decision, and release gates are recorded.

## Approved Read-Only Metadata Tools

| Tool | Status | Gate | Source Review Handoff |
| --- | --- | --- | --- |
| `git.show.commit_metadata` | approved bounded read-only Git commit metadata | `make git-commit-metadata-implementation-gate` | `make git-commit-metadata-source-review-bundle` |
| `git.show.ref_summary` | approved bounded read-only Git ref metadata | `make git-ref-summary-implementation-gate` | `make git-ref-summary-source-review-bundle` |
| `git.show.tag_metadata` | approved bounded read-only Git tag metadata | `make git-tag-metadata-implementation-gate` | `make git-tag-metadata-source-review-bundle` |
| `project.manifest.summary` | approved bounded read-only project manifest metadata | `make project-manifest-summary-implementation-gate` | `make project-manifest-summary-source-review-bundle` |
| `project.dependency.summary` | approved bounded read-only direct dependency count metadata | `make project-dependency-summary-implementation-gate` | `make project-dependency-summary-source-review-bundle` |
| `project.structure.summary` | approved bounded read-only project structure count metadata | `make project-structure-summary-implementation-gate` | `make project-structure-summary-source-review-bundle` |
| `project.test.summary` | approved bounded read-only project test-layout count metadata | `make project-test-summary-implementation-gate` | `make project-test-summary-source-review-bundle` |
| `project.docs.summary` | approved bounded read-only project documentation count metadata | `make project-docs-summary-implementation-gate` | `make project-docs-summary-source-review-bundle` |
| `project.language.summary` | approved bounded read-only project language count metadata | `make project-language-summary-implementation-gate` | `make project-language-summary-source-review-bundle` |
| `project.config.summary` | approved bounded read-only project config posture count metadata | `make project-config-summary-implementation-gate` | `make project-config-summary-source-review-bundle` |
| `project.ci.summary` | approved bounded read-only project CI posture count metadata | `make project-ci-summary-implementation-gate` | `make project-ci-summary-source-review-bundle` |

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

# Read-Only Capability Inventory

Status: approved read-only metadata inventory. This document records the bounded v0.9 metadata
capabilities that have moved beyond design-only planning through explicit implementation gates and
source-review handoff artifacts.

The inventory has tool count `12` and includes only local read-only developer metadata additions.
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

## Shared Boundary

Every approved capability in this inventory must preserve:

- `risk: read` and `category: git`;
- strict JSON Schema with `additionalProperties: false`;
- fixed internal Git argv and no shell;
- no caller-controlled Git argv, format strings, refspecs, pathspecs, remotes, or revisions beyond
  the reviewed structured input contract for that tool;
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

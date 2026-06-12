# Next Capability Readiness Check

Status: capability-expansion readiness checkpoint. This document does not add runtime behavior,
tool manifests, policy rules, MCP exposure, API behavior, UI behavior, or new governed tool powers.

This checkpoint exists because the first bounded read-only metadata lanes are now implemented:
`git.show.commit_metadata`, `git.show.ref_summary`, `project.manifest.summary`,
`project.dependency.summary`, and `project.structure.summary`. The historical candidate records
still show how each bounded metadata tool advanced through proposal, implementation planning,
implementation decision, source-review handoff, and local lane closure.

## Current State

- Current approved read-only metadata inventory: `git.show.commit_metadata`,
  `git.show.ref_summary`, `project.manifest.summary`, `project.dependency.summary`, and
  `project.structure.summary`.
- Current tool count: `15`.
- Next candidate: `project.test.summary`.
- Next candidate status: design-only selected.
- Next candidate implementation: blocked.
- Broader capability expansion: blocked.
- New powerful tool classes: blocked.

## Required Preflight Before Another Capability

Before any future capability implementation may begin, the project must record:

- a design-only candidate evaluation;
- a complete capability proposal;
- an implementation-planning packet;
- an explicit implementation decision for that one bounded capability;
- a focused source-review handoff bundle;
- policy preview/runtime resource evidence;
- policy fixtures and parity evidence;
- audit evidence fields;
- UI/review evidence where relevant;
- negative transcript coverage;
- resource limits;
- accepted-risk impact analysis;
- no-new-powers evidence;
- internal high/xhigh review using the current model-tiering guardrails;
- external/source review when the capability changes a reviewed boundary or introduces a new
  powerful tool class.

## Stop Conditions

Stop before implementation if a candidate needs shell execution, Docker/Kubernetes access, browser
automation, arbitrary HTTP methods/headers/bodies, broad filesystem writes, remote MCP, production
identity, runtime Postgres, hosted telemetry, plugin SDK work, package-manager execution, registry
or network access, raw diffs, file contents by default, or unbounded repository-controlled text.

## Gate

The most recent capability,
[project.structure.summary](capability-proposals/project-structure-summary.md), has advanced through
proposal, implementation planning, implementation decision, runtime implementation, and
source-review handoff as one bounded read-only metadata tool. The next design-only candidate is
[project.test.summary](capability-proposals/project-test-summary.md), and implementation remains
blocked until a later implementation-planning packet and explicit implementation decision exist.

Run:

```bash
make next-capability-readiness
make project-structure-summary-source-review-bundle
make project-test-summary-proposal-check
make project-test-summary-design-review-packet
```

The gate validates the shared read-only metadata capability contract, the approved bounded metadata
inventory, no-new-powers evidence, the historical candidate lineage, release-check wiring,
review-doc inclusion, and docs-site inclusion. It does not approve another
implementation by itself.

# Next Capability Readiness Check

Status: capability-expansion readiness checkpoint. This document does not add runtime behavior,
tool manifests, policy rules, MCP exposure, API behavior, UI behavior, or new governed tool powers.

This checkpoint exists because the first bounded read-only metadata lanes are now implemented:
`git.show.commit_metadata`, `git.show.ref_summary`, and `project.manifest.summary`. The historical
`v3-next-capability-candidate-evaluation.md` still records how `project.manifest.summary` was chosen
as a design-only candidate before it advanced through proposal, implementation planning,
implementation decision, source-review handoff, and local lane closure.

## Current State

- Current approved read-only metadata inventory: `git.show.commit_metadata`,
  `git.show.ref_summary`, and `project.manifest.summary`.
- Current tool count: `13`.
- Next candidate: `project.dependency.summary`.
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

The selected next design candidate is
[v3 project.dependency.summary Selection](v3-project-dependency-summary-selection.md). It remains
design-only, count-only, and implementation-blocked until a future explicit decision.

Run:

```bash
make next-capability-readiness
```

The gate validates the shared read-only metadata capability contract, the approved bounded metadata
inventory, no-new-powers evidence, the historical candidate lineage, release-check wiring, review-doc
inclusion, and docs-site inclusion. It does not approve another implementation by itself.

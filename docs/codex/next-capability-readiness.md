# Next Capability Readiness Check

Status: capability-expansion readiness checkpoint. This document does not add runtime behavior,
tool manifests, policy rules, MCP exposure, API behavior, UI behavior, or new governed tool powers.

This checkpoint exists because the first bounded read-only metadata lanes are now implemented:
`git.show.commit_metadata`, `git.show.ref_summary`, `git.show.tag_metadata`,
`project.manifest.summary`, `project.dependency.summary`, `project.structure.summary`,
`project.test.summary`, `project.docs.summary`, `project.language.summary`,
`project.config.summary`, `project.ci.summary`, `project.release.summary`, and
`project.risk.summary`. The historical
candidate records still show
how each bounded metadata tool advanced through proposal, implementation planning, implementation
decision, source-review handoff, and local lane closure.

## Current State

- Current approved read-only metadata inventory: `git.show.commit_metadata`,
  `git.show.ref_summary`, `git.show.tag_metadata`, `project.manifest.summary`,
  `project.dependency.summary`, `project.structure.summary`, `project.test.summary`,
  `project.docs.summary`, `project.language.summary`, `project.config.summary`,
  `project.ci.summary`, `project.release.summary`, and `project.risk.summary`.
- Current tool count: `23`.
- Selected candidate: not selected.
- Selected candidate status: pending selection.
- Most recent implemented candidate: `project.risk.summary`.
- Most recent implementation: approved bounded read-only runtime implementation complete.
- Fixture/test contract: retained for `project.risk.summary`.
- Implementation transition checklist: completed for `project.risk.summary`.
- Source-review handoff: recorded for `project.risk.summary`.
- Source-review bundle: recorded for `project.risk.summary`.
- Broader capability expansion: blocked.
- New powerful tool classes: blocked.

## Required Preflight Before Another Capability

Before any future capability implementation may begin, the project must record:

- a design-only candidate evaluation;
- a complete capability proposal;
- an implementation-planning packet;
- an explicit implementation decision for that one bounded capability;
- a focused source-review handoff bundle;
- a preimplementation fixture/test contract and check for the selected candidate;
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

The most recent implemented capability,
[project.risk.summary](capability-proposals/project-risk-summary.md), has advanced through
proposal, implementation planning, implementation decision, runtime implementation, internal source
review, and source-review handoff as one bounded read-only metadata tool.

No next capability is selected. `project.risk.summary` is intentionally risk-signal count metadata,
not vulnerability scanning, dependency analysis, compliance automation, security assurance, scanner
execution, package-manager execution, registry/network access, or raw sensitive metadata exposure.

Run:

```bash
make next-capability-readiness
make project-risk-summary-proposal-check
make project-risk-summary-implementation-plan-check
make project-risk-summary-implementation-gate
make project-risk-summary-preimplementation-check
make project-risk-summary-review-handoff-check
make project-risk-summary-design-review-packet
make project-risk-summary-source-review-bundle
make project-release-summary-proposal-check
make project-release-summary-implementation-plan-check
make project-release-summary-design-review-packet
```

The gate validates the shared read-only metadata capability contract, the approved bounded metadata
inventory, no-new-powers evidence, the historical candidate lineage, release-check wiring,
review-doc inclusion, and docs-site inclusion. It does not approve another implementation by
itself.

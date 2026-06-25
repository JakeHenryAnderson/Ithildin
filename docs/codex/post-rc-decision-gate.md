# Post-RC Decision Gate

Status: process gate for post-v1.0 RC boundary decisions.

Ithildin v1.0 remains frozen as a local-preview release candidate until a separate post-RC
decision record explicitly opens a lane. This gate does not approve runtime behavior. It defines the
minimum evidence that must exist before implementation planning can resume for any lane that changes
the product boundary.

Current governed tool count: `24`.

Current selected capability: `not selected`.

## Current Baseline

- Capability expansion remains blocked.
- Mission Control runtime behavior remains blocked.
- Live sandbox/VM/container inspection remains blocked.
- Local model invocation remains blocked.
- Trusted-host promotion remains blocked.
- SIEM adapter work remains blocked.
- Production identity, runtime Postgres, hosted telemetry, remote MCP, hosted MCP, and plugin SDK
  work remain blocked.
- Compliance automation and public/security-product positioning remain blocked.
- Runtime changes remain blocked except for blocking release fixes or explicit post-RC decisions.

## Decision Record Required Fields

Every post-RC decision record must include:

- Decision ID.
- Date.
- Owner and reviewer.
- Target lane.
- Trigger and requested change.
- Current boundary being changed.
- Allowed scope.
- Explicitly forbidden scope.
- Required source-review or external-review evidence.
- Required implementation plan.
- Rollback and stop conditions.
- Required tests, gates, and packet artifacts.
- Accepted-risk impact.
- Tool count and manifest impact.
- User/operator warning language.
- Go/no-go outcome.

Use the [Post-RC Decision Record Template](post-rc-decision-record-template.md) for the canonical
field layout.

## Lanes Requiring This Gate

This gate is required before any of these lanes may move beyond documentation or planning:

- New governed tool or capability implementation after the v1.0 RC freeze.
- Mission Control runtime importer, dashboard behavior that changes authority, or cross-project
  file handling beyond display/import planning.
- Live sandbox/VM/container inspection.
- Local model invocation.
- Trusted-host promotion.
- SIEM adapters or hosted telemetry.
- Production identity.
- Runtime Postgres.
- Remote MCP or hosted MCP.
- Plugin SDK behavior.
- Compliance automation or public/security-product positioning.
- Broad filesystem, network, or write expansion.

## Required References

Any decision record must reference the relevant current boundary docs:

- [v1.0 RC Feature Freeze](v1.0-rc-feature-freeze.md)
- [v1.0 RC Final Handoff](v1.0-rc-final-handoff.md)
- [v1.0 RC Post-Review Triage](v1.0-rc-post-review-triage.md)
- [Enterprise Readiness Runway](enterprise-readiness-runway.md)
- [Mission Control Display Integration Proposal](mission-control-display-integration-proposal.md)
- [Sandbox/VM Static Preflight Source Review](sandbox-vm-static-preflight-source-review.md)
- [Sandbox Promotion Evidence Contract](sandbox-promotion-evidence-contract.md)

## What This Gate Allows

This gate allows documentation, planning, review packets, and decision records.

It does not approve manifests, executors, API/MCP behavior, policy changes, UI runtime behavior,
Mission Control runtime behavior, sandbox orchestration, local model invocation, trusted-host
promotion, SIEM adapters, production identity, runtime storage changes, hosted telemetry, remote MCP,
plugin SDK behavior, or compliance/public-security claims.

## Stop Conditions

Stop before implementation if:

- The requested change alters the current v1.0 local-preview boundary without a decision record.
- Required source-review or external-review evidence is missing.
- The decision record does not include explicit forbidden scope.
- The change requires a new governed tool count but lacks a manifest/tool-surface plan.
- The change touches Mission Control, sandbox/VM, local-model, trusted-host, SIEM, identity, storage,
  or remote surfaces without naming the exact lane and evidence plan.
- The change would make public/security-product or compliance claims.

## Validation

Run:

```sh
make post-rc-decision-gate
```

The gate must remain green before `make release-check` can pass.

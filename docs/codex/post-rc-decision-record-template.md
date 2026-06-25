# Post-RC Decision Record Template

Status: template for post-v1.0 RC boundary decisions.

Use this template when a reviewer, operator, or implementation sprint requests work that would move
Ithildin beyond the v1.0 RC feature freeze. This template is a decision-record format only. It does
not approve runtime behavior, manifests, executors, policy changes, API/MCP behavior, UI runtime
behavior, Mission Control runtime behavior, sandbox orchestration, local model invocation,
trusted-host promotion, SIEM adapters, production identity, runtime Postgres, hosted telemetry,
remote MCP, hosted MCP, plugin SDK behavior, compliance automation, or public/security-product
positioning.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Decision record status: `draft | approved_for_planning | no_go | superseded`.

## Decision Header

- Decision ID:
- Date:
- Owner:
- Reviewer:
- Target lane:
- Requested by:
- Related review packet:
- Related findings:

## Trigger And Requested Change

- Trigger:
- Requested change:
- Why this cannot stay documentation-only:
- Current boundary being changed:

## Scope

- Allowed scope:
- Explicitly forbidden scope:
- Runtime surfaces touched:
- Runtime surfaces not touched:
- Tool count impact:
- Manifest impact:
- Policy/rule impact:
- API/MCP impact:
- UI runtime impact:
- Mission Control impact:
- Sandbox/VM impact:
- Local model impact:
- Trusted-host promotion impact:
- SIEM/telemetry impact:
- Identity/storage/remote impact:
- Compliance/public-positioning impact:

## Required Evidence

- Required source-review or external-review evidence:
- Required implementation plan:
- Required rollback and stop conditions:
- Required tests:
- Required gates:
- Required packet artifacts:
- Required negative transcripts:
- Required accepted-risk update:
- Required operator warning language:

## Risk And Boundary Decision

- Accepted-risk impact:
- Data exposure impact:
- Permission/authority impact:
- Audit/evidence impact:
- Recovery/rollback impact:
- Residual risk:
- Go/no-go outcome:
- Decision rationale:

## Implementation Preconditions

Implementation may not begin until every applicable item is complete:

- The [Post-RC Decision Gate](post-rc-decision-gate.md) passes.
- The decision record has a non-draft outcome.
- The allowed scope and explicitly forbidden scope are both filled in.
- Required source-review or external-review evidence is linked.
- Required implementation plan is linked.
- Required tests, gates, and packet artifacts are named.
- Tool count and manifest impact are explicit.
- Accepted-risk impact is explicit.
- Operator warning language is explicit.
- Stop conditions are explicit.

## Blocked-by-Default Lanes

These lanes remain blocked unless this template records a specific approved decision:

- New governed tool or capability implementation after the v1.0 RC freeze.
- Mission Control runtime importer or authority-changing dashboard behavior.
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

## Validation

Run:

```sh
make post-rc-decision-record-template-check
make post-rc-decision-gate
```

Both checks must remain green before `make release-check` can pass.

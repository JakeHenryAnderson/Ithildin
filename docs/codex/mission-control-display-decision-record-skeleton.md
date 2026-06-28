# Mission Control Display Decision Record Skeleton

Status: design-only decision-record skeleton for `ERG-002` and `PRD-MC-DISPLAY-001`.

Current governed tool count: `24`.

Current `ERG-002` status: `planning_only`.

Current selected capability: `not selected`.

This skeleton turns a future normalized Mission Control display/importer review response into a
post-RC decision record shape. It does not approve runtime behavior, a Mission Control runtime
importer, Mission Control execution authority, Mission Control policy authority, Mission Control
approval authority, Mission Control audit authority, API callbacks, polling or mutating Ithildin
APIs, local model invocation, VM/container lifecycle management, sandbox orchestration,
trusted-host promotion, SIEM adapters, production identity, runtime Postgres, hosted telemetry,
remote MCP, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem
writes, compliance automation, new governed tool powers, or public/security-product positioning.

Use this skeleton only after:

- `var/review-runs/mission-control-display/normalized-response.json` exists;
- `make mission-control-display-response-application-preflight-check` passed before applying the
  real response;
- `mission-control-display-response-application-preflight.md` still verifies the all-lane raw
  response path, lane-local normalized response path, command matrix, closure gate, dry-run,
  response kit, decision-record skeleton, and blocked runtime boundaries;
- `mission-control-display-response-application-record.md` and
  `mission-control-display-response-application-playbook.md` were followed for command order,
  allowed committed files, and stop conditions;
- `make mission-control-display-disposition-closure-check` reports `closure_ready: true`;
- the normalized response records `disposition_outcome: continue_design_only`;
- no critical/high `EXT-MC-DISPLAY-###` finding is open;
- the Mission Control display review packet hash in the response matches the packet being
  dispositioned.

## Allowed Decision Outcome

The only outcome this skeleton may support is:

```text
approved_for_planning
```

The only allowed lane movement is:

```text
ERG-002: planning_only -> ready_for_design_only_decision_record
```

That movement means Mission Control-side display/importer design planning may continue. It does not
approve implementation of a runtime importer on either side of the integration.

## Decision Header

- Decision ID: `PRD-MC-DISPLAY-001`
- Date:
- Owner:
- Reviewer:
- Target lane: `ERG-002` Mission Control display/importer.
- Requested by:
- Related review packet: `var/review-packets/v3/mission-control-display-external-review`
- Related response kit: `var/review-packets/v3/mission-control-display-response-kit`
- Related normalized response:
  `var/review-runs/mission-control-display/normalized-response.json`
- Related findings: `EXT-MC-DISPLAY-###` if present.

## Trigger And Requested Change

- Trigger: external/source reviewer accepts the Mission Control display/import planning lane for
  continued design-only work.
- Requested change: record that Mission Control-side display/importer planning may continue from
  the reviewed packet, schema contract, negative fixtures, and response kit.
- Why this cannot stay documentation-only: a later Mission Control-side repository task needs a
  stable decision artifact naming exactly what is still allowed and what remains blocked.
- Current boundary being changed: no runtime boundary changes; this is a design-only disposition
  marker.

## Scope

Mission Control runtime importer behavior remains blocked.

- Allowed scope: Mission Control-side UI display design, local packet file/import sketches, static
  metadata-only fixtures, display allowlist/denylist docs, warning-chip requirements, stale/mismatch
  negative fixtures, source-review handoff prompts, and operator-facing wording.
- Explicitly forbidden scope: runtime importer implementation, Mission Control execution authority,
  Mission Control policy authority, Mission Control approval authority, Mission Control audit
  authority, API callbacks, polling or mutating Ithildin APIs, local model invocation, VM/container
  lifecycle management, sandbox orchestration, trusted-host promotion, SIEM adapter behavior,
  production identity, runtime Postgres, hosted telemetry, remote MCP, shell/Docker/Kubernetes/browser
  governed powers, arbitrary HTTP, broad filesystem writes, compliance automation, new governed tool
  powers, or public/security-product positioning.
- Runtime surfaces touched: none.
- Runtime surfaces not touched: Ithildin manifests, executors, policy/rules, API/MCP behavior,
  approval/audit logic, UI runtime behavior, Mission Control runtime behavior, sandbox/VM runtime
  behavior, local model invocation, trusted-host promotion, SIEM/telemetry, identity, storage, and
  remote services.
- Tool count impact: none; remains `24`.
- Manifest impact: none.
- Policy/rule impact: none.
- API/MCP impact: none.
- UI runtime impact: none in Ithildin.
- Mission Control impact: planning artifacts only.
- Sandbox/VM impact: none.
- Local model impact: none.
- Trusted-host promotion impact: none.
- SIEM/telemetry impact: none.
- Identity/storage/remote impact: none.
- Compliance/public-positioning impact: none.

## Required Evidence

- Required source-review or external-review evidence:
  `var/review-runs/mission-control-display/normalized-response.json`.
- Required implementation plan: still required before any runtime importer implementation.
- Required rollback and stop conditions: stop if implementation would grant Mission Control
  execution, policy, approval, audit, sandbox, local-model, trusted-host promotion, SIEM, identity,
  storage, remote, or compliance authority.
- Required tests: `make mission-control-display-response-dry-run`,
  `make mission-control-display-disposition-closure-check`,
  `make mission-control-display-decision-record-skeleton-check`, and `make release-check`.
- Required gates: `make post-rc-decision-gate`,
  `make mission-control-display-decision-intake-check`,
  `make mission-control-display-external-response-intake-check`, and
  `make mission-control-display-disposition-closure-check`.
- Required packet artifacts: Mission Control display external-review bundle, disposition packet,
  response kit, and integration readiness packet.
- Required negative transcripts: stale, mismatched, unsafe attachment, authority overclaim, and
  content-leak fixtures remain required before implementation.
- Required accepted-risk update: none for this design-only decision record.
- Required operator warning language: Mission Control displays imported metadata only and remains
  non-authoritative for Ithildin execution, policy, approval, audit, sandbox, local-model, promotion,
  SIEM, identity, storage, remote, and compliance behavior.

## Risk And Boundary Decision

- Accepted-risk impact: no new accepted risk for design-only continuation.
- Data exposure impact: imported display data remains metadata-only and must not include prompts,
  file contents, diffs, response bodies, raw host paths, secrets, dependency names, package script
  values, or raw sandbox internals.
- Permission/authority impact: no authority transfer.
- Audit/evidence impact: decision evidence is local documentation and normalized reviewer evidence,
  not runtime audit custody.
- Recovery/rollback impact: revert the decision record and keep `ERG-002` as `planning_only` if
  evidence is later found stale or mismatched.
- Residual risk: Mission Control-side implementation may still drift when built later; that requires
  its own implementation plan, tests, and review.
- Go/no-go outcome: go for design-only Mission Control-side planning; no-go for runtime importer
  implementation or authority transfer.
- Decision rationale: the reviewed packet supports continuing UI/display planning only.

## Implementation Preconditions For Later Runtime Importer Work

Runtime importer work remains blocked until a separate future decision proves:

- exact Mission Control-side file/import behavior;
- stale packet and mismatched hash rejection;
- attachment path and unsafe payload rejection;
- visible warning chips;
- no authority overclaim;
- no raw sensitive content display;
- Mission Control-side tests and source review;
- no changes to Ithildin runtime behavior unless a separate Ithildin implementation decision exists.

## Validation

Run:

```sh
make mission-control-display-decision-record-skeleton-check
make mission-control-display-disposition-closure-check
make mission-control-display-response-dry-run
make mission-control-display-response-application-record-check
make mission-control-display-response-application-playbook-check
```

These checks must remain green before `make release-check` can pass.

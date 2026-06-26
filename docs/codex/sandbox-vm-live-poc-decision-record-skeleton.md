# Sandbox/VM Live POC Decision Record Skeleton

Status: design-only decision-record skeleton for blocked `ERG-004` and
`PRD-SANDBOX-LIVE-POC-001`.

Current governed tool count: `24`.

Current `ERG-004` status: `blocked`.

Current selected capability: `not selected`.

This skeleton turns a future normalized sandbox/VM live POC review response into a post-RC decision
record shape. It does not approve runtime implementation, live VM/container inspection,
VM/container lifecycle management, sandbox orchestration, Mission Control runtime behavior, local
model invocation, trusted-host promotion, network expansion, API/MCP profile loading, SIEM adapter
behavior, production identity, runtime Postgres, hosted telemetry, remote MCP, compliance
automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem
writes, plugin SDK behavior, new governed tool powers, or public/security-product positioning.

Use this skeleton only after:

- favorable `ERG-003` static preflight disposition is recorded;
- `make sandbox-vm-live-poc-prerequisite-disposition-dry-run` has proven that favorable
  static-preflight disposition fixtures satisfy only a prerequisite and do not unblock `ERG-004`;
- `var/review-runs/sandbox-vm-live-poc/normalized-response.json` exists;
- `make sandbox-vm-live-poc-decision-closure-check` reports `closure_ready: true`;
- the normalized response records
  `decision_outcome: approve_limited_operator_managed_poc_planning`;
- no critical/high `EXT-LIVE-POC-###` finding is open;
- the sandbox/VM live POC decision packet hash in the response matches the packet being
  dispositioned.

## Allowed Decision Outcome

The only outcome this skeleton may support is:

```text
approved_for_implementation_planning_only
```

The only allowed lane movement is:

```text
ERG-004: blocked -> ready_for_implementation_planning_only
```

That movement means a later implementation-planning packet may be drafted for a limited
operator-managed live POC. It does not approve runtime implementation.

## Decision Header

- Decision ID: `PRD-SANDBOX-LIVE-POC-001`
- Date:
- Owner:
- Reviewer:
- Target lane: `ERG-004` live sandbox/VM worker proof of concept.
- Requested by:
- Related prior lane: `ERG-003` static sandbox/VM preflight.
- Related decision packet: `var/review-packets/v3/sandbox-vm-live-poc-decision`
- Related normalized response:
  `var/review-runs/sandbox-vm-live-poc/normalized-response.json`
- Related findings: `EXT-LIVE-POC-###` if present.

## Trigger And Requested Change

- Trigger: external/source reviewer accepts that a limited operator-managed live POC may move to
  implementation-planning-only status.
- Requested change: record that implementation planning may begin from the reviewed preconditions
  map, evidence contract, decision packet, external-response intake, and closure gate.
- Why this cannot stay documentation-only: a later implementation-planning packet needs a stable
  decision artifact naming the exact POC boundaries and the authorities that remain blocked.
- Current boundary being changed: no runtime boundary changes; this is a planning-only disposition
  marker.

## Scope

Live sandbox/VM runtime behavior remains blocked.

- Allowed scope: implementation-planning document, static fixtures, operator-managed profile
  sketch, cleanup/failure transcript plan, evidence field list, source-review handoff prompt,
  Mission Control display-only note, local-model/client label design, and stop-condition language.
- Explicitly forbidden scope: runtime implementation, live VM/container inspection,
  VM/container lifecycle management, sandbox orchestration, Mission Control runtime behavior, local
  model invocation, trusted-host promotion, network expansion, API/MCP profile loading, SIEM adapter
  behavior, production identity, runtime Postgres, hosted telemetry, remote MCP,
  shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes, plugin
  SDK behavior, compliance automation, new governed tool powers, or public/security-product
  positioning.
- Runtime surfaces touched: none.
- Runtime surfaces not touched: Ithildin manifests, executors, policy/rules, API/MCP behavior,
  approval/audit logic, UI runtime behavior, Mission Control runtime behavior, sandbox/VM runtime
  behavior, local model invocation, trusted-host promotion, SIEM/telemetry, identity, storage, and
  remote services.
- Tool count impact: none; remains `24`.
- Manifest impact: none.
- Policy/rule impact: none.
- API/MCP impact: none.
- UI runtime impact: none.
- Mission Control impact: display-only planning notes at most.
- Sandbox/VM impact: planning artifacts only.
- Local model impact: planning labels only.
- Trusted-host promotion impact: none.
- SIEM/telemetry impact: none.
- Identity/storage/remote impact: none.
- Compliance/public-positioning impact: none.

## Required Evidence

- Required prior-lane evidence: favorable `ERG-003` static preflight disposition.
- Required prerequisite dry-run evidence:
  `sandbox-vm-live-poc-prerequisite-disposition-dry-run.md` evidence showing fixture-only
  prerequisite validation does not approve live POC planning.
- Required source-review or external-review evidence:
  `var/review-runs/sandbox-vm-live-poc/normalized-response.json`.
- Required closure gate: `make sandbox-vm-live-poc-decision-closure-check` reports
  `closure_ready: true` and `allowed_closure_state: ready_for_decision_record`.
- Required implementation plan: still required before any runtime implementation.
- Required rollback and stop conditions: stop if implementation would grant live VM/container
  inspection, sandbox orchestration, Mission Control runtime behavior, local model invocation,
  trusted-host promotion, network expansion, API/MCP profile loading, SIEM adapter behavior,
  identity, storage, remote, or compliance authority.
- Required tests: `make sandbox-vm-live-poc-response-dry-run`,
  `make sandbox-vm-live-poc-decision-closure-check`,
  `make sandbox-vm-live-poc-decision-record-skeleton-check`, and `make release-check`.
- Required packet artifacts: live POC decision packet, preconditions map, evidence contract,
  external-response intake, and the favorable static-preflight disposition evidence.
- Required negative transcripts: cleanup failure, unsafe mount/root posture, stale/mismatched
  packet hash, authority overclaim, local-model invocation overclaim, Mission Control runtime
  overclaim, trusted-host promotion overclaim, network expansion overclaim, and content-leak
  fixtures remain required before runtime implementation.
- Required accepted-risk update: none for this planning-only decision record.
- Required operator warning language: any later POC remains operator-managed and local-preview only;
  Ithildin does not become a VM/container orchestrator, local-model runner, trusted-host promotion
  engine, SIEM adapter, production identity provider, or compliance automation system.

## Risk And Boundary Decision

- Accepted-risk impact: no new accepted risk for planning-only continuation.
- Data exposure impact: planned evidence must not include prompts, file contents, diffs, response
  bodies, raw host paths, secrets, dependency names, package script values, raw sandbox internals, or
  local model prompts/responses.
- Permission/authority impact: no authority transfer.
- Audit/evidence impact: decision evidence is local documentation and normalized reviewer evidence,
  not runtime audit custody.
- Recovery/rollback impact: revert the decision record and keep `ERG-004` as `blocked` if evidence
  is later found stale, mismatched, missing favorable `ERG-003` disposition, or overbroad.
- Residual risk: a later live POC implementation may still drift into sandbox orchestration or local
  model runtime authority; that requires a separate implementation plan, tests, and review.
- Go/no-go outcome: go for implementation-planning-only; no-go for runtime implementation, live
  VM/container inspection, sandbox orchestration, Mission Control runtime behavior, local model
  invocation, trusted-host promotion, SIEM adapter behavior, or authority transfer.
- Decision rationale: the reviewed packet may support planning a limited operator-managed POC only.

## Implementation Preconditions For Later Runtime Work

Runtime work remains blocked until a separate future implementation decision proves:

- exact operator-managed VM/container profile behavior;
- exact artifact ingress/egress and cleanup behavior;
- stale packet and mismatched hash rejection;
- unsafe mount/root/network posture rejection;
- local model prompt/response exclusion or separately reviewed handling;
- Mission Control display-only boundaries if Mission Control participates;
- visible warning chips and operator stop conditions;
- cleanup and failure transcripts;
- no authority overclaim;
- no raw sensitive content display;
- Ithildin-side tests and source review;
- no changes to broader Ithildin runtime behavior unless a separate implementation decision exists.

## Validation

Run:

```sh
make sandbox-vm-live-poc-decision-record-skeleton-check
make sandbox-vm-live-poc-decision-closure-check
make sandbox-vm-live-poc-response-dry-run
```

These checks must remain green before `make release-check` can pass.

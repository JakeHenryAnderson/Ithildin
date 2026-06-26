# Sandbox/VM Static Preflight Disposition Record Skeleton

Status: design-only disposition-record skeleton for `ERG-003`.

Current governed tool count: `24`.

Current `ERG-003` status: `external_review_required`.

Current selected capability: `not selected`.

This skeleton turns a future normalized sandbox/VM static preflight external/source review response
into a committed disposition-record shape. It does not close `ERG-003` by itself. It does not
approve runtime implementation, live VM/container inspection, VM/container lifecycle management,
sandbox orchestration, Mission Control runtime behavior, local model invocation, trusted-host
promotion, network expansion, API/MCP profile loading, new governed tool powers, production
identity, runtime Postgres, hosted telemetry, remote MCP, SIEM adapter behavior, compliance
automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem
writes, plugin SDK behavior, or public/security-product positioning.

Use this skeleton only after:

- `var/review-runs/sandbox-vm-static-preflight/normalized-response.json` exists;
- `make sandbox-vm-static-preflight-disposition-closure-check` reports `closure_ready: true`;
- the normalized response records source access as `source-level` or `packet-and-source`;
- the normalized response records `can_close_source_rows: true`;
- the normalized response records `mutates_findings: false`;
- the normalized response records `closes_external_review: false`;
- no critical/high `EXT-SVP-###` finding is open;
- the static preflight disposition packet hash in the response matches the packet being
  dispositioned.

## Allowed Disposition Outcome

The only outcome this skeleton may support is:

```text
closed_local_preview_static_preflight
```

The only allowed lane movement is:

```text
ERG-003: external_review_required -> closed_local_preview_static_preflight
```

That movement means only that the CLI-only static sandbox/VM profile preflight lane has been
externally/source reviewed for local-preview fixture evidence. It does not approve live POC
planning, live runtime behavior, or any additional Ithildin authority.

## Decision Header

- Decision ID: `PRD-SANDBOX-STATIC-PREFLIGHT-001`
- Date:
- Owner:
- Reviewer:
- Target lane: `ERG-003` sandbox/VM static preflight.
- Requested by:
- Related downstream lane: `ERG-004` live sandbox/VM worker proof of concept.
- Related disposition packet: `var/review-packets/v3/sandbox-vm-static-preflight-disposition`
- Related normalized response:
  `var/review-runs/sandbox-vm-static-preflight/normalized-response.json`
- Related findings: `EXT-SVP-###` if present.

## Trigger And Requested Change

- Trigger: external/source reviewer accepts the CLI-only static profile preflight lane for
  local-preview fixture evidence.
- Requested change: record that `ERG-003` may move from `external_review_required` to
  `closed_local_preview_static_preflight`.
- Why this cannot stay documentation-only: downstream `ERG-004` planning depends on a clear,
  committed, hash-bound static-preflight disposition.
- Current boundary being changed: no runtime boundary changes; this is a review/disposition marker.

## Scope

Static preflight disposition remains limited to CLI-only fixture evidence.

- Allowed scope: disposition record, static preflight review evidence, normalized reviewer response,
  finding files, closure-matrix update, enterprise gap-matrix update, external-review queue update,
  post-RC decision-register update, live POC precondition status, and regenerated review evidence.
- Explicitly forbidden scope: runtime implementation, live VM/container inspection,
  VM/container lifecycle management, sandbox orchestration, Mission Control runtime behavior, local
  model invocation, trusted-host promotion, network expansion, API/MCP profile loading, new governed
  tool powers, production identity, runtime Postgres, hosted telemetry, remote MCP, SIEM adapter
  behavior, compliance automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP,
  broad filesystem writes, plugin SDK behavior, live POC planning approval, or public/security-product
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
- Mission Control impact: none.
- Sandbox/VM impact: static fixture evidence only.
- Local model impact: none.
- Trusted-host promotion impact: none.
- SIEM/telemetry impact: none.
- Identity/storage/remote impact: none.
- Compliance/public-positioning impact: none.

## Required Evidence

- Required source-review or external-review evidence:
  `var/review-runs/sandbox-vm-static-preflight/normalized-response.json`.
- Required closure gate: `make sandbox-vm-static-preflight-disposition-closure-check` reports
  `closure_ready: true` and `allowed_closure_state: closed_local_preview_static_preflight`.
- Required reviewer access: `source-level` or `packet-and-source`.
- Required finding namespace: `EXT-SVP-###`.
- Required packet hash: `reviewed_packet_hash` matches the static preflight disposition packet being
  dispositioned.
- Required follow-up checklist: `sandbox-vm-static-preflight-triage-update.md`.
- Required response-application record:
  `sandbox-vm-static-preflight-response-application-record.md`.
- Required tests: `make sandbox-vm-static-preflight-response-dry-run`,
  `make sandbox-vm-static-preflight-disposition-closure-check`,
  `make sandbox-vm-static-preflight-disposition-record-skeleton-check`,
  `make sandbox-vm-static-preflight-response-application-record-check`, and `make release-check`.
- Required packet artifacts: static preflight source-review packet, external-review bundle,
  response kit, disposition plan, disposition packet, external-response intake, closure gate, and
  reviewer reproduction map.
- Required downstream note: `ERG-004 remains blocked` unless and until a separate live POC decision
  record later authorizes implementation-planning-only status.

## Risk And Boundary Decision

- Accepted-risk impact: no new accepted risk for disposition-only closure.
- Data exposure impact: planned evidence must not include prompts, file contents, diffs, response
  bodies, raw host paths, secrets, dependency names, package script values, raw sandbox internals, or
  local model prompts/responses.
- Permission/authority impact: no authority transfer.
- Audit/evidence impact: disposition evidence is local documentation and normalized reviewer
  evidence, not runtime audit custody.
- Recovery/rollback impact: revert the disposition record and keep `ERG-003` as
  `external_review_required` if evidence is later found stale, mismatched, malformed, or overbroad.
- Residual risk: the static preflight is still fixture/profile evidence, not proof that any live
  sandbox/VM worker is safe.
- Go/no-go outcome: go for static-preflight local-preview disposition only; no-go for live POC
  planning, runtime implementation, sandbox orchestration, Mission Control runtime behavior, local
  model invocation, trusted-host promotion, SIEM adapter behavior, or authority transfer.
- Decision rationale: the reviewed static preflight lane may support downstream evidence planning
  only when bounded by this record and the closure gate.

## Downstream Constraints

After this disposition, `ERG-004` remains blocked. A favorable `ERG-003` disposition may satisfy one
precondition for a later live POC decision record, but it does not approve:

- live POC implementation planning;
- runtime implementation;
- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation;
- trusted-host promotion;
- network expansion;
- API/MCP profile loading;
- SIEM adapter behavior;
- new governed tool powers;
- public/security-product positioning.

## Validation

Run:

```sh
make sandbox-vm-static-preflight-disposition-record-skeleton-check
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-response-dry-run
```

These checks must remain green before `make release-check` can pass.

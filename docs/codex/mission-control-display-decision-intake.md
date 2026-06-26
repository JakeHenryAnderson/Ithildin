# Mission Control Display Decision Intake

Status: decision-intake planning packet for `ERG-002` and `PRD-MC-DISPLAY-001`.

Current governed tool count: `24`.

Current `ERG-002` status: `planning_only`.

Current selected capability: `not selected`.

This intake defines the evidence required before a future post-RC decision record may approve any
Mission Control display/importer runtime work. It does not approve runtime behavior, API callbacks,
MCP transports, Mission Control execution behavior, Mission Control policy authority, Mission
Control approval authority, Mission Control audit authority, local model invocation, VM/container
lifecycle management, sandbox orchestration, trusted-host promotion, SIEM adapters, production
identity, runtime Postgres, hosted telemetry, shell, Docker/Kubernetes/browser governed powers,
arbitrary HTTP, broad filesystem writes, compliance automation, or public/security-product claims.

Validate this intake with:

```sh
make mission-control-display-decision-intake-check
make mission-control-display-external-response-intake-check
```

## Required Preconditions

Any future implementation decision for `PRD-MC-DISPLAY-001` must prove:

- a Mission Control-side implementation plan exists for exact file/import display behavior;
- the Mission Control-side plan accepts only operator-selected local packet sources;
- the Ithildin handoff schema contract remains metadata-only;
- the negative fixture plan covers stale, mismatched, unsafe attachment, authority overclaim, and
  content leak cases;
- the Mission Control display review packet has been generated from the same commit as the decision
  evidence;
- warning chips remain mandatory and visible;
- source/review evidence exists for the exact Mission Control-side importer behavior;
- no post-RC decision record claims Mission Control execution, policy, approval, audit, sandbox,
  local-model, trusted-host promotion, SIEM, identity, storage, remote, or compliance authority.
- any external reviewer response is normalized through
  `mission-control-display-external-response-intake.md` before a separate committed triage update
  changes this lane's status.

## Required Decision Evidence

A future decision record must include at least:

| Evidence | Required source |
| --- | --- |
| Display proposal | `mission-control-display-integration-proposal.md` |
| Importer plan | `mission-control-display-importer-plan.md` |
| Mission Control-side handoff | `mission-control-side-handoff-plan.md` |
| Handoff schema contract | `mission-control-handoff-schema-contract.md` |
| Negative fixture plan | `mission-control-handoff-negative-fixtures.md` |
| Review packet | `make mission-control-display-review-packet` |
| Seed handoff evidence | `make hello-world-mission-control-handoff-check` |
| No-new-powers evidence | `make no-new-powers-guardrail` and `make tool-surface-invariant-gate` |
| Post-RC decision evidence | `make post-rc-decision-register-check` |

## Allowed Future Decision Outcomes

A future post-RC decision may choose only one of these outcomes:

- `go_for_mission_control_side_display_importer_planning`: continue Mission Control-side design,
  fixtures, and source-review packet work only.
- `conditional_go_for_display_only_importer_implementation`: approve one exact Mission Control-side
  file/import display implementation after the preconditions above are proven.
- `no_go`: keep the lane as planning-only and require additional review evidence.

Any outcome other than `no_go` must still keep Ithildin runtime behavior unchanged unless a separate
Ithildin implementation decision explicitly says otherwise.

## Required Negative Evidence

Before implementation, evidence must show rejection or warning behavior for:

- missing or unsupported schema;
- non-`metadata_only` handoff status;
- Mission Control execution, policy, approval, or audit authority overclaim;
- local model, VM/container, sandbox, shell, host-promotion, or SIEM authority overclaim;
- absolute, parent-traversal, URL, or runtime-instruction attachment paths;
- missing display allowlist, hidden-field denylist, or warning chips;
- stale commit or timestamp evidence;
- missing or mismatched artifact hashes;
- raw prompt, file content, diff, response body, token, private key, raw host path, environment
  value, dependency name, package script value, or raw sandbox-internal display.

## Current Allowed State

Current artifacts may reference this intake as a future decision checklist only. Today this intake
allows docs, schema contracts, static fixtures, review packets, source-review questions, and
operator warnings. It does not approve runtime behavior.

Current output must continue to report:

- Mission Control planning allowed: `true`;
- Mission Control runtime allowed: `false`;
- Mission Control execution authority allowed: `false`;
- Mission Control policy authority allowed: `false`;
- Mission Control approval authority allowed: `false`;
- Mission Control audit authority allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- trusted-host promotion allowed: `false`;
- SIEM adapter allowed: `false`;
- new power classes allowed: `false`;
- public/security-product positioning allowed: `false`.

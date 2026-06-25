# Trusted-Host Promotion Negative Fixtures

Status: design-only negative fixture contract for `ERG-005` and `PRD-TRUSTED-HOST-001`.

Current governed tool count: `24`.

Current `ERG-005` status: `blocked`.

Current selected capability: `not selected`.

This document defines the negative fixture and transcript families that any future trusted-host
promotion implementation must reject before a sandbox artifact could move to host staging or an
approved-output zone. It does not approve runtime behavior, direct host writes, overwrite/delete/move
behavior, broad archive extraction, automatic promotion, promotion without exact artifact hash
binding, promotion without approval evidence, API/MCP behavior, Mission Control runtime behavior,
local model invocation, VM/container lifecycle management, sandbox orchestration, SIEM adapters,
production identity, runtime Postgres, hosted telemetry, shell, Docker/Kubernetes/browser governed
powers, arbitrary HTTP, broad filesystem writes, compliance automation, or public/security-product
claims.

Validate this negative fixture contract with:

```sh
make trusted-host-promotion-negative-fixtures-check
```

The matching source/destination zone contract is
[trusted-host-promotion-zone-contract.md](trusted-host-promotion-zone-contract.md), validated with
`make trusted-host-promotion-zone-contract-check`.
The matching implementation-plan skeleton is
[trusted-host-promotion-implementation-plan.md](trusted-host-promotion-implementation-plan.md),
validated with `make trusted-host-promotion-implementation-plan-check`.

## Fixture Scope

These are static contract fixtures only. They do not write host files, promote artifacts, inspect a
real VM, call Mission Control, invoke a model, add MCP tools, add API endpoints, add policy rules,
add executors, mutate approval state, or create runtime promotion records.

Future runtime fixtures may use this document to build denial transcripts, but current evidence may
only report `promotion_status: not_promoted`.

## Required Negative Fixtures

A future trusted-host promotion implementation must reject or mark recovery/review-required for these
fixture families before treating promotion as allowed:

| Fixture ID | Scenario | Expected safe outcome |
| --- | --- | --- |
| `TRUSTED-PROMOTION-NEG-001` | unsupported or missing promotion schema version | reject as unsupported schema |
| `TRUSTED-PROMOTION-NEG-002` | unsupported state value outside the state machine | reject as unsupported state |
| `TRUSTED-PROMOTION-NEG-003` | transition not listed in the state-machine sketch | reject as invalid transition |
| `TRUSTED-PROMOTION-NEG-004` | request lacks source artifact hash | reject as missing artifact hash |
| `TRUSTED-PROMOTION-NEG-005` | request lacks approval ID | reject as missing approval evidence |
| `TRUSTED-PROMOTION-NEG-006` | request lacks one-time scope hash | reject as missing scope evidence |
| `TRUSTED-PROMOTION-NEG-007` | request lacks policy or manifest hash | reject as missing governance evidence |
| `TRUSTED-PROMOTION-NEG-008` | approval principal differs from request principal | reject as approval scope mismatch |
| `TRUSTED-PROMOTION-NEG-009` | workspace, sandbox, source label, staging label, or approved label differs from the approved scope | reject as approval scope mismatch |
| `TRUSTED-PROMOTION-NEG-010` | approval expired at execution time | reject as expired approval |
| `TRUSTED-PROMOTION-NEG-011` | approval ID, promotion ID, request hash, or one-time scope is reused | reject as replay denied |
| `TRUSTED-PROMOTION-NEG-012` | source artifact hash changed after approval | reject as stale source artifact |
| `TRUSTED-PROMOTION-NEG-013` | policy hash, manifest hash, schema version, or principal registry evidence changed after approval | reject as stale governance evidence |
| `TRUSTED-PROMOTION-NEG-014` | destination already exists or hash does not match expected approved-output hash | reject as target conflict |
| `TRUSTED-PROMOTION-NEG-015` | requested overwrite, delete, move, chmod, archive extraction, or automatic promotion | reject as unsupported operation |
| `TRUSTED-PROMOTION-NEG-016` | absolute path, parent traversal, encoded traversal, URL-shaped destination, Unicode ambiguity, or control-character label | reject as unsafe label |
| `TRUSTED-PROMOTION-NEG-017` | hidden path, `.git`, symlink, hardlink, directory, binary target, unsupported type, or broad archive target | reject as unsafe target |
| `TRUSTED-PROMOTION-NEG-018` | missing warning-state acknowledgement or stale evidence timestamp | reject as missing review acknowledgement |
| `TRUSTED-PROMOTION-NEG-019` | runtime packet commit does not match the reviewed packet commit | reject as stale review packet |
| `TRUSTED-PROMOTION-NEG-020` | request contains file contents, prompts, diffs, response bodies, raw host paths, raw sandbox-internal paths, VM logs, shell output, package script values, dependency names, environment values, tokens, private keys, or secret-like fields | reject as sensitive payload |
| `TRUSTED-PROMOTION-NEG-021` | request claims Mission Control executed actions, invoked a local model, started a VM/container, controlled Docker/Kubernetes/browser, or ran shell | reject as authority overclaim |
| `TRUSTED-PROMOTION-NEG-022` | request claims SIEM custody, external notarization, compliance automation, production identity, public/security-product readiness, or tamper-proof evidence | reject as product-boundary overclaim |
| `TRUSTED-PROMOTION-NEG-023` | incomplete attempt after future placement begins and completion evidence is missing | report `promotion_recovery_required` with read-only diagnostics only |
| `TRUSTED-PROMOTION-NEG-024` | current local-preview/demo artifact tries to report anything other than `not_promoted` | reject as current-boundary overclaim |

## Required Transcript Shape

Future denial transcripts must be secret-free and use stable labels:

```json
{
  "schema_version": "1",
  "fixture_id": "TRUSTED-PROMOTION-NEG-001",
  "promotion_id": "promotion_fixture",
  "attempted_transition": "promotion_requested->promotion_completed",
  "expected_outcome": "reject",
  "observed_status": "denied",
  "reason_label": "invalid_transition",
  "promotion_status": "not_promoted",
  "runtime_promotion_performed": false,
  "auto_promotion_performed": false,
  "trusted_host_write_performed": false,
  "safe_metadata_only": true
}
```

For future recovery-required cases, the transcript may use `promotion_recovery_required` only when a
separate implementation decision has approved promotion attempts. Current local-preview evidence may
not claim that recovery-required runtime behavior exists.

## Safe Error Expectations

Negative fixture validation and future transcripts must report reason labels only. They must not echo
file contents, prompts, diffs, response bodies, raw host paths, raw sandbox-internal paths, shell
output, VM logs, usernames, home directories, package script values, dependency names, environment
names or values, registry URLs, tokens, private keys, stack traces, or model outputs.

## Current Implementation Boundary

This contract is a planning and review artifact. It does not implement trusted-host promotion,
host-placement attempts, repair, rollback, reconciliation, promotion diagnostics, Mission Control
runtime behavior, local model invocation, VM/container lifecycle management, sandbox orchestration,
SIEM adapters, production identity, runtime Postgres, hosted telemetry, shell execution, Docker or
Kubernetes control, browser automation, arbitrary HTTP, broad filesystem writes, compliance
automation, or public/security-product posture.

Current outputs must continue to report:

- decision record required: `true`;
- implementation approved: `false`;
- runtime changes allowed: `false`;
- trusted-host promotion allowed: `false`;
- direct host writes allowed: `false`;
- overwrite/delete/move allowed: `false`;
- broad archive extraction allowed: `false`;
- automatic promotion allowed: `false`;
- promotion without exact artifact hash binding allowed: `false`;
- promotion without approval evidence allowed: `false`;
- Mission Control runtime allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- SIEM adapter allowed: `false`;
- new power classes allowed: `false`;
- public/security-product positioning allowed: `false`.

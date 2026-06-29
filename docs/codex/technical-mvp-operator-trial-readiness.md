# Ithildin Technical MVP Operator Trial Readiness

Status: checked operator-trial readiness view for the technical MVP.

This document answers the practical question: what specifically remains before Ithildin can be
treated as a technical MVP product for local-preview use? It is a readiness view, not a new runtime
approval, product-positioning claim, or enterprise/security-product sign-off.

Run:

```sh
make technical-mvp-operator-trial-readiness
```

## Current Answer

Ithildin is ready for a local-preview operator trial of the technical MVP surface when the checked
gates continue to pass from the same commit.

That means a local operator can validate the governed gateway, review console, Agent Run evidence,
approval and audit surfaces, local demo packets, and existing bounded governed tools. The remaining
hands-on work is to run the operator trial, record pass/fail evidence, and keep enterprise blocked
lanes from being mistaken for completed product capabilities.

## What Is Ready

The following surfaces are ready for local-preview operator trial:

| Area | Current state | Checked evidence |
| --- | --- | --- |
| Core governed gateway | `closed_local_preview` | `make release-check`, `make tool-surface-invariant-gate`, `make policy-parity` |
| Read-only and Git/project intelligence | `closed_local_preview` | `make read-only-capability-inventory-gate`, `make read-only-project-intelligence`, `make next-capability-readiness` |
| Evidence and review packets | `closed_local_preview` | `make review-candidate`, `make packet-redaction-scan`, `make v1-operator-trial-record` |
| Operator workbench and demo docs | `ready_for_operator_trial` | `make workbench-readiness`, `make demo-flow-readiness`, `make demo-evidence-readiness`, `make operator-sandbox-demo-readiness` |
| Current technical MVP map | `checked` | `make technical-mvp-ticket-map` |

## What Remains Before A Hands-On Technical MVP Trial

Run the local trial from a clean tree:

```sh
make release-check
make review-candidate
make v1-operator-trial-record
```

If Docker Compose is available and the operator wants to exercise the local API/UI path:

```sh
make demo-seed
make compose-up
make compose-smoke
```

Then inspect the local review console and evidence surfaces described in:

- `docs/codex/v1.0-operator-quickstart.md`
- `docs/codex/v1.0-operator-trial-checklist.md`
- `docs/codex/operator-managed-sandbox-demo-guide.md`

After the Compose path, always clean up:

```sh
make compose-down
```

If Compose is unavailable, record it as skipped in the operator trial record. Skipping Compose does
not prove the live API/UI path was exercised.

## Current External Review State

The current enterprise review send set remains:

- `ERG-003`: static sandbox/VM preflight disposition.
- `ERG-002`: Mission Control display/import planning review.

Use:

```sh
make enterprise-review-send-refresh
make enterprise-response-waiting-room
```

This readiness view does not normalize external responses or close ERG lanes. When real responses
exist, use the checked response-intake path rather than editing status docs by hand.

## What Remains Beyond Technical MVP

The following remain blocked or planning-only beyond the technical MVP:

- production deployment readiness;
- production identity or enterprise RBAC;
- runtime Postgres;
- hosted telemetry;
- remote MCP hosting;
- Mission Control execution authority;
- Ithildin-managed VM/container lifecycle;
- trusted-host promotion;
- SIEM custody;
- compliance automation;
- public/security-product positioning;
- new governed tool powers.

## What This Gate Does Not Do

`make technical-mvp-operator-trial-readiness` is read-only evidence plumbing. It:

- does not start services;
- does not call governed tools;
- does not approve sandbox/VM lifecycle control;
- does not grant Mission Control execution authority;
- does not approve public/security-product positioning;
- does not change tool manifests, policies, API/MCP behavior, approval behavior, audit behavior, or
  UI runtime behavior.

## Validation

Run:

```sh
make technical-mvp-operator-trial-readiness
make technical-mvp-ticket-map
make v1-operator-trial-record-check
make release-check
make review-candidate
```

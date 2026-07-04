# Ithildin Technical MVP Ticket Map

Status: checked technical-MVP ticket map for the current local-preview product.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Latest implemented tool: `sandbox.artifact.write_text`.

This map answers what is specifically left before Ithildin is a technical MVP product. It is a
ticket map and evidence index, not a new roadmap, runtime approval, or enterprise/security-product
claim.

Run:

```sh
make technical-mvp-ticket-map
```

## Technical MVP Boundary

Technical MVP means a local operator can run Ithildin, connect an MCP-capable agent, observe
mediated Agent Runs, use the bounded read-only/Git/project intelligence surface, request
approval-gated writes only through existing governed flows, and hand reviewers a reproducible
evidence packet.

Technical MVP does not mean production deployment readiness, production identity or enterprise RBAC,
runtime Postgres, hosted telemetry, remote MCP hosting, Mission Control execution authority,
Ithildin-managed VM/container lifecycle, trusted-host promotion, SIEM custody, compliance automation,
public/security-product positioning, or new governed tool powers.

## Ticket Map

| Ticket | Area | Current state | Done evidence | Next action |
| --- | --- | --- | --- | --- |
| `MVP-001` | Core governed gateway foundation | `closed_local_preview` | `make tool-surface-invariant-gate`, `make no-new-powers-guardrail`, `make policy-parity`, `make release-check` | Maintain only; no new power class without a new proposal and gate. |
| `MVP-002` | Read-only and Git intelligence tools | `closed_local_preview` | `make read-only-capability-inventory-gate`, `make read-only-project-intelligence`, `make next-capability-readiness` | Keep `next_candidate` as `not selected` unless a new explicit capability sprint begins. |
| `MVP-003` | Evidence, review, and packet machinery | `closed_local_preview` | `make review-candidate`, `make packet-redaction-scan`, `make review-run-manifest-check`, `make reviewer-findings-check` | Maintain packet freshness and same-commit transcripts. |
| `MVP-004` | Operator workbench and local demo | `operator_trial_observed` | `make workbench-readiness`, `make demo-flow-readiness`, `make demo-evidence-readiness`, `make live-demo-status`, `make v1-operator-trial-observed-check` | Keep observed trial evidence fresh for local technical-preview handoff. |
| `MVP-005` | Mission Control display/import handoff | `planning_only` | `make mission-control-enterprise-status-import-check`, `make mission-control-display-external-review-bundle`, `make mission-control-display-response-kit` | Send or review the `ERG-002` packet; keep Mission Control display/import design-only until disposition. |
| `MVP-006` | Sandbox/VM static preflight | `external_review_required` | `make sandbox-vm-static-preflight-external-review-bundle-check`, `make sandbox-vm-static-preflight-response-kit-check`, `make sandbox-vm-static-preflight-disposition-closure-check` | Send or review the `ERG-003` packet before any live sandbox/VM POC decision. |
| `MVP-007` | Live sandbox/VM worker proof of concept | `blocked` | `make sandbox-vm-live-poc-preconditions-ready-check`, `make sandbox-vm-live-poc-decision-packet-check`, `make sandbox-vm-live-poc-response-kit-check` | Wait for favorable `ERG-003` disposition and a separate decision record. |
| `MVP-008` | Trusted-host artifact promotion | `blocked` | `make trusted-host-descriptor-contract-check`, `make trusted-host-promotion-decision-intake-check`, `make trusted-host-promotion-state-machine-check`, `make trusted-host-promotion-external-review-bundle-check` | Keep host promotion blocked until a later decision record and source review. |
| `MVP-009` | Enterprise architecture lanes | `planning_only` | `make production-identity-storage-architecture-check`, `make siem-export-adapter-architecture-check`, `make compliance-mapping-architecture-check` | Continue architecture planning only; no runtime implementation from these lanes. |
| `MVP-010` | Public/security-product positioning | `blocked` | `make public-security-product-positioning-decision-intake-check`, `make public-positioning-external-review-bundle-check`, `make public-security-product-positioning-response-kit-check` | Keep public/security-product positioning no-go until a later explicit claim decision. |

## Current Best Next Step

The current best next step is:

```sh
make release-check
make review-candidate
make enterprise-review-send-refresh
```

Then send the current recommended enterprise packets:

- `ERG-003`: static sandbox/VM preflight disposition.
- `ERG-002`: Mission Control display/import planning review.

After real reviewer responses exist, do not edit committed status docs directly. Use the checked
response path:

```sh
make enterprise-response-waiting-room
make enterprise-response-paste-preflight
make enterprise-response-intake-refresh
```

## Technical MVP Acceptance Snapshot

Technical MVP is locally usable when:

- `make release-check` passes from a clean tree;
- `make review-candidate` passes from the same commit;
- packet redaction scan reports `findings: 0`;
- tool count remains `24`;
- selected capability remains `not selected`;
- capability expansion remains blocked;
- public/security-product positioning remains blocked;
- the local operator can follow `v1.0-operator-quickstart.md` and `v1.0-operator-trial-checklist.md`.

## What Remains Beyond Technical MVP

The enterprise-ready goal still requires separate ERG decisions for Mission Control runtime
behavior, live sandbox/VM inspection, trusted-host promotion, production identity/storage,
SIEM-shaped delivery, compliance mapping support, and public/security-product positioning. Those
are not completed by this technical MVP map.

## Validation

Run:

```sh
make technical-mvp-ticket-map
make v1-progress-assessment
make enterprise-operator-next-action
make release-check
make review-candidate
```

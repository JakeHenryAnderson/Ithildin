# Enterprise Current Checkpoint

Status: checked operator checkpoint for the current v1.0 local-preview and enterprise-readiness
handoff state.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make enterprise-current-checkpoint
```

This checkpoint is a read-only summary. It does not record external review, normalize responses,
close enterprise lanes, approve runtime behavior, or approve public/security-product positioning.

## Current Interpretation

- v1.0 local-preview RC packet generation is ready through `make review-candidate`.
- The current reviewed local-preview boundary remains the governed MCP/tool gateway with 24 tools.
- Capability expansion remains blocked.
- Runtime changes remain blocked outside already-approved local-preview tool behavior.
- Public/security-product positioning remains blocked.
- Enterprise response evidence is not present yet.
- `ERG-004`: descriptor-only sandbox/VM live POC runtime source review is locally dispositioned
  for continued local-development progress only.
- `ERG-005`: trusted-host artifact promotion review is the next blocked design lane.
- The descriptor-only runtime slice has both an internal source review and a high-effort internal
  proxy disposition with no findings. That is not external review and does not approve live
  VM/container runtime behavior.

Validate the active ERG-005 trusted-host promotion review surface with:

```sh
make trusted-host-descriptor-contract-check
make trusted-host-promotion-decision-intake-check
make trusted-host-promotion-state-machine-check
make trusted-host-promotion-negative-fixtures-check
make trusted-host-promotion-zone-contract-check
make trusted-host-promotion-implementation-plan-check
make trusted-host-promotion-limited-runtime-plan-check
make trusted-host-promotion-limited-runtime-ticket-check
make trusted-host-promotion-source-review-packet-check
make trusted-host-promotion-disposition-packet-check
make trusted-host-promotion-external-review-bundle-check
make trusted-host-promotion-response-kit-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

The committed `sandbox-vm-live-poc-runtime-gate-readiness-decision-record.md` allows only
descriptor-only implementation planning. The descriptor-only plan and implementation ticket record
the next non-runtime checkpoints before any future descriptor slice is considered. The ERG-005
limited runtime plan and ticket skeleton record the next non-runtime checkpoints before any future
staging-only artifact promotion slice is considered. Those records still do not approve runtime
implementation, live VM/container inspection, sandbox orchestration, Mission Control runtime
behavior, local model invocation, host writes, trusted-host promotion, network expansion, API/MCP
profile loading, or new governed tool powers.

## Recommended Next Actions

The historical dual-send artifacts remain below for lineage and response-intake fallback. They are
not the active post-disposition route while `make enterprise-operator-next-action` reports
`prepare_erg005_trusted_host_promotion_review`.

The current recommended enterprise handoff set is:

1. `ERG-005`: trusted-host artifact promotion review.

Generate or refresh the active send-ready operator artifact with:

```sh
make enterprise-send-now
make trusted-host-promotion-external-review-bundle
make trusted-host-promotion-response-kit
```

The active ERG-005 source-review packet and response kit are:

```sh
var/review-packets/v3/trusted-host-promotion-external-review/
var/review-packets/v3/trusted-host-promotion-response-kit/
```

The bounded implementation-planning checkpoint for the next ERG-005 slice is:

```sh
docs/codex/trusted-host-promotion-limited-runtime-plan.md
docs/codex/trusted-host-promotion-limited-runtime-ticket.md
```

It is checked with `make trusted-host-promotion-limited-runtime-plan-check` and
`make trusted-host-promotion-limited-runtime-ticket-check`. These checkpoints still do not approve
runtime trusted-host promotion, direct host writes, automatic promotion, Mission Control runtime
behavior, sandbox orchestration, or new governed tool powers.

After a real ERG-005 trusted-host reviewer response arrives, do not edit status docs directly.
Run the lane-specific response checks before any committed disposition update:

```sh
make trusted-host-promotion-response-dry-run
make trusted-host-promotion-disposition-closure-check
```

Follow the descriptor-only response application playbook before any committed disposition update.
The general enterprise response flow remains documented by:

```sh
make enterprise-response-waiting-room
make enterprise-response-now
make enterprise-response-paste-preflight
make enterprise-response-intake-quickstart
make enterprise-response-application-protocol
make enterprise-response-application-rehearsal
```

The historical ERG-003/ERG-002 dual-send commands remain available only for lineage and fallback.

## Current Packet Paths

- v1.0 RC packet: `var/review-packets/v1.0/rc/`
- historical consolidated packet: `var/review-packets/v0.2/GPT-5.5-Pro-consolidated/`
- `ERG-003` packet: `var/review-packets/v3/sandbox-vm-static-preflight-external-review/`
- `ERG-002` packet: `var/review-packets/v3/mission-control-display-external-review/`
- `ERG-004` descriptor-only source-review packet:
  `var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-source-review/`
- `ERG-004` descriptor-only response inbox:
  `var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox/`
- dual-review outbox: `var/review-packets/v3/enterprise-dual-review-outbox/`
- send manifest: `var/review-packets/v3/enterprise-review-send-manifest/`
- send quickstart: `var/review-packets/v3/enterprise-review-send-quickstart/`
- send receipt template: `var/review-packets/v3/enterprise-review-send-receipt-template/`
- send package: `var/review-packets/v3/enterprise-review-send-package/`
- send session record: `var/review-runs/enterprise-review-send-session-record/`
- dual-response inbox: `var/review-runs/enterprise-dual-response-inbox/`
- response inbox: `var/review-runs/enterprise-response-inbox/`
- response status snapshot: `var/review-runs/enterprise-response-status-board/`

Generated packet paths are handoff artifacts, not source of truth. Regenerate them before sending.

## What This Checkpoint Does Not Approve

This checkpoint does not approve:

- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation;
- trusted-host promotion;
- SIEM adapter runtime behavior;
- production identity or enterprise RBAC;
- runtime Postgres;
- hosted telemetry;
- remote MCP hosting;
- compliance automation;
- public/security-product positioning;
- new governed tool powers.

## Validation

Run:

```sh
make enterprise-current-checkpoint
make enterprise-review-send-readiness
make enterprise-response-status-board
make v1-progress-assessment
```

`make release-check` includes this checkpoint so stale top-level enterprise status, recommended
packet ordering, tool count, or blocked-boundary wording cannot quietly drift.

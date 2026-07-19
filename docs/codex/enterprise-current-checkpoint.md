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
- `ERG-005`: staging-only trusted-host promotion runtime source findings are dispositioned for the
  bounded local-preview slice; ERG-005, placement authority, broader promotion, release, and UAT
  remain blocked.
- Handoff readiness marker: `ERG-006`/`ERG-007`: production identity/storage architecture review is next.
- The descriptor-only runtime slice has both an internal source review and a high-effort internal
  proxy disposition with no findings. That is not external review and does not approve live
  VM/container runtime behavior.

Validate the active planning-only ERG-006/ERG-007 architecture-review surface with:

```sh
make production-identity-storage-architecture-check
make production-identity-storage-disposition-packet-check
make production-identity-storage-external-review-bundle-check
make production-identity-storage-response-kit-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

The accepted ERG-005 response closes only its two tracked runtime source findings. The active
ERG-006/ERG-007 packet asks whether the existing production identity, tenancy, session, storage,
migration, retention, recovery, and custody architecture is coherent enough for continued
planning. It does not approve PIS implementation packages, production identity, enterprise RBAC,
remote administration, runtime Postgres, migrations, production Node transport, or new governed
tool powers.

## Recommended Next Actions

The historical ERG-005 and dual-send artifacts remain below for lineage and response-intake
fallback. They are not the active post-disposition route while
`make enterprise-operator-next-action` reports
`prepare_erg006_erg007_production_identity_storage_architecture_review`.

The current recommended enterprise handoff set is:

1. `ERG-006`/`ERG-007`: production identity and durable-storage architecture review.

Generate or refresh the active source-review artifact with:

```sh
make enterprise-send-now
make production-identity-storage-external-review-bundle
make production-identity-storage-response-kit
```

The active ERG-006/ERG-007 architecture-review packet and response kit are:

```sh
var/review-packets/v3/production-identity-storage-external-review/
var/review-packets/v3/production-identity-storage-response-kit/
```

The bounded implementation-planning checkpoint for the next ERG-005 slice is:

```sh
docs/codex/trusted-host-promotion-limited-runtime-plan.md
docs/codex/trusted-host-promotion-limited-runtime-ticket.md
docs/codex/trusted-host-promotion-runtime-implementation-decision.md
docs/codex/trusted-host-promotion-runtime-implementation.md
docs/codex/v3-trusted-host-promotion-runtime-internal-review.md
docs/codex/v3-trusted-host-promotion-runtime-review-closure.md
docs/codex/v3-trusted-host-promotion-runtime-local-disposition.md
docs/codex/trusted-host-promotion-runtime-source-review.md
```

It is checked with `make trusted-host-promotion-limited-runtime-plan-check` and
`make trusted-host-promotion-limited-runtime-ticket-check`. The implementation decision draft is
checked with `make trusted-host-promotion-runtime-implementation-decision-check`. The implemented
slice is checked with `make trusted-host-promotion-negative-transcripts` and
`make trusted-host-promotion-runtime-source-review-bundle-check`. These checkpoints still do not
approve broad trusted-host promotion, direct arbitrary host writes, automatic promotion, Mission
Control runtime behavior (historical name for the current Ithildin Command Center
runtime-authority boundary), sandbox orchestration, or new governed tool powers.

The Ithildin Command Center runtime-authority boundary remains unchanged: Command Center displays
and initiates governed workflows, while Gateway policy, approval, execution, and audit remain
authoritative.

Historical lineage: `ERG-005`: staging-only trusted-host promotion runtime source review is ready,
and its source findings are dispositioned. This lineage marker does not make ERG-005 the current
operator route or authorize broader promotion.

After a real ERG-006/ERG-007 production identity/storage reviewer response arrives, do not edit
status docs directly.
Run the lane-specific response checks before any committed disposition update:

```sh
make production-identity-storage-response-dry-run
make production-identity-storage-disposition-closure-check
```

Follow the production identity/storage response kit before any committed disposition update. The
general enterprise response flow remains documented by:

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
- `ERG-005` runtime source-review packet:
  `var/review-packets/v3/trusted-host-promotion-runtime-source-review/`
- `ERG-006`/`ERG-007` architecture-review packet:
  `var/review-packets/v3/production-identity-storage-external-review/`
- `ERG-006`/`ERG-007` response kit:
  `var/review-packets/v3/production-identity-storage-response-kit/`
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
- Mission Control runtime behavior, now described in current-facing docs as Ithildin Command Center
  runtime authority;
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

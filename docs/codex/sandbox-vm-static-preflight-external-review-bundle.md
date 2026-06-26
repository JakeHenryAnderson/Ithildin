# Sandbox/VM Static Preflight External Review Bundle

Status: launch bundle for `ERG-003` external/source review.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-003` status before reviewer disposition: `external_review_required`.

Generate the bundle with:

```sh
make sandbox-vm-static-preflight-external-review-bundle
```

Validate it with:

```sh
make sandbox-vm-static-preflight-external-review-bundle-check
```

The bundle is written under:

```text
var/review-packets/v3/sandbox-vm-static-preflight-external-review/
```

## Purpose

This is the reviewer-friendly launch artifact for the next recommended enterprise review:
`ERG-003` static sandbox/VM preflight disposition. It consolidates the existing source-review
packet, disposition packet, implementation contracts, fixture/negative evidence, response intake,
fail-closed closure gate, disposition-record skeleton, response dry run, triage-update checklist,
reproduction map, queue status, and command evidence into one 10-file handoff.

The goal is to make the external/source reviewer answer one narrow question:

> Can the CLI-only static sandbox/VM profile preflight lane move from `external_review_required` to
> `closed_local_preview_static_preflight` for local-preview fixture evidence only?

## Generated Artifacts

The generated bundle contains exactly these upload-friendly artifacts:

- `00_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_INDEX.md`
- `01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md`
- `02_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_PACKET.md`
- `03_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_PACKET.md`
- `04_SANDBOX_VM_STATIC_PREFLIGHT_IMPLEMENTATION_CONTRACTS.md`
- `05_SANDBOX_VM_STATIC_PREFLIGHT_FIXTURES_NEGATIVES.md`
- `06_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_CLOSURE_TRIAGE.md`
- `07_SANDBOX_VM_STATIC_PREFLIGHT_REPRODUCTION_QUEUE_STATUS.md`
- `08_SANDBOX_VM_STATIC_PREFLIGHT_COMMAND_EVIDENCE.md`
- `sandbox-vm-static-preflight-external-review-artifact-hashes.json`

`06_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_CLOSURE_TRIAGE.md` must include
`sandbox-vm-static-preflight-disposition-record-skeleton.md` so the external reviewer sees the
allowed future record shape while `ERG-003` remains open.

## Boundary

This launch bundle does not close `ERG-003`, does not record external review, and does not approve
runtime implementation. Only a later committed triage update using
`sandbox-vm-static-preflight-triage-update.md` may move `ERG-003` after real favorable
source-level evidence is normalized and the fail-closed closure gate reports `closure_ready: true`.

The following remain blocked:

- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation;
- trusted-host promotion;
- network expansion;
- API/MCP profile loading;
- new governed tool powers;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP;
- SIEM delivery;
- compliance automation;
- public/security-product positioning.

## Review Relationship

This bundle wraps and cross-checks:

- `sandbox-vm-static-preflight-source-review.md`;
- `sandbox-vm-static-preflight-disposition-packet.md`;
- `sandbox-vm-static-preflight-disposition-plan.md`;
- `sandbox-vm-static-preflight-disposition-closure-gate.md`;
- `sandbox-vm-static-preflight-external-response-intake.md`;
- `sandbox-vm-static-preflight-response-dry-run.md`;
- `sandbox-vm-static-preflight-triage-update.md`;
- `sandbox-vm-static-preflight-reviewer-reproduction-map.md`;
- `enterprise-external-review-queue.md`;
- `sandbox-vm-live-poc-preconditions-map.md`.

## Validation

Run:

```sh
make sandbox-vm-static-preflight-external-review-bundle-check
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-triage-update-check
make enterprise-external-review-queue-check
```

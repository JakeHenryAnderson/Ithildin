# Sandbox/VM Live POC External Review Bundle

Status: reviewer launch bundle for blocked `ERG-004`.

This document describes the generated bundle for the live sandbox/VM worker proof-of-concept
decision lane. The bundle exists to make external/source review easier by consolidating the
decision packet, evidence contract, preconditions, response intake, closure gate, dry-run evidence,
queue status, command evidence, and artifact hashes into one handoff directory.

Generate it with:

```sh
make sandbox-vm-live-poc-external-review-bundle
```

Validate wiring without regenerating the full handoff with:

```sh
make sandbox-vm-live-poc-external-review-bundle-check
```

Default output:

```text
var/review-packets/v3/sandbox-vm-live-poc-external-review/
```

## Generated Artifacts

The bundle contains exactly these review files plus one hash manifest:

1. `00_SANDBOX_VM_LIVE_POC_EXTERNAL_REVIEW_INDEX.md`
2. `01_SANDBOX_VM_LIVE_POC_EXTERNAL_REVIEW_PROMPT.md`
3. `02_SANDBOX_VM_LIVE_POC_DECISION_PACKET.md`
4. `03_SANDBOX_VM_LIVE_POC_CONTRACTS_AND_PRECONDITIONS.md`
5. `04_SANDBOX_VM_LIVE_POC_RESPONSE_CLOSURE_DRY_RUN.md`
6. `05_SANDBOX_VM_LIVE_POC_QUEUE_AND_BOUNDARY_STATUS.md`
7. `06_SANDBOX_VM_LIVE_POC_COMMAND_EVIDENCE.md`
8. `sandbox-vm-live-poc-external-review-artifact-hashes.json`

## Review Question

The bundle asks whether `ERG-004` can continue design-only decision review while live
VM/container inspection, VM/container lifecycle management, sandbox orchestration, Mission Control
runtime behavior, local model invocation, trusted-host promotion, SIEM adapter runtime behavior,
production identity, runtime Postgres, hosted telemetry, remote MCP, compliance automation,
public/security-product positioning, and new governed tool powers remain blocked.

The finding namespace is:

```text
EXT-LIVE-POC-###
```

## Boundary

This bundle does not close `ERG-004`, does not record external review, and does not approve
implementation planning. It is a handoff artifact only.

It does not approve:

- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation;
- trusted-host promotion;
- direct host writes or automatic host promotion;
- SIEM adapter runtime behavior;
- production identity or runtime Postgres;
- compliance automation or public/security-product positioning;
- new governed tool powers.

`ERG-004` remains blocked until favorable `ERG-003` static preflight disposition exists and a later
post-RC decision record explicitly authorizes implementation-planning-only movement.

## Validation

The check target verifies that:

- all generated bundle artifacts exist;
- artifact hashes cover the generated review files and do not hash the hash manifest itself;
- the prompt uses the `EXT-LIVE-POC-###` finding namespace;
- command evidence keeps all blocked runtime flags false;
- README, docs site, review docs, enterprise queue, enterprise runway, enterprise gap matrix, and
  post-RC decision register reference this launch bundle;
- `release-check` includes `sandbox-vm-live-poc-external-review-bundle-check`;
- `review-candidate` regenerates `sandbox-vm-live-poc-external-review-bundle`.

The bundle is also included in `make review-candidate` so the v1.0 RC review packet can carry the
latest `ERG-004` handoff without implying that the lane is closed or that live sandbox/VM runtime
work is approved.

# Sandbox/VM Live POC Response Kit

Status: response-intake kit for blocked `ERG-004` after external/source decision-packet review.

Current governed tool count: `24`.

Current `ERG-003` status: `closed_local_preview_static_preflight`.

Current `ERG-004` status: `blocked`.

Generate the kit with:

```sh
make sandbox-vm-live-poc-response-kit
```

Validate the kit wiring with:

```sh
make sandbox-vm-live-poc-response-kit-check
```

The generated kit lives under:

```text
var/review-packets/v3/sandbox-vm-live-poc-response-kit/
```

## Purpose

This kit is the operator/reviewer bridge between the blocked `ERG-004` decision packet and any later
post-RC decision-record update. It packages:

- response-intake guidance for `sandbox-vm-live-poc`;
- favorable and unfavorable normalized-response examples;
- closure-gate, prerequisite-disposition dry-run, decision-record, release-check, and
  review-candidate commands;
- queue, precondition, and boundary status;
- command evidence and artifact hashes.

It is meant to make the post-review path repeatable without pretending that review already happened.

## Artifacts

The kit generates:

1. `00_SANDBOX_VM_LIVE_POC_RESPONSE_KIT_INDEX.md`
2. `01_SANDBOX_VM_LIVE_POC_RESPONSE_INTAKE_GUIDE.md`
3. `02_SANDBOX_VM_LIVE_POC_NORMALIZED_RESPONSE_EXAMPLES.md`
4. `03_SANDBOX_VM_LIVE_POC_CLOSURE_TRIAGE_COMMANDS.md`
5. `04_SANDBOX_VM_LIVE_POC_QUEUE_AND_BOUNDARY_STATUS.md`
6. `05_SANDBOX_VM_LIVE_POC_RESPONSE_KIT_EVIDENCE.md`
7. `sandbox-vm-live-poc-response-kit-artifact-hashes.json`

## Boundary

This kit does not prove live POC external review happened, does not close `ERG-004`,
does not approve implementation planning, and does not approve live VM/container inspection,
VM/container lifecycle management, sandbox orchestration, Mission Control runtime behavior, local
model invocation, trusted-host promotion, network expansion, API/MCP profile loading, new governed
tool powers, production identity, runtime Postgres, hosted telemetry, remote MCP, SIEM delivery,
compliance automation, or public/security-product positioning.

Only a later committed decision-record update may move `ERG-004`, and only if real normalized
response evidence passes `make sandbox-vm-live-poc-decision-closure-check` with
`closure_ready: true`.
That future committed update must use `sandbox-vm-live-poc-decision-record-skeleton.md` as the
decision-record shape and must keep runtime implementation blocked unless a later explicit
implementation sprint is approved.

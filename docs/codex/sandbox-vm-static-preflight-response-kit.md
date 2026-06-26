# Sandbox/VM Static Preflight Response Kit

Status: response-intake kit for `ERG-003` after external/source review.

Current governed tool count: `24`.

Current `ERG-003` status: `external_review_required`.

Current `ERG-004` status: `blocked`.

Generate the kit with:

```sh
make sandbox-vm-static-preflight-response-kit
```

Validate the kit wiring with:

```sh
make sandbox-vm-static-preflight-response-kit-check
```

The generated kit lives under:

```text
var/review-packets/v3/sandbox-vm-static-preflight-response-kit/
```

## Purpose

This kit is the operator/reviewer bridge between the `ERG-003` external-review bundle and the later
triage update path. It packages:

- response-intake guidance for `sandbox-vm-static-preflight`;
- favorable and unfavorable normalized-response examples;
- closure-gate, dry-run, triage-update, release-check, and review-candidate commands;
- queue, precondition, and boundary status;
- command evidence and artifact hashes.

It is meant to make the post-review path repeatable without pretending that review already
happened.

## Artifacts

The kit generates:

1. `00_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_KIT_INDEX.md`
2. `01_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_INTAKE_GUIDE.md`
3. `02_SANDBOX_VM_STATIC_PREFLIGHT_NORMALIZED_RESPONSE_EXAMPLES.md`
4. `03_SANDBOX_VM_STATIC_PREFLIGHT_CLOSURE_TRIAGE_COMMANDS.md`
5. `04_SANDBOX_VM_STATIC_PREFLIGHT_QUEUE_AND_BOUNDARY_STATUS.md`
6. `05_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_KIT_EVIDENCE.md`
7. `sandbox-vm-static-preflight-response-kit-artifact-hashes.json`

## Boundary

This kit does not prove external review happened, does not close `ERG-003`, does not unblock
`ERG-004`, and does not approve live VM/container inspection, VM/container lifecycle management,
sandbox orchestration, Mission Control runtime behavior, local model invocation, trusted-host
promotion, network expansion, API/MCP profile loading, new governed tool powers, production
identity, runtime Postgres, hosted telemetry, remote MCP, SIEM delivery, compliance automation, or
public/security-product positioning.

Only a later committed triage update may move `ERG-003`, and only if real normalized response
evidence passes `make sandbox-vm-static-preflight-disposition-closure-check` with
`closure_ready: true`.
That future committed update must use `sandbox-vm-static-preflight-disposition-record-skeleton.md`
as the disposition-record shape and must keep `ERG-004` blocked.

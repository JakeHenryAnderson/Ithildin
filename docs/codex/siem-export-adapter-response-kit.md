# SIEM Export Adapter Response Kit

Status: response-intake kit for planning-only `ERG-008`.

Current governed tool count: `24`.

Current `ERG-008` status: `planning_only`.

Generate the kit with:

```sh
make siem-export-adapter-response-kit
```

Validate the kit wiring with:

```sh
make siem-export-adapter-response-kit-check
```

The generated kit lives under:

```text
var/review-packets/v3/siem-export-adapter-response-kit/
```

## Purpose

This kit is the operator/reviewer bridge between the planning-only `ERG-008` SIEM export adapter
disposition packet and any later post-RC triage update. It packages:

- response-intake guidance for `siem-export-adapter`;
- favorable and unfavorable normalized-response examples;
- closure-gate, dry-run, release-check, and review-candidate commands;
- queue, disposition, and boundary status;
- command evidence and artifact hashes.

It is meant to make the post-review path repeatable without pretending that review already happened.

## Artifacts

The kit generates:

1. `00_SIEM_EXPORT_ADAPTER_RESPONSE_KIT_INDEX.md`
2. `01_SIEM_EXPORT_ADAPTER_RESPONSE_INTAKE_GUIDE.md`
3. `02_SIEM_EXPORT_ADAPTER_NORMALIZED_RESPONSE_EXAMPLES.md`
4. `03_SIEM_EXPORT_ADAPTER_CLOSURE_TRIAGE_COMMANDS.md`
5. `04_SIEM_EXPORT_ADAPTER_QUEUE_AND_BOUNDARY_STATUS.md`
6. `05_SIEM_EXPORT_ADAPTER_RESPONSE_KIT_EVIDENCE.md`
7. `siem-export-adapter-response-kit-artifact-hashes.json`

## Boundary

This kit does not prove external review happened, does not close `ERG-008`, does not approve
implementation planning, and does not approve SIEM adapter behavior. It does not approve hosted
telemetry, remote delivery, custody-grade audit claims, external notarization, immutable storage,
security-operations control-plane claims, production identity, runtime Postgres, compliance
automation, hosted control plane behavior, remote MCP, sandbox orchestration, local model
invocation, trusted-host promotion, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP,
broad filesystem writes, plugin SDK behavior, new governed tool powers, or public/security-product
positioning.

Only a later committed triage update may move `ERG-008`, and only if real normalized response
evidence passes `make siem-export-adapter-disposition-closure-check` with `closure_ready: true`.
That future committed update may support continued architecture planning or a later
implementation-planning decision record; runtime SIEM adapter behavior, hosted telemetry, remote
delivery, custody-grade audit claims, external notarization, immutable storage, and
security-operations control-plane claims remain blocked until separate explicit implementation
decisions exist.

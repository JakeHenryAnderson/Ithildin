# Sandbox/VM Live POC Runtime Descriptor-Only Response Application Preflight

Status: checked preflight for applying a real `ERG-004` descriptor-only response.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-004` descriptor-only status before real reviewer disposition:
`descriptor_only_runtime_implemented_source_review_pending`.

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check
```

This preflight proves the ERG-004 descriptor-only response-application path is aligned before any
real reviewer response is applied. It does not normalize responses, does not write normalized
response files, does not mutate findings, does not record external review, does not close
`ERG-004`, does not approve descriptor-only source disposition, and does not approve runtime
implementation.

## Checked Path

- Source-review bundle:
  `sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle.md`.
- Response intake:
  `sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake.md`.
- Response dry run:
  `sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run.md`.
- Response application record:
  `sandbox-vm-live-poc-runtime-descriptor-only-response-application-record.md`.
- Response application playbook:
  `sandbox-vm-live-poc-runtime-descriptor-only-response-application-playbook.md`.

## Required Commands

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-implementation-check
make sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review-check
make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check
make sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake-check
make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-record-check
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-playbook-check
```

## Allowed Future State

If a real reviewer response later satisfies the application record and playbook, the only allowed
transition is:

```text
ERG-004 descriptor-only: source_review_pending -> descriptor_only_local_preview_disposition_ready
```

That transition still does not approve runtime implementation.

## Explicitly Blocked Scope

The preflight keeps runtime implementation, live VM/container inspection, VM/container lifecycle
management, sandbox orchestration, Mission Control runtime behavior, local model invocation,
trusted-host promotion, host writes, network expansion, API/MCP profile loading, SIEM adapter
runtime behavior, production identity, runtime Postgres, hosted telemetry, remote MCP, compliance
automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem
writes, plugin SDK behavior, new governed tool powers, and public/security-product positioning
blocked.

Blocked-boundary labels for release checks: live VM/container inspection, VM/container lifecycle management, Mission Control runtime behavior, API/MCP profile loading, SIEM adapter runtime behavior, hosted telemetry, compliance automation.

## Validation

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check
make release-check
```

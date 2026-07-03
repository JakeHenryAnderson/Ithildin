# Sandbox/VM Live POC Runtime Descriptor-Only Response Application Record

Status: process-only response-application record for the `ERG-004` descriptor-only source review.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Current `ERG-004` descriptor-only status before real reviewer disposition:
`descriptor_only_runtime_implemented_source_review_pending`.

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-record-check
```

This record is a manager-owned checklist for applying a future real `EXT-LIVE-DESC-###` response.
It does not normalize responses, does not write normalized response files, does not mutate findings,
does not record external review, does not close `ERG-004`, does not approve descriptor-only source
disposition by itself, and does not approve runtime implementation.

Use
[sandbox-vm-live-poc-runtime-descriptor-only-response-application-playbook.md](sandbox-vm-live-poc-runtime-descriptor-only-response-application-playbook.md)
as the command-order companion. Use
[sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight.md](sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight.md)
before applying any real descriptor-only reviewer response.

## Required Response Evidence

- Normalized response:
  `var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only/normalized-response.json`.
- Normalization area: `sandbox-vm-live-poc-runtime-descriptor-only`.
- Finding namespace: `EXT-LIVE-DESC-###`.
- Reviewed packet:
  `var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-source-review`.
- Required normalized response type: `ithildin.external_review.normalized_response`.
- Required source access: `source-level` or `packet-and-source`.
- Required disposition: `approve_descriptor_only_local_preview_disposition`.
- Required closure evidence: `can_close_source_rows: true`.
- Required safety evidence: `mutates_findings: false` and `closes_external_review: false`.
- Required finding state: no critical/high findings are open.

## Required Commands

Before a committed descriptor-only disposition record is considered, run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check
make sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake-check
make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-record-check
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-playbook-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
make release-check
make review-candidate
```

## Allowed Future State

If and only if all preconditions are met, this response-application process may support this later
committed state change:

```text
ERG-004 descriptor-only: source_review_pending -> descriptor_only_local_preview_disposition_ready
```

That state change means only that the already implemented operator-attested descriptor-only slice
has favorable descriptor-only source-review evidence for local-preview disposition. It still does
not approve runtime implementation.

## Explicitly Blocked Scope

The response-application process does not approve runtime implementation, live VM/container
inspection, VM/container lifecycle management, sandbox orchestration, Mission Control runtime
behavior, local model invocation, trusted-host promotion, host writes, network expansion, API/MCP
profile loading, SIEM adapter runtime behavior, production identity, runtime Postgres, hosted
telemetry, remote MCP, compliance automation, shell/Docker/Kubernetes/browser governed powers,
arbitrary HTTP, broad filesystem writes, plugin SDK behavior, new governed tool powers, or
public/security-product positioning.

Blocked-boundary labels for release checks: live VM/container inspection, Mission Control runtime behavior, API/MCP profile loading, hosted telemetry.

## Validation

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-record-check
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-playbook-check
make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check
```

# Sandbox/VM Live POC Runtime Descriptor-Only Send Receipt

Status: generated operator send receipt template for the active ERG-004 descriptor-only review.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-send-receipt
```

Validate:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-send-receipt-check
```

The generated receipt is written under:

```text
var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only-send-receipt/
```

## Purpose

This receipt template gives the operator a local, ignored place to record that the active ERG-004
descriptor-only source-review packet was sent. It binds the current commit, prompt path,
source-review packet hash manifest, finding namespace, and raw-response landing pad without
asserting that a reviewer response exists.

The active source-review packet is:

```text
var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-source-review/
```

The active raw-response landing pad is:

```text
var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox/RAW_RESPONSE_ERG-004-DESCRIPTOR-ONLY.md
```

The finding namespace remains `EXT-LIVE-DESC-###`.

## Operator Flow

1. Regenerate current evidence:

   ```sh
   make enterprise-send-now-artifact
   make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle
   make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox
   ```

2. Generate the send receipt scaffold:

   ```sh
   make sandbox-vm-live-poc-runtime-descriptor-only-send-receipt
   ```

3. Send the generated source-review packet to the reviewer.
4. Copy the generated receipt into local operator notes and fill in the send timestamp, channel,
   reviewer label, thread URL or message ID, and operator notes.
5. Wait for a real reviewer response.
6. Paste only the real reviewer response into the ignored raw-response landing pad.
7. Run:

   ```sh
   make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run
   make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check
   ```

Only a later manager-owned disposition update may move ERG-004 away from
`descriptor_only_runtime_implemented_source_review_pending`.

## Boundary

This receipt does not record external review, does not normalize responses, does not write response files,
does not mutate findings, does not close `ERG-004`, does not approve descriptor-only source
disposition, and does not approve runtime implementation.

It also does not approve live VM/container inspection, VM/container lifecycle management, sandbox
orchestration, Mission Control runtime behavior, local model invocation, trusted-host promotion,
host writes, network expansion, API/MCP profile loading, SIEM adapter runtime behavior, production
identity, runtime Postgres, hosted telemetry, remote MCP, compliance automation,
shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem writes, plugin SDK
behavior, new governed tool powers, or public/security-product positioning.

The generated receipt must keep these flags false:

- `records_external_review`
- `normalizes_responses`
- `writes_response_files`
- `closes_erg_004`
- `runtime_changes_allowed`
- `mission_control_runtime_allowed`
- `live_vm_inspection_allowed`
- `sandbox_orchestration_allowed`
- `new_power_classes_allowed`

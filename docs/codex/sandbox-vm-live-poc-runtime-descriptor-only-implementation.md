# Sandbox/VM Live POC Runtime Descriptor-Only Implementation

Status: implemented bounded descriptor-only runtime slice for `ERG-004`.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-implementation-check
```

This checkpoint implements only operator-attested descriptor evidence for sandbox/VM runs. It does
not inspect, start, stop, pause, snapshot, shell into, or verify a VM/container. It does not add MCP
tools, governed tool powers, policy rules, broad writes, Mission Control runtime authority, local
model invocation, trusted-host promotion, host artifact promotion, network expansion, SIEM adapters,
or public/security-product positioning.

## Runtime Surfaces Implemented

The implemented surface is intentionally small:

- closed `SandboxDescriptorPayload` schema validation;
- local SQLite-backed `sandbox_descriptors` record storage;
- admin-protected `POST /sandbox-descriptors`;
- admin-protected `GET /sandbox-descriptors`;
- admin-protected `GET /sandbox-descriptors/{descriptor_id}`;
- `/system/status.sandbox_descriptors` posture evidence;
- safe audit event metadata using `sandbox.descriptor.submitted`;
- focused API tests for accepted descriptors and rejected unsafe descriptors.

The descriptor is an operator-attested record. Ithildin records what the operator supplied and which
authority flags are false; it does not independently verify isolation.

## Preserved Descriptor Facts

Accepted descriptors preserve these facts:

- `descriptor_source: operator_supplied`
- `vm_lifecycle_source: operator_managed`
- `isolation_claim_source: operator_attested`
- `network_posture_source: operator_attested`
- `mount_posture_source: operator_attested`
- `model_client_source: operator_attested`
- `ithildin_live_inspection_performed: false`
- `ithildin_lifecycle_control_performed: false`
- `mission_control_runtime_authority_used: false`
- `trusted_host_promotion_performed: false`

## Safe Output Contract

Descriptor responses and audit metadata may include labels, hashes, timestamps, booleans, status
codes, descriptor IDs, run IDs, workspace IDs, principal IDs, sandbox IDs, profile IDs, and
correlation IDs.

They must not include prompts, model responses, file contents, diffs, transcripts, raw paths,
directory listings, command lines, shell output, environment values, registry URLs, dependency names,
package scripts, or secrets.

Rejected descriptors return a generic `invalid sandbox descriptor` error instead of echoing unsafe
input.

## Rejected Cases

The first implementation covers these fail-closed cases:

- unknown descriptor fields;
- forbidden `ithildin_lifecycle_control_performed: true`;
- raw-path-like mount labels;
- malformed SHA-256 profile/evidence hashes;
- unsupported query parameters;
- malformed descriptor IDs.

Future source-review/negative-transcript work should expand this into a dedicated
`EXT-LIVE-DESC-###` handoff packet.

## Explicit Non-Approvals

This checkpoint does not approve:

- live VM/container inspection;
- VM/container lifecycle management;
- sandbox orchestration;
- Mission Control runtime behavior;
- local model invocation by Ithildin;
- trusted-host promotion;
- host writes or artifact promotion;
- network expansion;
- API/MCP profile loading;
- SIEM adapter runtime behavior;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP;
- compliance automation;
- shell, Docker, Kubernetes, or browser governed powers;
- arbitrary HTTP;
- broad filesystem writes;
- plugin SDK behavior;
- new governed tool powers;
- public/security-product positioning.

## Next Required Milestone

Before stronger claims or expanded ERG-004 behavior, generate a focused source-review handoff packet
for the descriptor-only runtime slice and review the implementation against the `EXT-LIVE-DESC-###`
finding namespace.

## Validation

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-implementation-check
uv run pytest tests/test_api_service.py::test_sandbox_descriptor_endpoints_require_auth_and_store_safe_evidence tests/test_api_service.py::test_sandbox_descriptor_denies_unsafe_inputs_safely -q
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

The normal release gates must still pass. Tool count must remain `24`.

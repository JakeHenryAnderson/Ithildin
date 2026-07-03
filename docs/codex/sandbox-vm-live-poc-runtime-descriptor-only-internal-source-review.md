# Sandbox/VM Live POC Runtime Descriptor-Only Internal Source Review

Status: internal source review completed for the implemented descriptor-only runtime slice.

Current governed tool count: `24`.

Run:

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review-check
```

This review covers the bounded `ERG-004` descriptor-only runtime implementation. It is an internal
source review for continued local-preview development only. It does not close `ERG-004`, does not
replace external/source disposition, and does not approve live VM/container inspection, lifecycle
control, sandbox orchestration, local model invocation, Mission Control runtime authority,
trusted-host promotion, host writes, network expansion, API/MCP profile loading, or new governed
tool powers.

## Files Inspected

- `apps/api/src/ithildin_api/sandbox_descriptors.py`
- `apps/api/src/ithildin_api/app.py`
- `packages/schemas/src/ithildin_schemas/types.py`
- `tests/test_api_service.py`
- `scripts/sandbox_vm_live_poc_runtime_descriptor_only_implementation_check.py`
- `scripts/sandbox_vm_live_poc_runtime_descriptor_only_source_review_bundle.py`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-implementation.md`
- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle.md`

## Claims Reviewed

### Closed Descriptor Schema

Claim tested: descriptor submission accepts only the operator-attested descriptor evidence shape and
rejects unsafe or authority-expanding fields.

Implementation evidence:

- `SandboxDescriptorPayload` uses `StrictBaseModel`, literal source fields, and literal `False`
  authority flags for live inspection, lifecycle control, Mission Control runtime authority, and
  trusted-host promotion.
- Safe label validation rejects path-like labels, `..`, path separators, control characters, and
  oversized labels.
- Hash fields are restricted to `sha256:<64 lowercase hex chars>`.

Test evidence:

- `test_sandbox_descriptor_endpoints_require_auth_and_store_safe_evidence`
- `test_sandbox_descriptor_denies_unsafe_inputs_safely`

Residual risk: descriptor truth still depends on operator attestation; Ithildin does not verify the
actual sandbox/VM state.

### Local Persistence And Safe Summaries

Claim tested: descriptor records are stored locally and returned with secret-free summary/detail
metadata.

Implementation evidence:

- `SandboxDescriptorStore` creates a local `sandbox_descriptors` SQLite table.
- Records use generated `sdesc_` IDs, canonical payload hashes, timestamps, and status `accepted`.
- `summary()` and `detail()` include only labels, hashes, booleans, timestamps, IDs, correlation
  IDs, and output-policy metadata.

Test evidence:

- `test_sandbox_descriptor_endpoints_require_auth_and_store_safe_evidence`

Residual risk: this is local evidence, not notarized custody or independent sandbox verification.

### Admin API Boundary

Claim tested: descriptor submission/list/detail are admin-protected and fail safely.

Implementation evidence:

- `POST /sandbox-descriptors`, `GET /sandbox-descriptors`, and
  `GET /sandbox-descriptors/{descriptor_id}` use `Depends(require_admin_token)`.
- Unsupported list query parameters return `unsupported query parameter`.
- Invalid descriptor IDs return `invalid sandbox descriptor id`.
- Invalid payloads return the generic `invalid sandbox descriptor` detail without echoing unsafe
  input.

Test evidence:

- `test_sandbox_descriptor_endpoints_require_auth_and_store_safe_evidence`
- `test_sandbox_descriptor_denies_unsafe_inputs_safely`

Residual risk: local admin authentication remains a local-preview boundary, not production identity.

### Status And Audit Evidence

Claim tested: status and audit evidence preserve descriptor-only posture without promoting runtime
authority.

Implementation evidence:

- `/system/status.sandbox_descriptors` reports mode
  `operator_attested_descriptor_only`.
- Runtime-control booleans for live VM inspection, lifecycle control, sandbox orchestration,
  Mission Control runtime authority, trusted-host promotion, host writes, and network expansion are
  all `false`.
- `sandbox.descriptor.submitted` audit metadata contains safe descriptor IDs, status, payload hash,
  operator-attested source labels, false authority flags, and output-policy evidence.

Test evidence:

- `test_sandbox_descriptor_endpoints_require_auth_and_store_safe_evidence`

Residual risk: audit events prove what Ithildin recorded, not what happened outside the mediated
gateway.

### Source Review Packet

Claim tested: the implemented descriptor-only runtime slice has a focused source-review handoff.

Implementation evidence:

- `make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle`
- `make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check`
- Finding namespace: `EXT-LIVE-DESC-###`

Residual risk: external/source disposition remains pending.

## Findings

No `INT-LIVE-DESC-###` findings were opened in this pass.

## Disposition

The descriptor-only runtime slice is internally reviewed for continued local-preview development.
This disposition is narrow: it confirms no blocking issue was found in the descriptor-only source
review pass, while preserving the requirement for external/source disposition before treating this
`ERG-004` lane as closed.

## Follow-Up Queue

- External/source reviewer should inspect the descriptor-only source-review bundle using the
  `EXT-LIVE-DESC-###` namespace.
- Any future move beyond descriptor records into VM/container inspection, lifecycle control,
  sandbox orchestration, Mission Control runtime authority, local model invocation, trusted-host
  promotion, host writes, profile loading, network expansion, or new governed tools requires a new
  explicit proposal, implementation gate, tests, and source-review lane.

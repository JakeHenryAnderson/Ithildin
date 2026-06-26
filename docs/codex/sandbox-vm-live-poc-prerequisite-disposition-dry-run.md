# Sandbox/VM Live POC Prerequisite Disposition Dry Run

Status: temporary fixture dry run for the blocked `ERG-004` prerequisite chain.

Current governed tool count: `24`.

Current `ERG-003` status: `external_review_required`.

Current `ERG-004` status: `blocked`.

Validation command:

```sh
make sandbox-vm-live-poc-prerequisite-disposition-dry-run
```

This dry run exercises favorable and unfavorable `ERG-003` static-preflight disposition-record
fixtures before any live sandbox/VM POC planning decision is considered. It does not record external
review, does not close `ERG-003`, does not unblock `ERG-004`, does not write the real normalized
review response path, does not record a post-RC decision record, and does not approve
implementation.

The dry run uses temporary fixture files only. It exists to prove that the `ERG-004` precondition
chain can distinguish a narrow favorable static-preflight disposition from malformed, stale,
unfavorable, or overbroad disposition evidence.

## Cases Exercised

The dry run checks:

- missing static-preflight disposition record is rejected;
- favorable `ERG-003` static-preflight disposition record satisfies only the prerequisite fixture;
- wrong lane is rejected;
- wrong outcome is rejected;
- stale or malformed packet hash is rejected;
- critical/high static-preflight finding is rejected;
- runtime approval language is rejected;
- `ERG-004` unblocking language is rejected;
- live POC planning approval language is rejected.

## Boundaries Preserved

The dry run always reports:

```text
committed_findings_mutated: false
external_review_recorded: false
erg_003_closed: false
erg_004_unblocked: false
decision_record_recorded: false
implementation_planning_allowed: false
runtime_changes_allowed: false
live_vm_inspection_allowed: false
vm_container_lifecycle_management_allowed: false
mission_control_runtime_allowed: false
local_model_invocation_allowed: false
sandbox_orchestration_allowed: false
trusted_host_promotion_allowed: false
network_expansion_allowed: false
api_mcp_profile_loading_allowed: false
siem_adapter_allowed: false
public_security_product_positioning_allowed: false
```

It also keeps production identity, runtime Postgres, hosted telemetry, remote MCP, compliance
automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem
writes, plugin SDK behavior, and new governed tool powers blocked.

## What This Does Not Prove

This is not an external review, source review, live sandbox/VM test, local model invocation,
Mission Control runtime integration, trusted-host promotion approval, implementation approval, or
public/security-product positioning approval. A favorable fixture only proves that the local
precondition logic can recognize the allowed static-preflight disposition-record shape while keeping
`ERG-004` blocked.

Any real movement of `ERG-003` still requires favorable source-level static-preflight review evidence,
the real normalized response path, the real disposition closure gate, and a committed triage update.
Any later movement of `ERG-004` still requires that committed `ERG-003` disposition plus a separate
post-RC live POC decision record. No fixture outcome in this dry run approves live POC planning,
runtime behavior, VM/container lifecycle management, sandbox orchestration, Mission Control runtime
behavior, local model invocation, trusted-host promotion, SIEM adapter behavior, or new governed
tool powers.

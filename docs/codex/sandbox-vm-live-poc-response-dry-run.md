# Sandbox/VM Live POC Response Dry Run

Status: temporary fixture dry run for the blocked `ERG-004` decision closure gate.

Validation command:

```sh
make sandbox-vm-live-poc-response-dry-run
```

This dry run exercises favorable and unfavorable normalized-response fixtures against
`sandbox-vm-live-poc-decision-closure-gate.md` without recording external review, mutating
committed findings, recording a post-RC decision record, or approving implementation. It writes
temporary JSON fixtures to:

```text
var/review-runs/sandbox-vm-live-poc/normalized-response.json
```

The original ignored response path is restored before the command exits.

## Cases Exercised

The dry run checks:

- absent normalized response remains valid but not closure-ready;
- source-level response with `erg_003_favorable_disposition: true` and
  `decision_outcome: approve_limited_operator_managed_poc_planning` can report
  `ready_for_decision_record`;
- missing favorable `ERG-003` disposition is rejected;
- packet-only response is rejected;
- invalid reviewed packet hash is rejected;
- critical/high finding is rejected;
- direct `closes_external_review: true` is rejected.

## Boundaries Preserved

The dry run always reports:

```text
committed_findings_mutated: false
external_review_recorded: false
erg_004_closed: false
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
public/security-product positioning approval. A favorable dry-run fixture only proves that the
local fail-closed closure gate can distinguish acceptable normalized response shapes from
unacceptable ones.

Any real movement of `ERG-004` still requires favorable `ERG-003` disposition evidence and a
separate committed post-RC decision record that cites the reviewed packet hash, cites closure-gate
output, preserves reviewer findings in the normal finding workflow, and keeps runtime work blocked
until a later explicit implementation sprint is approved.

# Sandbox/VM Live POC Runtime Gate Readiness Response Dry Run

Status: temporary fixture dry run for `ERG-004` runtime gate-readiness response intake.

Validation command:

```sh
make sandbox-vm-live-poc-runtime-gate-readiness-response-inbox-check
make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run
```

Before applying any future real response, also validate
[sandbox-vm-live-poc-runtime-gate-readiness-response-application-record.md](sandbox-vm-live-poc-runtime-gate-readiness-response-application-record.md),
[sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook.md](sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook.md),
and
[sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight.md](sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight.md).

This dry run exercises favorable and blocked fixtures for
`sandbox-vm-live-poc-runtime-gate-readiness-response-intake.md` without recording external review,
mutating committed findings, recording a decision record, closing `ERG-004`, or approving runtime
implementation. It writes temporary JSON fixtures to:

```text
var/review-runs/sandbox-vm-live-poc-runtime-gate-readiness/normalized-response.json
```

The original ignored response path is restored before the command exits.

## Cases Exercised

The dry run checks:

- absent normalized response keeps the intake template valid and keeps planning blocked;
- packet-and-source response with no findings and
  `approved_for_descriptor_only_runtime_implementation_planning` can be intaken for later
  decision-record consideration;
- packet-only response is not decision-ready;
- docs-only response is not decision-ready;
- missing allowed outcome is not decision-ready;
- critical/high `EXT-LIVE-GATE-###` finding is not decision-ready;
- invalid reviewed packet hash is rejected;
- wrong finding namespace is rejected;
- secret marker is rejected;
- response without an explicit finding table or no-findings statement is rejected.

## Boundaries Preserved

The dry run always reports:

```text
committed_findings_mutated: false
external_review_recorded: false
erg_004_closed: false
decision_record_recorded: false
descriptor_only_planning_allowed: false
runtime_changes_allowed: false
runtime_implementation_allowed: false
live_vm_inspection_allowed: false
vm_container_lifecycle_allowed: false
sandbox_orchestration_allowed: false
mission_control_runtime_allowed: false
local_model_invocation_allowed: false
trusted_host_promotion_allowed: false
host_writes_allowed: false
network_expansion_allowed: false
api_mcp_profile_loading_allowed: false
siem_adapter_allowed: false
public_security_product_positioning_allowed: false
```

It also keeps production identity, runtime Postgres, hosted telemetry, remote MCP, compliance
automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem
writes, plugin SDK behavior, and new governed tool powers blocked.

## What This Does Not Prove

This is not an external review, source review, live sandbox/VM test, local model invocation, Mission
Control runtime integration, trusted-host promotion approval, descriptor-only planning approval,
implementation approval, or public/security-product positioning approval. A favorable fixture only
proves that the local response-intake shape can distinguish a response that may be considered by a
later decision-record workflow from responses that must remain blocked.

Any real movement of `ERG-004` still requires a saved raw response transcript, normalized response,
reviewed packet hash, no open critical/high `EXT-LIVE-GATE-###` findings, and a separate committed
decision record that preserves runtime implementation as a later explicit implementation sprint.

# Sandbox/VM Live POC Runtime Descriptor-Only Response Dry Run

Status: deterministic dry-run for descriptor-only `ERG-004` source-review response intake.

Current governed tool count: `24`.

Current `ERG-004` descriptor-only status before reviewer disposition:
`descriptor_only_runtime_implemented_source_review_pending`.

This dry-run exercises the descriptor-only external response intake without recording review,
closing `ERG-004`, mutating committed findings, or approving runtime behavior. Use
[sandbox-vm-live-poc-runtime-descriptor-only-response-inbox.md](sandbox-vm-live-poc-runtime-descriptor-only-response-inbox.md)
to capture a real raw response path and reviewed packet hash before normalizing a live reviewer
response. This is a local release gate for the response path only.

## Command

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run
```

Direct JSON form:

```sh
uv run python scripts/sandbox_vm_live_poc_runtime_descriptor_only_response_dry_run.py --json
```

## Covered Cases

The dry-run validates that:

- an absent response keeps the intake valid and does not close `ERG-004`;
- a favorable source-level or packet-and-source response normalizes with `EXT-LIVE-DESC-###`;
- packet-only and docs-only responses cannot become descriptor-only source disposition evidence;
- missing outcome text cannot become disposition-ready evidence;
- critical/high findings block later descriptor-only closure;
- malformed packet hashes are rejected;
- wrong finding namespaces are rejected;
- wrong reviewed areas are rejected;
- secret markers are rejected;
- responses without a finding table or explicit no-findings statement are rejected;
- any pre-existing normalized response file is restored exactly after the dry-run.

## Non-Effects

The dry-run records these invariants in its report:

- `committed_findings_mutated: false`
- `external_review_recorded: false`
- `erg_004_closed: false`
- `descriptor_only_closure_recorded: false`
- `descriptor_only_source_disposition_allowed: false`
- `runtime_changes_allowed: false`
- `runtime_implementation_allowed: false`
- `live_vm_inspection_allowed: false`
- `vm_container_lifecycle_allowed: false`
- `sandbox_orchestration_allowed: false`
- `mission_control_runtime_allowed: false`
- `local_model_invocation_allowed: false`
- `trusted_host_promotion_allowed: false`
- `host_writes_allowed: false`
- `network_expansion_allowed: false`
- `api_mcp_profile_loading_allowed: false`
- `siem_adapter_allowed: false`
- `production_identity_allowed: false`
- `runtime_postgres_allowed: false`
- `hosted_telemetry_allowed: false`
- `remote_mcp_allowed: false`
- `compliance_automation_allowed: false`
- `shell_docker_kubernetes_browser_powers_allowed: false`
- `arbitrary_http_allowed: false`
- `broad_filesystem_writes_allowed: false`
- `plugin_sdk_allowed: false`
- `new_power_classes_allowed: false`
- `public_security_product_positioning_allowed: false`

Only a later committed triage/disposition update may move the descriptor-only slice away from
`descriptor_only_runtime_implemented_source_review_pending`.

## Related Artifacts

- [Sandbox/VM Live POC Runtime Descriptor-Only External Response Intake](sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake.md)
- [Sandbox/VM Live POC Runtime Descriptor-Only Response Application Record](sandbox-vm-live-poc-runtime-descriptor-only-response-application-record.md)
- [Sandbox/VM Live POC Runtime Descriptor-Only Response Application Preflight](sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight.md)
- [Sandbox/VM Live POC Runtime Descriptor-Only Source Review Bundle](sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle.md)

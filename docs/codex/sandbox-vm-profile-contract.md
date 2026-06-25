# Sandbox/VM Profile Contract

Status: design-only profile contract for a future operator-managed sandbox/VM worker proof of
concept.

This contract defines the secret-free profile shape a future sandbox/VM worker demo must provide
before Ithildin or Mission Control may reference sandbox evidence. It does not add runtime behavior,
API endpoints, MCP tools, tool manifests, policy rules, executors, sandbox orchestration,
VM/container lifecycle management, local model invocation, Mission Control runtime behavior,
trusted-host promotion, SIEM adapters, production identity, runtime Postgres, hosted telemetry,
shell, Docker, Kubernetes, browser automation, arbitrary HTTP, broad filesystem writes, compliance
automation, or new governed tool powers.

Validate this contract with:

```sh
make sandbox-vm-profile-contract-check
```

## Relationship To The Boundary Charter

The [Sandbox/VM Worker Boundary Charter](sandbox-vm-worker-boundary-charter.md) says the sandbox
layer is operator-managed infrastructure. This profile contract turns that boundary into the
minimum metadata that later implementation plans must validate before a sandbox/VM worker proof of
concept can be trusted enough to display.

The profile is evidence metadata only. It is not a VM handle, container handle, mount authority,
promotion authority, shell command, local model configuration, or sandbox lifecycle API.

## Required Profile Fields

A future profile must contain these secret-free fields:

| Field | Required meaning |
| --- | --- |
| `schema_version` | Profile schema version, initially `1`. |
| `sandbox_id` | Stable local identifier such as `sandbox_demo_001`; no raw paths or hostnames. |
| `sandbox_label` | Operator-facing display label with no secrets or host paths. |
| `workspace_id` | Ithildin workspace ID the profile is associated with. |
| `trusted_config_source` | Local reviewed source label, not raw file contents. |
| `lifecycle_owner` | `operator`, `mission_control_display_only`, or another future reviewed owner label. |
| `support_status` | `demo_only`, `unsupported`, or `review_required`. |
| `warning_state` | Must include `not_os_isolation_proof`. |
| `working_root_label` | Label such as `sandbox://demo/work`, not a raw filesystem path. |
| `host_staging_root_label` | Label such as `host-staging://demo`, not a raw filesystem path. |
| `approved_output_root_label` | Optional future approved-output label; absent or `not_configured` today. |
| `mount_posture` | Coarse label such as `operator_managed_read_write_working_root`. |
| `network_posture` | Coarse label such as `unknown`, `offline`, or `operator_managed`. |
| `cleanup_posture` | `manual_required`, `operator_confirmed`, or `not_configured`. |
| `evidence_output_label` | Label for where evidence bundles are written, not a raw path. |
| `promotion_status` | Must be `not_promoted` until a separate promotion lane exists. |

## Forbidden Profile Fields

Profiles must not contain:

- credentials, tokens, private keys, or host secrets;
- raw sensitive host paths, home-directory paths, mount internals, or Docker socket paths;
- shell commands, Docker commands, Kubernetes commands, browser automation instructions, or package
  script values;
- environment variable names or values;
- dependency names, registry URLs, prompts, model output, file contents, diffs, response bodies,
  container logs, VM logs, or sandbox internals;
- endpoint URLs for broad network access;
- any flag implying Ithildin starts, stops, repairs, snapshots, or controls the sandbox/VM.

## Required Validation Decisions

A future implementation plan must reject or warn on:

- missing required profile fields;
- unsupported schema version;
- unknown `workspace_id`;
- disabled workspace;
- `support_status: unsupported`;
- missing or hidden `warning_state`;
- missing cleanup posture;
- lifecycle owner claiming Ithildin starts or manages a VM/container;
- raw path-shaped labels where only labels are allowed;
- host-staging or approved-output labels that imply trusted-host promotion is already implemented;
- missing `promotion_status: not_promoted`;
- any profile that grants shell, Docker, Kubernetes, browser, arbitrary network, or broad filesystem
  authority.

## Current Allowed State

Current Ithildin artifacts may include sandbox labels and `promotion_status: not_promoted` as
evidence metadata. They may not load a live sandbox profile, start a VM, call a local model, create
Mission Control runtime behavior, move files to trusted host locations, or claim OS isolation.

## Future Implementation Gate

Any future runtime profile loader or Mission Control importer must receive a separate proposal,
implementation plan, implementation gate, source-review handoff, negative transcripts, and
release/readiness update. Until then, `make sandbox-vm-profile-contract-check` must continue
reporting:

- runtime changes allowed: `false`;
- Mission Control runtime allowed: `false`;
- local model invocation allowed: `false`;
- sandbox orchestration allowed: `false`;
- trusted-host promotion allowed: `false`;
- new power classes allowed: `false`.

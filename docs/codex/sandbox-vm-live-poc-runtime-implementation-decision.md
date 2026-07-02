# Sandbox/VM Live POC Runtime Implementation Decision

Status: planning-only implementation decision for the `ERG-004` descriptor/correlation slice.

Current governed tool count: `24`.

Current `ERG-004` status: `runtime_descriptor_contract_planning`.

Validation:

```sh
make sandbox-vm-live-poc-runtime-descriptor-contract-check
```

This decision allows only the committed descriptor/correlation contract work needed before a later
implementation sprint can be considered. Runtime implementation remains blocked. This decision does
not approve an API endpoint, MCP tool, governed executor, policy rule, UI runtime behavior,
persisted runtime state, VM/container lifecycle control, live VM/container inspection, sandbox
orchestration, Mission Control runtime behavior, local model invocation, trusted-host promotion,
host writes, network expansion, API/MCP profile loading, SIEM adapter runtime behavior, production
identity, runtime Postgres, hosted telemetry, remote MCP, compliance automation, new governed tool
powers, or public/security-product positioning.

## Allowed Planning Scope

This decision allows only these planning artifacts:

- `docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract.md`;
- `docs/codex/sandbox-vm-live-poc-runtime-negative-fixtures.md`;
- a local validation script and Make target that check the planning artifacts;
- release/readiness wiring that proves the documents remain linked and boundary-safe.

The allowed future implementation shape remains descriptor-only:

- accept an operator-supplied descriptor only after a later explicit implementation gate;
- validate closed fields, safe labels, hashes, timestamps, enums, and correlation IDs;
- correlate descriptor values with existing Agent Run, approval, audit, and signed-export evidence;
- emit secret-free status summaries and warning labels;
- reject descriptors that imply forbidden authority or leak raw sensitive content.

## Not Approved

This decision does not approve runtime code. In particular, it does not approve:

- reading live VM/container state;
- starting, stopping, pausing, snapshotting, or shelling into a VM/container;
- invoking a local model;
- commanding Mission Control;
- loading VM profiles through API/MCP;
- moving files between host and VM;
- writing host files or promoting artifacts;
- adding a governed tool, manifest, executor, policy rule, API endpoint, MCP method, UI runtime
  control, or persistent runtime table;
- claiming OS isolation, trusted custody, compliance automation, or production security.

## Future Gate Requirements

A later implementation sprint must still add a separate implementation gate and source-review
handoff before any runtime behavior is added. That future gate must prove:

- descriptor contract and negative fixtures are implemented;
- all forbidden authority attempts fail closed;
- outputs contain safe labels and hashes only;
- Agent Run, approval, audit, and signed-export correlations are checked without reading raw
  sensitive content;
- cleanup and failure transcript evidence is hash-bound and secret-free;
- rollback/removal instructions exist;
- no new governed power class is introduced.

## Stop Conditions

Stop before runtime work if the next slice requires VM lifecycle authority, live inspection, local
model invocation, Mission Control runtime authority, host writes, trusted-host promotion, network
expansion, API/MCP profile loading, new governed powers, or stronger product claims.


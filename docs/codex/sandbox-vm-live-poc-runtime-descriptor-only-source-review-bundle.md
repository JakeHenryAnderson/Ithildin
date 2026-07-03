# Sandbox/VM Live POC Runtime Descriptor-Only Source Review Bundle

Status: checked source-review handoff for the implemented descriptor-only runtime slice.

Current governed tool count: `24`.

This review bundle packages the implemented `ERG-004` descriptor-only runtime records for
source-level review. It is the follow-up to the earlier descriptor-only implementation ticket and
does not replace external or human source review.

## Commands

```sh
make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle
make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check
```

The generated packet is written under:

```text
var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-source-review/
```

## Scope

The packet asks a reviewer to inspect:

- `SandboxDescriptorPayload` validation and safe operator-attested field boundaries;
- `SandboxDescriptorStore` persistence and safe summary/detail behavior;
- admin-only descriptor submit/list/detail endpoints;
- `/system/status` descriptor evidence;
- `sandbox.descriptor.submitted` audit metadata;
- invalid descriptor safe-error behavior;
- tests and gates proving the slice remains descriptor-only.

The packet uses the `EXT-LIVE-DESC-###` finding namespace.

## Boundary

This bundle does not close `ERG-004`, does not approve live VM/container inspection, does not start
or stop VMs/containers, does not inspect a sandbox, does not invoke a local model, does not grant
Mission Control runtime authority, does not promote trusted-host artifacts, does not add MCP tools,
and does not add new governed tool powers.

External/source disposition is still required before this descriptor-only runtime slice can be
treated as closed for the local-preview enterprise lane.

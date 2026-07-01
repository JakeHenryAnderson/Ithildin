# Sandbox/VM Live POC Implementation Review Bundle

Status: checked external-review gate for `ERG-004` implementation planning.

Current governed tool count: `24`.

Current `ERG-004` status: `ready_for_implementation_planning_only`.

Run:

```sh
make sandbox-vm-live-poc-implementation-review-bundle
make sandbox-vm-live-poc-implementation-review-bundle-check
```

Generated output:

```text
var/review-packets/v3/sandbox-vm-live-poc-implementation-review/
```

This bundle packages the VM-first, operator-managed implementation-planning material for external
review. It asks whether the planning surface is complete enough to prepare a later runtime proposal.
It does not approve runtime implementation.

## Review Scope

The bundle includes:

- the `ERG-004` decision record;
- the VM-first implementation plan;
- the active-route clarity note;
- sandbox/VM evidence contracts and precondition maps;
- static fixture, cleanup, and failure transcript planning requirements;
- command evidence and artifact hashes.

## Required External Decision

The reviewer should decide whether `ERG-004` may proceed from implementation-planning-only into a
separate future runtime implementation proposal. A favorable answer still does not authorize runtime
code by itself.

## What This Bundle Does Not Approve

This bundle does not approve runtime implementation, live VM/container inspection, VM/container
lifecycle management, sandbox orchestration, Mission Control runtime behavior, local model
invocation, trusted-host promotion, network expansion, API/MCP profile loading, SIEM adapter
behavior, production identity, runtime Postgres, hosted telemetry, remote MCP, compliance
automation, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem
writes, plugin SDK behavior, new governed tool powers, or public/security-product positioning.

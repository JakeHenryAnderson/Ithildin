# Sandbox/VM Static Preflight Source Review Handoff

Status: source-review handoff only.

This document defines the focused review handoff for the static sandbox/VM profile preflight lane.
The current implementation is CLI-only and fixture-only: Ithildin does not load sandbox profiles
through API/MCP, start VMs or containers, invoke local models, call Mission Control runtime
behavior, promote artifacts to a trusted host, or expose any new governed tool/API/MCP surface.

Generate the focused handoff packet with:

```sh
make sandbox-vm-static-preflight-source-review-packet
```

Validate packet wiring with:

```sh
make sandbox-vm-static-preflight-source-review-packet-check
```

## Review Scope

The packet asks a source reviewer to inspect the static-profile preflight lane before any broader
sandbox/VM integration is planned. The review namespace is `EXT-SANDBOX-PREFLIGHT-###`.

The review surface is:

- `sandbox-vm-static-profile-preflight-plan.md`;
- `sandbox-vm-static-profile-fixture-contract.md`;
- `fixtures/sandbox-vm-static-profile.local-preview.example.json`;
- `sandbox-vm-static-profile-negative-fixtures.md`;
- the existing sandbox/VM worker, profile, and preflight contracts;
- the enterprise-readiness runway pointers;
- command evidence for the existing design/fixture gates and no-new-powers gates.

## Required Reviewer Question

The reviewer should answer whether the CLI-only, fixture-only static profile preflight runner stays
within the approved boundary and whether broader sandbox/VM planning may proceed. A positive answer
is not approval to implement live sandbox control.

## Explicit Non-Goals

This packet does not prove OS isolation, live sandbox validation, local model safety, Mission
Control execution behavior, VM/container lifecycle safety, Docker/Kubernetes safety, SIEM custody,
compliance automation, production security, or public/security-product readiness.

It also does not authorize:

- new governed tools;
- new MCP/API behavior;
- runtime profile loading;
- shell execution;
- Docker socket access;
- Kubernetes control;
- browser automation;
- arbitrary HTTP;
- broad filesystem writes;
- local model invocation;
- trusted-host promotion;
- sandbox orchestration;
- Mission Control runtime authority;
- production identity;
- runtime Postgres;
- hosted telemetry;
- remote MCP hosting;
- plugin SDK behavior.

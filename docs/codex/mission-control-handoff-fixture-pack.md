# Mission Control Handoff Fixture Pack

Status: generated fixture pack for Mission Control display/import tests.

This document defines the Ithildin-side fixture pack for future Mission Control importer tests. It
is display/import fixtures only. It does not add Mission Control runtime behavior, callbacks into
Ithildin, API polling, MCP behavior, approvals, audit authority transfer, local model invocation,
VM/container lifecycle management, sandbox orchestration, trusted-host promotion, SIEM adapters,
production identity, runtime Postgres, hosted telemetry, shell, Docker/Kubernetes/browser governed
powers, arbitrary HTTP, broad filesystem writes, compliance automation, or public/security-product
claims.

Generate the fixture pack with:

```sh
make mission-control-handoff-fixture-pack
make mission-control-handoff-fixture-pack-check
make mission-control-importer-acceptance-matrix-check
```

Generated output:

```text
var/review-packets/v3/mission-control-handoff-fixtures/
```

## Purpose

The fixture pack gives the future Mission Control display/import implementation a concrete test set
without requiring Mission Control to call Ithildin, run an agent, start services, or mutate gateway
state.

The importer acceptance matrix in
[mission-control-importer-acceptance-matrix.md](mission-control-importer-acceptance-matrix.md)
maps each generated fixture to the expected display/import state, warning labels, safe rejection
reasons, and forbidden fields for the future Mission Control-side tests.

The pack contains:

- one valid metadata-only handoff payload;
- fourteen negative handoff payloads matching the existing `MC-HANDOFF-NEG-###` cases;
- stable expected safe reason labels for each negative case;
- a machine-readable fixture summary;
- artifact hashes for handoff integrity.

## Fixture Families

The positive fixture must be accepted only as metadata-only evidence.

The negative fixtures must be rejected or kept in a warning-only state:

- `MC-HANDOFF-NEG-001` through `MC-HANDOFF-NEG-014`;
- unsupported schema;
- live-status or authority overclaims;
- missing display contract, warning chips, or hidden-field denylist;
- unsafe attachment paths;
- raw file content or prompt leakage.

## Safe Error Requirements

Mission Control should report stable reason labels only. It must not echo raw prompts, file
contents, raw host paths, environment values, tokens, private keys, response bodies, dependency
names, package script values, or sandbox internals.

## Boundary

This fixture pack does not approve runtime importer behavior. It is evidence for a later
Mission Control-side implementation task and source-review handoff. It does not close `ERG-002`,
does not approve Mission Control execution, and does not approve callbacks into Ithildin.

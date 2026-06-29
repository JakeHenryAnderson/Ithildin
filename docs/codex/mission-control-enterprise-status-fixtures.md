# Mission Control Enterprise Status Fixtures

Status: generated fixture pack for Mission Control enterprise status display/import tests.

This document defines the Ithildin-side fixture pack for the future Mission Control display-only
importer of the [Enterprise Status Export](enterprise-status-export.md). It is display/import fixtures only. It does not add Mission Control runtime behavior, callbacks into Ithildin, API
polling, MCP behavior, approvals, audit authority transfer, local model invocation, VM/container
lifecycle management, sandbox orchestration, trusted-host promotion, SIEM adapters, production
identity, runtime Postgres, hosted telemetry, shell, Docker/Kubernetes/browser governed powers,
arbitrary HTTP, broad filesystem writes, compliance automation, or public/security-product claims.

Generate the fixture pack with:

```sh
make mission-control-enterprise-status-fixtures
make mission-control-enterprise-status-fixtures-check
make mission-control-enterprise-status-import-check
make mission-control-enterprise-status-acceptance-matrix-check
make mission-control-enterprise-status-reference-validator
```

Generated output:

```text
var/review-packets/v3/mission-control-enterprise-status-fixtures/
```

## Purpose

The fixture pack gives the future Mission Control enterprise status importer a concrete local test
set without requiring Mission Control to call Ithildin, run an agent, start services, or mutate
gateway state.

The [Mission Control Enterprise Status Import Contract](mission-control-enterprise-status-import-contract.md)
defines the allowed display fields and boundary rules for these fixtures. The pack turns that
contract into one valid JSON payload and negative payloads that must be rejected with safe reason
labels.

The [Mission Control Enterprise Status Acceptance Matrix](mission-control-enterprise-status-acceptance-matrix.md)
maps the fixture pack to future display-only importer states, warning labels, safe rejection
reasons, and forbidden displays.

The [Mission Control Enterprise Status Reference Validator](mission-control-enterprise-status-reference-validator.md)
validates the generated fixture pack as an Ithildin-side display-only oracle for future Mission
Control importer tests.

The pack contains:

- one valid display-only enterprise status export payload;
- twelve negative enterprise status payloads matching the `MC-STATUS-NEG-###` cases;
- stable expected safe reason labels for each negative case;
- a machine-readable fixture summary;
- artifact hashes for handoff integrity.

## Fixture Families

The positive fixture must be accepted only as non-authoritative display status.

The negative fixtures must be rejected or quarantined:

- `MC-STATUS-NEG-001` through `MC-STATUS-NEG-012`;
- unsupported schema or artifact type;
- non-display status claims;
- Mission Control runtime or authority overclaims;
- runtime/new-power/public-positioning flags set to true;
- lane closure claims without normalized external responses;
- raw prompt or file-content leakage.
- unsafe action commands outside the checked Ithildin operator refresh helpers;
- unsafe handoff artifact paths outside ignored review artifact roots.

The final two fixtures are explicit handoff-safety cases: `MC-STATUS-NEG-011` rejects unsafe
action commands with `unsupported_action_command`, and `MC-STATUS-NEG-012` rejects unsafe handoff
artifact paths with `unsafe_handoff_artifact`.

## Safe Error Requirements

Mission Control should report stable reason labels only. It must not echo raw prompts, file
contents, raw host paths, environment values, tokens, private keys, response bodies, dependency
names, package script values, arbitrary JSON subtrees, or sandbox internals.

## Boundary

This fixture pack does not approve Mission Control enterprise status importer implementation. It is
evidence for a later Mission Control-side display-only implementation task and source-review
handoff. It does not close `ERG-002`, does not approve Mission Control execution, does not approve
runtime importer behavior, and does not approve callbacks into Ithildin.

# Mission Control Enterprise Status Acceptance Matrix

Status: acceptance matrix for future Mission Control enterprise status display/import tests.

This document maps the Ithildin-generated enterprise status fixture pack to the expected behavior
of a future Mission Control display-only importer. It is test and review guidance only. It does not
add Mission Control runtime behavior, callbacks into Ithildin, API polling, MCP behavior, approvals,
audit authority transfer, local model invocation, live VM/container inspection, sandbox
orchestration, trusted-host promotion, SIEM adapters, production identity, runtime Postgres, hosted
telemetry, shell, Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem
writes, compliance automation, or public/security-product claims.

Validate this matrix with:

```sh
make mission-control-enterprise-status-acceptance-matrix-check
```

Generate the referenced fixture pack first with:

```sh
make mission-control-enterprise-status-fixtures
```

Generated fixture output:

```text
var/review-packets/v3/mission-control-enterprise-status-fixtures/
```

## Purpose

The future Mission Control importer should be able to consume the enterprise status fixture pack as
local files and decide whether each payload can be displayed as non-authoritative dashboard status.
Ithildin remains the execution, policy, approval, audit, review-lane closure, and runtime authority.
Mission Control may display status labels, short hashes, warning chips, safe reason labels, packet
paths, and artifact pointers; it must not execute work, invoke models, call Ithildin APIs, close
enterprise lanes, or promote artifacts.

The [Mission Control Enterprise Status Fixtures](mission-control-enterprise-status-fixtures.md)
document and generator provide the current Ithildin-side oracle for these expected accept/reject
results. They are useful for Mission Control tests, but they are not a runtime importer and do not
approve callbacks into Ithildin.

## Importer Display Contract

Accepted fixtures may display only:

- schema, artifact, status, and fixture labels;
- tool count, recommended review lane labels, response counts, and closure readiness labels;
- safe warning chips showing blocked runtime authority;
- artifact hash and byte-count metadata;
- packet-relative artifact pointers from the generated fixture pack;
- boundary flags showing runtime authority remains blocked.

Rejected fixtures should display stable reason labels only. They must not echo raw prompts, file
contents, raw host paths, environment values, tokens, private keys, response bodies, dependency
names, package script values, sandbox internals, raw stack traces, arbitrary JSON subtrees, or
compliance conclusions.

## Acceptance Matrix

| Fixture ID | Fixture path | Expected importer state | Required visible labels | Forbidden display |
| --- | --- | --- | --- | --- |
| `MC-STATUS-VALID-001` | `valid/enterprise-status-valid.json` | `accepted_display_only_status` | `display_only`, `ithildin_remains_authority`, `mission_control_runtime_blocked`, `new_power_classes_blocked` | raw prompts, file contents, raw host paths, tokens, private keys, environment values, response bodies |
| `MC-STATUS-NEG-001` | `negatives/MC-STATUS-NEG-001-missing_schema_version.json` | `rejected_safe_reason` | `unsupported_schema_version` | raw payload echo, raw stack traces |
| `MC-STATUS-NEG-002` | `negatives/MC-STATUS-NEG-002-unsupported_schema_version.json` | `rejected_safe_reason` | `unsupported_schema_version` | raw payload echo, raw stack traces |
| `MC-STATUS-NEG-003` | `negatives/MC-STATUS-NEG-003-wrong_artifact_type.json` | `rejected_safe_reason` | `unsupported_artifact_type` | unsupported artifact rendering as trusted status |
| `MC-STATUS-NEG-004` | `negatives/MC-STATUS-NEG-004-non_display_status.json` | `rejected_safe_reason` | `status_must_be_display_only` | runtime control affordances |
| `MC-STATUS-NEG-005` | `negatives/MC-STATUS-NEG-005-mission_control_runtime_true.json` | `rejected_safe_reason` | `mission_control_runtime_allowed_must_be_false` | Mission Control execution controls |
| `MC-STATUS-NEG-006` | `negatives/MC-STATUS-NEG-006-sandbox_orchestration_true.json` | `rejected_safe_reason` | `sandbox_orchestration_allowed_must_be_false` | sandbox orchestration controls |
| `MC-STATUS-NEG-007` | `negatives/MC-STATUS-NEG-007-new_power_classes_true.json` | `rejected_safe_reason` | `new_power_classes_allowed_must_be_false` | capability expansion controls |
| `MC-STATUS-NEG-008` | `negatives/MC-STATUS-NEG-008-closure_without_response.json` | `rejected_safe_reason` | `closure_claim_requires_normalized_response` | lane closure controls |
| `MC-STATUS-NEG-009` | `negatives/MC-STATUS-NEG-009-raw_prompt.json` | `rejected_safe_reason` | `forbidden_payload_field` | raw prompts |
| `MC-STATUS-NEG-010` | `negatives/MC-STATUS-NEG-010-raw_file_contents.json` | `rejected_safe_reason` | `forbidden_payload_field` | file contents |

## Mission Control Test Expectations

Future Mission Control importer tests should cover:

- accepting `MC-STATUS-VALID-001` as display-only status evidence;
- rejecting all `MC-STATUS-NEG-001` through `MC-STATUS-NEG-010` fixtures with safe reason labels;
- showing warning chips for local-preview, display-only, Mission Control runtime blocked, no local
  model invocation, no live VM/container inspection, no sandbox orchestration, no trusted-host
  promotion, no SIEM adapter, no compliance automation, and no public/security-product
  positioning;
- hiding all fields in the forbidden payload denylist;
- preserving artifact hashes and byte counts without opening attachments;
- never calling Ithildin, starting services, invoking a model, inspecting a live VM, writing host
  files, or closing review lanes as part of fixture import.

Use `make mission-control-enterprise-status-reference-validator` to validate that the generated
fixture pack and expected safe reason labels form a stable display-only oracle for future Mission
Control importer tests.

## Boundary

This matrix does not approve Mission Control importer implementation. It makes a future
Mission Control-side task easier to test and review while keeping `ERG-002` planning-only and
keeping Ithildin as the sole execution, policy, approval, audit, review-lane closure, and runtime
authority.

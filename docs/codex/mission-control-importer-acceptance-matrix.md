# Mission Control Importer Acceptance Matrix

Status: acceptance matrix for future Mission Control display/import tests.

This document maps the Ithildin-side Mission Control handoff fixture pack to the expected behavior
of a future Mission Control display-only importer. It is test and review guidance only. It does not
add Mission Control runtime behavior, callbacks into Ithildin, API polling, MCP behavior, approvals,
audit authority transfer, local model invocation, VM/container lifecycle management, sandbox
orchestration, trusted-host promotion, SIEM adapters, production identity, runtime Postgres, hosted
telemetry, shell, Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad filesystem
writes, compliance automation, or public/security-product claims.

Validate this matrix with:

```sh
make mission-control-importer-acceptance-matrix-check
```

Generate the referenced fixture pack first with:

```sh
make mission-control-handoff-fixture-pack
```

Generated fixture output:

```text
var/review-packets/v3/mission-control-handoff-fixtures/
```

## Purpose

The future Mission Control importer should be able to consume the fixture pack as local files and
decide whether each payload can be displayed as metadata-only evidence. Ithildin remains the
execution, policy, approval, and audit authority. Mission Control may display labels, hashes,
warning chips, safe reason labels, and artifact pointers; it must not execute work, invoke models,
call Ithildin APIs, close review lanes, or promote artifacts.

## Importer Display Contract

Accepted fixtures may display only:

- schema and fixture status labels;
- run, workspace, artifact, approval, audit, and packet identifiers;
- safe warning chips;
- artifact hash and byte-count metadata;
- boundary flags showing runtime authority remains blocked;
- relative attachment pointers already present in the handoff payload.

Rejected fixtures should display stable reason labels only. They must not echo raw prompts, file
contents, raw host paths, environment values, tokens, private keys, response bodies, dependency
names, package script values, sandbox internals, raw stack traces, or arbitrary JSON subtrees.

## Acceptance Matrix

| Fixture ID | Fixture path | Expected importer state | Required visible labels | Forbidden display |
| --- | --- | --- | --- | --- |
| `MC-HANDOFF-VALID-001` | `valid/mission-control-handoff-valid.json` | `accepted_metadata_only` | `local_preview_only`, `mission_control_metadata_only`, `ithildin_remains_authority`, `host_promotion_not_performed` | raw prompts, file contents, raw host paths, tokens, private keys, environment values, response bodies |
| `MC-HANDOFF-NEG-001` | `negatives/MC-HANDOFF-NEG-001-missing_schema_version.json` | `rejected_safe_reason` | `missing_schema_version` | raw payload echo, raw stack traces |
| `MC-HANDOFF-NEG-002` | `negatives/MC-HANDOFF-NEG-002-unsupported_schema_version.json` | `rejected_safe_reason` | `unsupported_schema_version` | raw payload echo, raw stack traces |
| `MC-HANDOFF-NEG-003` | `negatives/MC-HANDOFF-NEG-003-live_status_claim.json` | `rejected_safe_reason` | `status_must_be_metadata_only` | live-control affordances, callbacks into Ithildin |
| `MC-HANDOFF-NEG-004` | `negatives/MC-HANDOFF-NEG-004-mission_control_runtime_true.json` | `rejected_safe_reason` | `runtime_behavior_must_be_false` | Mission Control execution controls |
| `MC-HANDOFF-NEG-005` | `negatives/MC-HANDOFF-NEG-005-host_promotion_true.json` | `rejected_safe_reason` | `host_promotion_must_be_false` | host promotion controls |
| `MC-HANDOFF-NEG-006` | `negatives/MC-HANDOFF-NEG-006-policy_authority_false.json` | `rejected_safe_reason` | `ithildin_policy_authority_required` | Mission Control policy/approval authority |
| `MC-HANDOFF-NEG-007` | `negatives/MC-HANDOFF-NEG-007-absolute_attachment_path.json` | `rejected_safe_reason` | `attachment_path_must_be_relative` | absolute host paths |
| `MC-HANDOFF-NEG-008` | `negatives/MC-HANDOFF-NEG-008-parent_attachment_path.json` | `rejected_safe_reason` | `attachment_path_must_not_escape` | parent-directory traversal paths |
| `MC-HANDOFF-NEG-009` | `negatives/MC-HANDOFF-NEG-009-missing_display_contract.json` | `rejected_safe_reason` | `display_contract_required` | implicit display allowlists |
| `MC-HANDOFF-NEG-010` | `negatives/MC-HANDOFF-NEG-010-missing_token_hide_field.json` | `rejected_safe_reason` | `hidden_field_denylist_incomplete` | tokens or hidden sensitive fields |
| `MC-HANDOFF-NEG-011` | `negatives/MC-HANDOFF-NEG-011-missing_host_promotion_warning.json` | `rejected_safe_reason` | `warning_chips_incomplete` | missing boundary warnings |
| `MC-HANDOFF-NEG-012` | `negatives/MC-HANDOFF-NEG-012-executor_authority_claim.json` | `rejected_safe_reason` | `mission_control_authority_invalid` | executor, policy, approval, or audit authority transfer |
| `MC-HANDOFF-NEG-013` | `negatives/MC-HANDOFF-NEG-013-raw_file_contents.json` | `rejected_safe_reason` | `forbidden_payload_key:file_contents` | file contents |
| `MC-HANDOFF-NEG-014` | `negatives/MC-HANDOFF-NEG-014-raw_prompt.json` | `rejected_safe_reason` | `forbidden_payload_key:raw_prompt` | raw prompts |

## Mission Control Test Expectations

Future Mission Control importer tests should cover:

- accepting `MC-HANDOFF-VALID-001` as metadata-only display evidence;
- rejecting all `MC-HANDOFF-NEG-001` through `MC-HANDOFF-NEG-014` fixtures with safe reason labels;
- showing warning chips for local-preview, metadata-only, no local-model invocation, no VM start, and
  no host promotion;
- hiding all fields in the display contract denylist;
- preserving artifact hashes and byte counts without opening attachments;
- never calling Ithildin, starting services, invoking a model, writing host files, or closing review
  lanes as part of fixture import.

## Boundary

This matrix does not approve Mission Control importer implementation. It makes a future
Mission Control-side task easier to test and review while keeping `ERG-002` planning-only and
keeping Ithildin as the sole execution, policy, approval, and audit authority.

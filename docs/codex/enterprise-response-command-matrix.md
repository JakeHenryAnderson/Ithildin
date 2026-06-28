# Enterprise Response Command Matrix

Status: checked command matrix for applying enterprise external-review responses.

Current governed tool count: `24`.

Current selected capability: `not selected`.

Run:

```sh
make enterprise-response-command-matrix
```

This matrix is the committed operator map for what to run after real reviewer text arrives. It
complements the generated [Enterprise Response Inbox](enterprise-response-inbox.md), the checked
[Enterprise Response Application Protocol](enterprise-response-application-protocol.md), and the
[Enterprise Transition Map](enterprise-transition-map.md).
For the current `ERG-003` and `ERG-002` receive path, the compact operator quickstart is checked
with `make enterprise-response-intake-quickstart`.

This matrix does not normalize responses, does not write normalized response files, does not mutate findings, does not record external review, does not close any enterprise lane, and does not approve runtime behavior.

Use the generated inbox for exact reviewed-packet hashes before applying a real response:

```sh
make enterprise-response-inbox
```

For `ERG-003`, use
[Sandbox/VM Static Preflight Response Application Preflight](sandbox-vm-static-preflight-response-application-preflight.md)
before applying a real reviewer response. It verifies the raw-response path, normalized-response
path, command matrix row, closure gate, dry-run, application record, application playbook, and
blocked runtime boundaries without normalizing responses or closing the lane.

For `ERG-002`, use
[Mission Control Display Response Application Preflight](mission-control-display-response-application-preflight.md)
before using a real reviewer response to support a design-only decision record. It verifies the
raw-response path, normalized-response path, command matrix row, closure gate, dry-run, response kit,
decision-record skeleton, and blocked Mission Control runtime boundaries without normalizing
responses or closing the lane.

## Command Matrix

| Lane | Raw response path | Normalizer command | Normalized response path | Dry run | Closure gate | Response kit | Maximum allowed transition | Still blocked |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ERG-003` | `var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-003.md` | `uv run python scripts/external_response_normalize.py var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-003.md --reviewer "REVIEWER NAME" --reviewer-type "ai_external" --source-access source-level --reviewed-commit "$(git rev-parse HEAD)" --reviewed-packet-hash "sha256:<from generated inbox>" --area sandbox-vm-static-preflight --output var/review-runs/sandbox-vm-static-preflight/normalized-response.json` | `var/review-runs/sandbox-vm-static-preflight/normalized-response.json` | `make sandbox-vm-static-preflight-response-dry-run` | `make sandbox-vm-static-preflight-disposition-closure-check` | `var/review-packets/v3/sandbox-vm-static-preflight-response-kit` | `closed_local_preview_static_preflight` | live VM/container inspection, lifecycle management, local model invocation, sandbox orchestration |
| `ERG-002` | `var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-002.md` | `uv run python scripts/external_response_normalize.py var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-002.md --reviewer "REVIEWER NAME" --reviewer-type "ai_external" --source-access source-level --reviewed-commit "$(git rev-parse HEAD)" --reviewed-packet-hash "sha256:<from generated inbox>" --area mission-control-display --output var/review-runs/mission-control-display/normalized-response.json` | `var/review-runs/mission-control-display/normalized-response.json` | `make mission-control-display-response-dry-run` | `make mission-control-display-disposition-closure-check` | `var/review-packets/v3/mission-control-display-response-kit` | `ready_for_design_only_decision_record` | Mission Control runtime importer behavior, execution authority, polling or mutating APIs |
| `ERG-005` | `var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-005.md` | `uv run python scripts/external_response_normalize.py var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-005.md --reviewer "REVIEWER NAME" --reviewer-type "ai_external" --source-access source-level --reviewed-commit "$(git rev-parse HEAD)" --reviewed-packet-hash "sha256:<from generated inbox>" --area trusted-host-promotion --output var/review-runs/trusted-host-promotion/normalized-response.json` | `var/review-runs/trusted-host-promotion/normalized-response.json` | `make trusted-host-promotion-response-dry-run` | `make trusted-host-promotion-disposition-closure-check` | `var/review-packets/v3/trusted-host-promotion-response-kit` | `ready_for_design_only_decision_record` | direct host writes, overwrite/delete/move behavior, automatic promotion |
| `ERG-006-ERG-007` | `var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-006-ERG-007.md` | `uv run python scripts/external_response_normalize.py var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-006-ERG-007.md --reviewer "REVIEWER NAME" --reviewer-type "ai_external" --source-access source-level --reviewed-commit "$(git rev-parse HEAD)" --reviewed-packet-hash "sha256:<from generated inbox>" --area production-identity-storage --output var/review-runs/production-identity-storage/normalized-response.json` | `var/review-runs/production-identity-storage/normalized-response.json` | `make production-identity-storage-response-dry-run` | `make production-identity-storage-disposition-closure-check` | `var/review-packets/v3/production-identity-storage-response-kit` | `architecture_continuation_only` | production identity, enterprise RBAC, runtime Postgres, migrations, retention enforcement |
| `ERG-008` | `var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-008.md` | `uv run python scripts/external_response_normalize.py var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-008.md --reviewer "REVIEWER NAME" --reviewer-type "ai_external" --source-access source-level --reviewed-commit "$(git rev-parse HEAD)" --reviewed-packet-hash "sha256:<from generated inbox>" --area siem-export-adapter --output var/review-runs/siem-export-adapter/normalized-response.json` | `var/review-runs/siem-export-adapter/normalized-response.json` | `make siem-export-adapter-response-dry-run` | `make siem-export-adapter-disposition-closure-check` | `var/review-packets/v3/siem-export-adapter-response-kit` | `architecture_continuation_only` | SIEM adapter runtime behavior, hosted telemetry, remote delivery, custody-grade audit claims |
| `ERG-009` | `var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-009.md` | `uv run python scripts/external_response_normalize.py var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-009.md --reviewer "REVIEWER NAME" --reviewer-type "ai_external" --source-access source-level --reviewed-commit "$(git rev-parse HEAD)" --reviewed-packet-hash "sha256:<from generated inbox>" --area compliance-mapping --output var/review-runs/compliance-mapping/normalized-response.json` | `var/review-runs/compliance-mapping/normalized-response.json` | `make compliance-mapping-response-dry-run` | `make compliance-mapping-disposition-closure-check` | `var/review-packets/v3/compliance-mapping-response-kit` | `architecture_continuation_only` | compliance automation, legal conclusions, certification claims, regulated-industry compliance claims |
| `ERG-004` | `var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-004.md` | `uv run python scripts/external_response_normalize.py var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-004.md --reviewer "REVIEWER NAME" --reviewer-type "ai_external" --source-access source-level --reviewed-commit "$(git rev-parse HEAD)" --reviewed-packet-hash "sha256:<from generated inbox>" --area sandbox-vm-live-poc --output var/review-runs/sandbox-vm-live-poc/normalized-response.json` | `var/review-runs/sandbox-vm-live-poc/normalized-response.json` | `make sandbox-vm-live-poc-response-dry-run` | `make sandbox-vm-live-poc-decision-closure-check` | `var/review-packets/v3/sandbox-vm-live-poc-response-kit` | `ready_for_decision_record` | live implementation until ERG-003 and an ERG-004 decision record explicitly approve it |
| `ERG-010` | `var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-010.md` | `uv run python scripts/external_response_normalize.py var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-010.md --reviewer "REVIEWER NAME" --reviewer-type "ai_external" --source-access source-level --reviewed-commit "$(git rev-parse HEAD)" --reviewed-packet-hash "sha256:<from generated inbox>" --area public-security-product-positioning --output var/review-runs/public-security-product-positioning/normalized-response.json` | `var/review-runs/public-security-product-positioning/normalized-response.json` | `none` | `make public-security-product-positioning-decision-closure-check` | `var/review-packets/v3/public-security-product-positioning-response-kit` | `positioning_decision_record_only` | public/security-product positioning unless a later decision explicitly narrows and approves claims |

## Boundary Flags

- normalizes_responses: `false`
- writes_response_files: `false`
- committed_findings_mutated: `false`
- external_review_recorded: `false`
- closes_enterprise_lanes: `false`
- runtime_changes_allowed: `false`
- mission_control_runtime_allowed: `false`
- live_vm_inspection_allowed: `false`
- local_model_invocation_allowed: `false`
- sandbox_orchestration_allowed: `false`
- trusted_host_promotion_allowed: `false`
- siem_adapter_runtime_allowed: `false`
- compliance_automation_allowed: `false`
- public_security_product_positioning_allowed: `false`
- new_power_classes_allowed: `false`

## Use Order

1. Generate or refresh the all-lane inbox with `make enterprise-response-inbox`.
2. Paste the real reviewer response into the matching raw-response placeholder.
3. Run the lane's normalizer command from the generated inbox so the reviewed packet hash is exact.
4. Run the lane dry-run command when present.
5. Run the lane closure gate.
6. Commit a later triage or decision-record update only if the closure gate proves the response is
   favorable and the allowed transition in this matrix permits the next state.

Do not manually promote a lane from this matrix alone. The matrix is an operator command map, not
review evidence and not a closure artifact.

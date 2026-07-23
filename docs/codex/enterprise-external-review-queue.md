# Enterprise External Review Queue

Status: planning-only queue for post-RC enterprise review lanes.

Current governed tool count: `24`.

Current selected capability: `not selected`.

This queue turns the enterprise gap matrix and post-RC decision register into an operator-readable
review sequence. It does not approve runtime behavior, tool manifests, executors, policy rules,
API/MCP behavior, Mission Control runtime behavior, sandbox orchestration, trusted-host promotion,
local model invocation, SIEM adapters, compliance automation, production identity, runtime Postgres,
hosted telemetry, remote MCP, plugin SDK behavior, arbitrary HTTP expansion, broad filesystem
writes, or public/security-product positioning.

Validate this queue with:

```sh
make enterprise-external-review-queue-check
```

Validate that every queued response lane is supported by the shared response normalizer with:

```sh
make enterprise-response-normalization-coverage
```

Create ignored raw-response placeholders and exact normalization commands for all queued response
lanes with:

```sh
make enterprise-response-inbox
```

Exercise every response-intake path with temporary fixtures before a real response arrives with:

```sh
make enterprise-response-intake-drill
```

## Queue Rules

- Every row must point to an existing evidence packet or intake document.
- A lane may be reviewed, but review does not approve implementation unless a later committed
  decision record explicitly says so.
- Favorable review feedback is intake evidence only until normalized, dispositioned, and reflected
  in the post-RC decision register.
- Critical/high findings keep the lane blocked.
- A lane that depends on another lane cannot move forward until the prerequisite row is
  dispositioned.
- public/security-product positioning remains a no-go lane until its exact claim evidence is
  independently reviewed and explicitly approved by a later decision record.

## Active Route Versus Historical Queue

The post-disposition active route is now the external target and signed-receipt input wait recorded
by the reviewed PIS-003 environment-evidence authority. The bounded `ERG-005`
runtime source findings are
dispositioned, but ERG-005 and broader trusted-host promotion remain blocked. The historical
`ERG-004` descriptor-only and `ERG-003`/`ERG-002` routes remain below for provenance,
response-intake fallback, and dependency traceability. They are not the current operator next
action while `make enterprise-operator-next-action` reports
`await_external_operator_target_and_signed_receipt_inputs_before_separate_collection_action_authority`.

Current active route: external target and signed-receipt input wait; no review send is active.

Current active route validation:

```sh
make enterprise-active-route-clarity
make production-identity-storage-pis-001-internal-review-check
make production-identity-storage-pis-001-decision-check
make no-new-powers-guardrail
make tool-surface-invariant-gate
```

This active route still does not approve runtime implementation, production identity, enterprise
RBAC, remote administration, runtime Postgres, migrations, live VM/container inspection,
VM/container lifecycle management, sandbox orchestration, Mission Control runtime behavior, local
model invocation, trusted-host promotion, host writes, network expansion, API/MCP profile loading,
SIEM adapter behavior, public/security-product positioning, or new governed tool powers.

## Historical Review Queue

| Order | Gap / PRD | Status before review | Primary packet or doc | Intake / response path | Allowed next action | Runtime allowed |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `ERG-003` / `PRD-SANDBOX-PREFLIGHT-001` | `external_review_required` | `sandbox-vm-static-preflight-external-review-bundle.md` plus `sandbox-vm-static-preflight-disposition-packet.md` | `sandbox-vm-static-preflight-response-kit.md`, `sandbox-vm-static-preflight-external-response-intake.md`, `sandbox-vm-static-preflight-disposition-closure-gate.md`, `sandbox-vm-static-preflight-response-dry-run.md`, `sandbox-vm-static-preflight-triage-update.md`, `sandbox-vm-static-preflight-response-application-playbook.md`, and `sandbox-vm-static-preflight-response-application-record.md` | External/source review disposition of static preflight fixture evidence | `false` |
| 2 | `ERG-002` / `PRD-MC-DISPLAY-001` | `planning_only` | `mission-control-display-external-review-bundle.md` plus `mission-control-integration-readiness-packet.md` | `mission-control-display-response-kit.md`, `mission-control-display-external-response-intake.md`, `mission-control-display-disposition-closure-gate.md`, and `mission-control-display-response-dry-run.md` | Mission Control-side display/importer planning review only | `false` |
| 3 | `ERG-005` / `PRD-TRUSTED-HOST-001` | `blocked` | `trusted-host-promotion-external-review-bundle.md` plus `trusted-host-promotion-disposition-packet.md` | `trusted-host-promotion-response-kit.md`, `trusted-host-promotion-external-response-intake.md`, `trusted-host-promotion-disposition-closure-gate.md`, and `trusted-host-promotion-response-dry-run.md` | Review of design-only promotion evidence and negative fixtures | `false` |
| 4 | `ERG-006` + `ERG-007` / `PRD-PROD-IAM-STORAGE-001` | `planning_only` | `production-identity-storage-external-review-bundle.md` plus `production-identity-storage-disposition-packet.md` | `production-identity-storage-response-kit.md`, `production-identity-storage-external-response-intake.md`, `production-identity-storage-disposition-closure-gate.md`, and `production-identity-storage-response-dry-run.md` | Architecture review for identity, tenancy, storage, retention, and custody boundaries | `false` |
| 5 | `ERG-008` / `PRD-SIEM-EXPORT-001` | `planning_only` | `siem-export-adapter-external-review-bundle.md` plus `siem-export-adapter-disposition-packet.md` | `siem-export-adapter-response-kit.md`, `siem-export-adapter-external-response-intake.md`, `siem-export-adapter-disposition-closure-gate.md`, and `siem-export-adapter-response-dry-run.md` | Design review for offline/export adapter shape and delivery questions | `false` |
| 6 | `ERG-009` / `PRD-COMPLIANCE-MAPPING-001` | `planning_only` | `compliance-mapping-external-review-bundle.md` plus `compliance-mapping-disposition-packet.md` | `compliance-mapping-response-kit.md`, `compliance-mapping-external-response-intake.md`, `compliance-mapping-disposition-closure-gate.md`, and `compliance-mapping-response-dry-run.md` | Design review for control-mapping support and operator responsibility language | `false` |
| 7 | `ERG-004` / `PRD-SANDBOX-LIVE-POC-001` | `blocked` | `sandbox-vm-live-poc-external-review-bundle.md` plus `sandbox-vm-live-poc-decision-packet.md` | `sandbox-vm-live-poc-response-kit.md`, `sandbox-vm-live-poc-external-response-intake.md`, `sandbox-vm-live-poc-decision-closure-gate.md`, `sandbox-vm-live-poc-response-dry-run.md`, and `sandbox-vm-live-poc-prerequisite-disposition-dry-run.md` | Keep live sandbox/VM worker POC blocked until `ERG-003` receives favorable disposition | `false` |
| 8 | `ERG-010` / `PRD-PUBLIC-POSITIONING-001` | `blocked` | `public-positioning-external-review-bundle.md` plus `public-security-product-positioning-decision-intake.md` | `public-security-product-positioning-response-kit.md`, `public-security-product-positioning-decision-closure-gate.md`, and later claim-review response intake | Claim-review preparation and warning-packet review only | `false` |

The `ERG-003` row also depends on
`sandbox-vm-static-preflight-external-review-bundle.md`, which consolidates the source-review and
disposition artifacts for handoff, and `sandbox-vm-static-preflight-disposition-closure-gate.md`,
which keeps the lane open until
normalized source-level response evidence exists, and
`sandbox-vm-static-preflight-response-kit.md`, which packages response-intake guidance,
normalized-response examples, closure/triage commands, and command evidence for the real response
path, and
`sandbox-vm-static-preflight-response-dry-run.md`, which verifies favorable and unfavorable
normalized-response fixtures without recording external review. A future favorable response must
then follow `sandbox-vm-static-preflight-response-application-playbook.md`,
`sandbox-vm-static-preflight-response-application-record.md`, and
`sandbox-vm-static-preflight-triage-update.md` for the safe committed status update while keeping
`ERG-004` and live runtime work blocked.

## Dependency Order

1. `ERG-003` is first because live sandbox/VM worker proof-of-concept planning depends on static
   preflight disposition.
2. `ERG-002` can proceed in parallel as display/import planning because it stays outside execution,
   policy, approval, audit, sandbox, and local-model authority. Its consolidated launch bundle is
   `mission-control-display-external-review-bundle.md`, its response kit is
   `mission-control-display-response-kit.md`, its fail-closed closure gate is
   `mission-control-display-disposition-closure-gate.md`, and its response dry run is
   `mission-control-display-response-dry-run.md`.
3. `ERG-005` remains blocked until sandbox artifact evidence, exact hash binding, approval
   binding, and negative fixtures receive review. Its consolidated launch bundle is
   `trusted-host-promotion-external-review-bundle.md`, its response kit is
   `trusted-host-promotion-response-kit.md`, its fail-closed closure gate is
   `trusted-host-promotion-disposition-closure-gate.md`, and its response dry run is
   `trusted-host-promotion-response-dry-run.md`.
4. `ERG-006` and `ERG-007` must remain architecture-only until identity, tenancy, storage,
   retention, migration, backup/restore, and evidence custody questions are reviewed; their
   response kit is `production-identity-storage-response-kit.md`, and its response dry run is
   `production-identity-storage-response-dry-run.md`.
5. `ERG-008` remains design-only until adapter schema, redaction, signing, retry/backpressure, and
   delivery boundaries are reviewed; its consolidated launch bundle is
   `siem-export-adapter-external-review-bundle.md`, its response kit is
   `siem-export-adapter-response-kit.md`, and its response dry run is
   `siem-export-adapter-response-dry-run.md`.
6. `ERG-009` remains mapping-support-only and cannot become compliance automation or legal-review
   substitute. Its consolidated launch bundle is `compliance-mapping-external-review-bundle.md`,
   its response kit is `compliance-mapping-response-kit.md`, and its response dry run is
   `compliance-mapping-response-dry-run.md`.
7. `ERG-004` cannot move until `ERG-003` receives favorable disposition and a later post-RC
   decision record approves implementation planning. Its consolidated launch bundle is
   `sandbox-vm-live-poc-external-review-bundle.md`, its fail-closed closure gate is
   `sandbox-vm-live-poc-decision-closure-gate.md`, its response dry run is
   `sandbox-vm-live-poc-response-dry-run.md`, and its prerequisite disposition dry run is
   `sandbox-vm-live-poc-prerequisite-disposition-dry-run.md`.
8. `ERG-010` is last because public/security-product positioning depends on the exact claims that
   prior rows can or cannot support.

## Historical Recommended Review

Recommended next review (historical): `ERG-003` static sandbox/VM preflight disposition.

Historical recommended review: `ERG-003` static sandbox/VM preflight disposition.

Reason: it is the earliest dependency for the live sandbox/VM worker proof of concept and has the
most complete source-review packet, disposition packet, response-intake template, reviewer
reproduction map, negative fixtures, and internal review evidence.

That dependency has since been dispositioned for the local-preview planning path. Keep the section
below as a fallback for old packet reproduction and response-intake lineage; use the active
`ERG-004` route above for current work.

For a compact operator handoff pointer, run:

```sh
make enterprise-next-review-handoff
```

That command is documented in `enterprise-next-review-handoff.md`, writes
`var/review-packets/v3/enterprise-next-review-handoff/`, and points to the exact `ERG-003` upload
files, reviewer prompt, and fail-closed response path.

For a cross-lane operator send-readiness summary, run:

```sh
make enterprise-review-send-readiness
```

When sending the current two recommended packets together, generate the compact operator pointer
with:

```sh
make enterprise-dual-review-handoff
```

See [Enterprise Dual Review Handoff](enterprise-dual-review-handoff.md).

To create one ignored send-ready outbox containing the current `ERG-003/` and `ERG-002/` attachment
sets, run:

```sh
make enterprise-dual-review-outbox
```

See [Enterprise Dual Review Outbox](enterprise-dual-review-outbox.md).

To generate a checked send manifest that ties the current `ERG-003/ERG-002` outbox to response
paths and still-blocked boundaries, run:

```sh
make enterprise-review-send-manifest
```

See [Enterprise Review Send Manifest](enterprise-review-send-manifest.md).

To rehearse the current send/receive sequence with the outbox, send manifest, response inbox,
status board, and fixture-only intake drill, run:

```sh
make enterprise-review-handoff-drill
```

See [Enterprise Review Handoff Drill](enterprise-review-handoff-drill.md). This does not record
review, normalize real responses, close lanes, or approve runtime behavior.

After sending the two packets, prepare local response handling with:

```sh
make enterprise-dual-response-inbox
make enterprise-response-waiting-room
```

See [Enterprise Dual Response Inbox](enterprise-dual-response-inbox.md). The inbox does not
normalize responses, mutate findings, close either lane, or approve runtime behavior.

To prove the all-lane response path still rejects unsafe fixture cases and restores ignored
response state, run:

```sh
make enterprise-response-intake-drill
```

See [Enterprise Response Intake Drill](enterprise-response-intake-drill.md).

After packets are sent, track normalized-response status across all enterprise lanes with:

```sh
make enterprise-response-status-board
```

See [Enterprise Response Status Board](enterprise-response-status-board.md). This board is
read-only and does not record review, mutate findings, close lanes, or approve runtime behavior.

That command is documented in `enterprise-review-send-readiness.md`; it reports packet handoff
readiness for `ERG-003`, `ERG-002`, and the remaining enterprise lanes while keeping implementation
approval, runtime behavior, and lane closure blocked.

Run:

```sh
make sandbox-vm-static-preflight-disposition-packet
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-external-response-intake-check
make sandbox-vm-static-preflight-reviewer-reproduction-map-check
make enterprise-external-review-queue-check
```

After a favorable source-level response, the committed update path must use
`sandbox-vm-static-preflight-disposition-record-skeleton.md` as the disposition-record shape. The
skeleton permits only the static-preflight local-preview disposition and does not unblock `ERG-004`.

The received `ERG-003`/`ERG-002` disposition is now recorded in
`enterprise-dual-response-disposition-record.md`. It closes only the static-preflight evidence lane
allowed by the closure gate, allows only Mission Control design-only continuation, records the open
low advisory `EXT-MC-DISPLAY-001`, and keeps capability expansion and runtime authority blocked.

## Stop Conditions

Stop the queue and keep affected lanes blocked if:

- any review response identifies a critical/high finding;
- a proposed next action requires a runtime surface before its decision record exists;
- a packet asks reviewers to close a lane without source/evidence inspection;
- a lane starts implying Mission Control execution authority, sandbox orchestration, local model
  invocation, trusted-host promotion, SIEM adapter runtime behavior, compliance automation, or
  public/security-product positioning;
- a prerequisite row remains unresolved.

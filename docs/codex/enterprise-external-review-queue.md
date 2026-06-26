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

## Review Queue

| Order | Gap / PRD | Status before review | Primary packet or doc | Intake / response path | Allowed next action | Runtime allowed |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `ERG-003` / `PRD-SANDBOX-PREFLIGHT-001` | `external_review_required` | `sandbox-vm-static-preflight-disposition-packet.md` | `sandbox-vm-static-preflight-external-response-intake.md` | External/source review disposition of static preflight fixture evidence | `false` |
| 2 | `ERG-002` / `PRD-MC-DISPLAY-001` | `planning_only` | `mission-control-integration-readiness-packet.md` | `mission-control-display-external-response-intake.md` | Mission Control-side display/importer planning review only | `false` |
| 3 | `ERG-005` / `PRD-TRUSTED-HOST-001` | `blocked` | `trusted-host-promotion-disposition-packet.md` | `trusted-host-promotion-external-response-intake.md` | Review of design-only promotion evidence and negative fixtures | `false` |
| 4 | `ERG-006` + `ERG-007` / `PRD-PROD-IAM-STORAGE-001` | `planning_only` | `production-identity-storage-disposition-packet.md` | `production-identity-storage-external-response-intake.md` | Architecture review for identity, tenancy, storage, retention, and custody boundaries | `false` |
| 5 | `ERG-008` / `PRD-SIEM-EXPORT-001` | `planning_only` | `siem-export-adapter-disposition-packet.md` | `siem-export-adapter-external-response-intake.md` | Design review for offline/export adapter shape and delivery questions | `false` |
| 6 | `ERG-009` / `PRD-COMPLIANCE-MAPPING-001` | `planning_only` | `compliance-mapping-disposition-packet.md` | `compliance-mapping-external-response-intake.md` | Design review for control-mapping support and operator responsibility language | `false` |
| 7 | `ERG-004` / `PRD-SANDBOX-LIVE-POC-001` | `blocked` | `sandbox-vm-live-poc-decision-packet.md` | `sandbox-vm-live-poc-external-response-intake.md` | Keep live sandbox/VM worker POC blocked until `ERG-003` receives favorable disposition | `false` |
| 8 | `ERG-010` / `PRD-PUBLIC-POSITIONING-001` | `blocked` | `public-security-product-positioning-decision-intake.md` | later claim-review response intake | Claim-review preparation and warning-packet review only | `false` |

The `ERG-003` row also depends on
`sandbox-vm-static-preflight-disposition-closure-gate.md`, which keeps the lane open until
normalized source-level response evidence exists.

## Dependency Order

1. `ERG-003` is first because live sandbox/VM worker proof-of-concept planning depends on static
   preflight disposition.
2. `ERG-002` can proceed in parallel as display/import planning because it stays outside execution,
   policy, approval, audit, sandbox, and local-model authority.
3. `ERG-005` remains design-only until sandbox artifact evidence, exact hash binding, approval
   binding, and negative fixtures receive review.
4. `ERG-006` and `ERG-007` must remain architecture-only until identity, tenancy, storage,
   retention, migration, backup/restore, and evidence custody questions are reviewed.
5. `ERG-008` remains design-only until adapter schema, redaction, signing, retry/backpressure, and
   delivery boundaries are reviewed.
6. `ERG-009` remains mapping-support-only and cannot become compliance automation or legal-review
   substitute.
7. `ERG-004` cannot move until `ERG-003` receives favorable disposition and a later post-RC
   decision record approves implementation planning.
8. `ERG-010` is last because public/security-product positioning depends on the exact claims that
   prior rows can or cannot support.

## Current Recommended Next Review

Recommended next review: `ERG-003` static sandbox/VM preflight disposition.

Reason: it is the earliest dependency for the live sandbox/VM worker proof of concept and has the
most complete source-review packet, disposition packet, response-intake template, reviewer
reproduction map, negative fixtures, and internal review evidence.

Run:

```sh
make sandbox-vm-static-preflight-disposition-packet
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-external-response-intake-check
make sandbox-vm-static-preflight-reviewer-reproduction-map-check
make enterprise-external-review-queue-check
```

## Stop Conditions

Stop the queue and keep affected lanes blocked if:

- any review response identifies a critical/high finding;
- a proposed next action requires a runtime surface before its decision record exists;
- a packet asks reviewers to close a lane without source/evidence inspection;
- a lane starts implying Mission Control execution authority, sandbox orchestration, local model
  invocation, trusted-host promotion, SIEM adapter runtime behavior, compliance automation, or
  public/security-product positioning;
- a prerequisite row remains unresolved.

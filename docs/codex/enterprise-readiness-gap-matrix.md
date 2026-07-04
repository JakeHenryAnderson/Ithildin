# Ithildin Enterprise Readiness Gap Matrix

Status: design-only enterprise gap matrix beyond the v1.0 local-preview RC.

This matrix translates the enterprise-readiness runway into reviewable gaps. It does not approve
runtime behavior, tool manifests, executors, policy rules, API endpoints, MCP transports, Mission
Control runtime behavior, sandbox orchestration, SIEM adapters, production identity, runtime
Postgres, hosted telemetry, shell, Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad
filesystem writes, compliance automation, or public/security-product claims.

Current governed tool count: `24`.

Current selected capability: `not selected`.

## Matrix Rules

- A row marked `closed_local_preview` is closed only for the v1.0 local-preview boundary.
- A row marked `planning_only` may receive docs, schemas, static fixtures, packets, and review
  prompts only.
- A row marked `blocked` requires a post-RC decision record before any implementation work begins.
- A row marked `external_review_required` cannot support broader claims until source or external
  review disposition is recorded.
- No row in this matrix authorizes production identity, runtime Postgres, hosted telemetry, remote
  MCP, Mission Control execution authority, live VM/container control, trusted-host promotion, SIEM
  custody, compliance automation, or public/security-product positioning.

## Gap Matrix

| Gap ID | Area | Current status | Blocks claim/capability | Required evidence before implementation or stronger claim |
| --- | --- | --- | --- | --- |
| `ERG-001` | Local-preview RC operator trial | `closed_local_preview` | Broader public/security-product positioning | Same-commit `make release-check`, `make review-candidate`, packet redaction `findings: 0`, and no critical/high local-preview findings |
| `ERG-002` | Mission Control display/importer | `planning_only` | Mission Control runtime importer and operator dashboard integration | Mission Control-side repository implementation plan, display-only schema, stale/mismatched packet fixtures, source-review handoff, and post-RC decision record; Ithildin-side importer planning exists in `mission-control-display-importer-plan.md`, the decision intake exists in `mission-control-display-decision-intake.md`, the disposition packet exists in `mission-control-display-disposition-packet.md`, the launch bundle exists in `mission-control-display-external-review-bundle.md`, the external response intake template exists in `mission-control-display-external-response-intake.md`, the fail-closed closure gate exists in `mission-control-display-disposition-closure-gate.md`, the response dry-run fixture checker exists in `mission-control-display-response-dry-run.md`, the response kit exists in `mission-control-display-response-kit.md`, the design-only decision-record skeleton exists in `mission-control-display-decision-record-skeleton.md`, the integration readiness packet exists in `mission-control-integration-readiness-packet.md`, the cross-repo work order exists in `mission-control-side-handoff-plan.md`, and the concrete Mission Control implementation ticket exists in `mission-control-integration-implementation-ticket.md` |
| `ERG-003` | Sandbox/VM static preflight | `external_review_required` | Live VM/container inspection and sandbox posture claims | External/source review disposition of static preflight implementation, negative fixtures, profile contract, unsupported-profile warnings, the launch bundle in `sandbox-vm-static-preflight-external-review-bundle.md`, the response kit in `sandbox-vm-static-preflight-response-kit.md`, the disposition packet in `sandbox-vm-static-preflight-disposition-packet.md`, the disposition plan in `sandbox-vm-static-preflight-disposition-plan.md`, the fail-closed closure gate in `sandbox-vm-static-preflight-disposition-closure-gate.md`, the response intake template in `sandbox-vm-static-preflight-external-response-intake.md`, the dry-run fixture checker in `sandbox-vm-static-preflight-response-dry-run.md`, the triage-update checklist in `sandbox-vm-static-preflight-triage-update.md`, the response application playbook in `sandbox-vm-static-preflight-response-application-playbook.md`, and the reviewer reproduction map in `sandbox-vm-static-preflight-reviewer-reproduction-map.md` |
| `ERG-004` | Live sandbox/VM worker proof of concept | `descriptor_only_local_preview_disposition_ready` | Local model invocation inside a VM/container and sandbox run evidence | Favorable `ERG-003` disposition, live-preflight decision record in `sandbox-vm-live-poc-decision-record.md`, the VM-first planning packet in `sandbox-vm-live-poc-implementation-plan.md`, the runtime proposal in `sandbox-vm-live-poc-runtime-proposal.md`, the descriptor-only implementation record in `sandbox-vm-live-poc-runtime-descriptor-only-implementation.md`, the descriptor-only source-review bundle in `sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle.md`, the descriptor-only response inbox in `sandbox-vm-live-poc-runtime-descriptor-only-response-inbox.md`, the descriptor-only send receipt in `sandbox-vm-live-poc-runtime-descriptor-only-send-receipt.md`, the local-development disposition marker in `sandbox-vm-live-poc-runtime-descriptor-only-response-application-record.md`, the readiness map in `enterprise-sandbox-control-plane-readiness.md`, the intake packet in `sandbox-vm-live-poc-decision-intake.md`, the evidence contract in `sandbox-vm-live-poc-evidence-contract.md`, the preconditions map in `sandbox-vm-live-poc-preconditions-map.md`, the aggregate ready check in `sandbox-vm-live-poc-preconditions-ready-check.md`, the post-`ERG-003` handoff in `sandbox-vm-live-poc-post-erg003-handoff.md`, the prerequisite disposition dry-run fixture checker in `sandbox-vm-live-poc-prerequisite-disposition-dry-run.md`, the decision packet in `sandbox-vm-live-poc-decision-packet.md`, the launch bundle in `sandbox-vm-live-poc-external-review-bundle.md`, the response kit in `sandbox-vm-live-poc-response-kit.md`, the external response intake template in `sandbox-vm-live-poc-external-response-intake.md`, the fail-closed closure gate in `sandbox-vm-live-poc-decision-closure-gate.md`, the decision-record skeleton in `sandbox-vm-live-poc-decision-record-skeleton.md`, and the response dry-run fixture checker in `sandbox-vm-live-poc-response-dry-run.md`; live VM/container inspection, local model invocation, sandbox orchestration, runtime behavior, and broader enterprise claims still require a later explicit runtime gate and external/source review |
| `ERG-005` | Trusted-host artifact promotion | `ready_for_implementation_planning_only` | Moving sandbox outputs into host staging/approved zones | Artifact hash-binding model, approval model, the trusted host descriptor contract in `trusted-host-descriptor-contract.md`, the state machine in `trusted-host-promotion-state-machine.md`, the negative fixture contract in `trusted-host-promotion-negative-fixtures.md`, the zone contract in `trusted-host-promotion-zone-contract.md`, the implementation-plan contract in `trusted-host-promotion-implementation-plan.md`, the source-review handoff in `trusted-host-promotion-source-review.md`, the disposition packet in `trusted-host-promotion-disposition-packet.md`, the launch bundle in `trusted-host-promotion-external-review-bundle.md`, the response kit in `trusted-host-promotion-response-kit.md`, the external response intake template in `trusted-host-promotion-external-response-intake.md`, the fail-closed closure gate in `trusted-host-promotion-disposition-closure-gate.md`, the response dry-run fixture checker in `trusted-host-promotion-response-dry-run.md`, the decision record in `trusted-host-promotion-decision-record.md`, Goal B source-review/runtime-boundary packet, Goal C implementation-gate decision, conflict/replay/path-escape negative transcripts, external/source review, and the decision intake in `trusted-host-promotion-decision-intake.md`; runtime trusted-host promotion remains blocked |
| `ERG-006` | Production identity and multi-user authorization | `planning_only` | Enterprise identity, RBAC, tenant/team authorization, and remote admin use | The design-only architecture packet in `production-identity-storage-architecture.md`, the disposition packet in `production-identity-storage-disposition-packet.md`, the launch bundle in `production-identity-storage-external-review-bundle.md`, the response kit in `production-identity-storage-response-kit.md`, the external response intake template in `production-identity-storage-external-response-intake.md`, the fail-closed closure gate in `production-identity-storage-disposition-closure-gate.md`, the response dry-run fixture checker in `production-identity-storage-response-dry-run.md`, identity provider design, local-principal mapping, tenant/workspace model, session/admin model, audit attribution model, post-RC decision record, and external architecture review |
| `ERG-007` | Durable runtime storage and retention | `planning_only` | Runtime Postgres, multi-user concurrency, retention policy, backup/restore, and production custody | The design-only architecture packet in `production-identity-storage-architecture.md`, the disposition packet in `production-identity-storage-disposition-packet.md`, the launch bundle in `production-identity-storage-external-review-bundle.md`, the response kit in `production-identity-storage-response-kit.md`, the external response intake template in `production-identity-storage-external-response-intake.md`, the fail-closed closure gate in `production-identity-storage-disposition-closure-gate.md`, the response dry-run fixture checker in `production-identity-storage-response-dry-run.md`, storage architecture decision, migration plan, backup/restore plan, retention model, failure-mode tests, post-RC decision record, and source review |
| `ERG-008` | SIEM-shaped export adapter | `planning_only` | SIEM integration, delivery/retry behavior, and security-ops ingestion | The design-only adapter architecture packet in `siem-export-adapter-architecture.md`, the disposition packet in `siem-export-adapter-disposition-packet.md`, the launch bundle in `siem-export-adapter-external-review-bundle.md`, the response kit in `siem-export-adapter-response-kit.md`, the external response intake template in `siem-export-adapter-external-response-intake.md`, the fail-closed closure gate in `siem-export-adapter-disposition-closure-gate.md`, the response dry-run fixture checker in `siem-export-adapter-response-dry-run.md`, stable event schema, redaction policy, delivery/backpressure model, compatibility tests, signing/verification story, post-RC decision record, and external/source review |
| `ERG-009` | Compliance mapping support | `planning_only` | HIPAA/GLBA/SOX/GDPR or other compliance claims | The design-only architecture packet in `compliance-mapping-architecture.md`, the disposition packet in `compliance-mapping-disposition-packet.md`, the launch bundle in `compliance-mapping-external-review-bundle.md`, the response kit in `compliance-mapping-response-kit.md`, the external response intake template in `compliance-mapping-external-response-intake.md`, the fail-closed closure gate in `compliance-mapping-disposition-closure-gate.md`, the response dry-run fixture checker in `compliance-mapping-response-dry-run.md`, control mapping templates, legal-review boundary, operator responsibility language, evidence reconstruction guide, explicit no-compliance-automation wording, post-RC decision record, and external/source review |
| `ERG-010` | Public/security-product positioning | `blocked` | Marketing as production security control, sandbox, EDR/MDM, SIEM, or compliance system | The no-go decision intake in `public-security-product-positioning-decision-intake.md`, the launch bundle in `public-positioning-external-review-bundle.md`, the response kit in `public-security-product-positioning-response-kit.md`, the fail-closed closure gate in `public-security-product-positioning-decision-closure-gate.md`, independent review, resolved accepted risks, production identity/storage decisions, deployment hardening, support model, explicit claim wording review, and a later committed go/no-go decision before broader public/security-product positioning |

## Claim Boundary Summary

Allowed current claims:

- local-preview governed MCP/tool gateway;
- bounded read-only metadata tools and approval-gated patch apply under the current manifests;
- local, tamper-evident evidence and locally signed exports where configured;
- operator workbench and Mission Control handoff packets as evidence/display planning surfaces.
- Mission Control outside execution, policy, approval, audit authority.

Blocked current claims, written without product-marketing claim phrases:

- production deployment readiness;
- organization identity/RBAC;
- OS-isolated sandbox guarantee;
- SIEM custody;
- custody-grade or regulatory audit guarantee;
- HIPAA/GLBA/SOX/GDPR compliance automation;
- Mission Control execution authority;
- Ithildin-managed VM/container lifecycle;
- trusted-host promotion.

## Next Enterprise Action

The next enterprise-readiness action is to choose one matrix row and create or update a post-RC
decision record before implementation begins. The review sequence is tracked in
`enterprise-external-review-queue.md`, which currently recommends `ERG-003` static sandbox/VM
preflight disposition as the next external/source review because it gates later live sandbox/VM
worker planning. Mission Control display/importer planning (`ERG-002`) remains the most
conservative usability lane because it can improve operator visibility while keeping Mission
Control outside execution, policy, approval, audit authority, local-model invocation, sandbox
orchestration, and trusted-host promotion. Compliance mapping support (`ERG-009`) now has the
planning-only architecture packet in
`compliance-mapping-architecture.md` and the focused disposition packet in
`compliance-mapping-disposition-packet.md`; it may support future operator control mapping only and
still blocks compliance automation, legal conclusions, and regulated-industry compliance claims.
Public/security-product positioning (`ERG-010`) now has the explicit no-go decision intake in
`public-security-product-positioning-decision-intake.md`; the fail-closed closure gate in
`public-security-product-positioning-decision-closure-gate.md` supports claim-review evidence
and the response kit in `public-security-product-positioning-response-kit.md` packages real
reviewer feedback for later claim-decision triage
validation only
and keeps broader public/security-product, production/security/compliance, sandbox, EDR/MDM, SIEM
custody, and compliance-product claims blocked.

The only future `ERG-003` static preflight disposition-record shape is
`sandbox-vm-static-preflight-disposition-record-skeleton.md`. It may be used only after favorable
source-level evidence passes the closure gate and still keeps `ERG-004` and live sandbox/VM runtime
work blocked.

The current received-response disposition is recorded in
`enterprise-dual-response-disposition-record.md`. It records `ERG-003` as
`closed_local_preview_static_preflight` for CLI-only static preflight evidence and `ERG-002` as
`ready_for_design_only_decision_record` for Mission Control display/import planning only, while
preserving the open low advisory `EXT-MC-DISPLAY-001` and keeping runtime/importer/live-VM powers
blocked.

## Validation

Run:

```sh
make enterprise-readiness-gap-matrix-check
make enterprise-readiness-runway-check
make post-rc-decision-register-check
```

All checks must remain green before `make release-check` can pass.

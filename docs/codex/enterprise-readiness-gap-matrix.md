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
| `ERG-002` | Mission Control display/importer | `planning_only` | Mission Control runtime importer and operator dashboard integration | Mission Control-side repository implementation plan, display-only schema, stale/mismatched packet fixtures, source-review handoff, and post-RC decision record; Ithildin-side importer planning exists in `mission-control-display-importer-plan.md`, the decision intake exists in `mission-control-display-decision-intake.md`, the disposition packet exists in `mission-control-display-disposition-packet.md`, the cross-repo work order exists in `mission-control-side-handoff-plan.md`, and the concrete Mission Control implementation ticket exists in `mission-control-integration-implementation-ticket.md` |
| `ERG-003` | Sandbox/VM static preflight | `external_review_required` | Live VM/container inspection and sandbox posture claims | External/source review disposition of static preflight implementation, negative fixtures, profile contract, unsupported-profile warnings, the disposition packet in `sandbox-vm-static-preflight-disposition-packet.md`, the disposition plan in `sandbox-vm-static-preflight-disposition-plan.md`, and the response intake template in `sandbox-vm-static-preflight-external-response-intake.md` |
| `ERG-004` | Live sandbox/VM worker proof of concept | `blocked` | Local model invocation inside a VM/container and sandbox run evidence | Favorable `ERG-003` disposition, live-preflight decision record, the intake packet in `sandbox-vm-live-poc-decision-intake.md`, the evidence contract in `sandbox-vm-live-poc-evidence-contract.md`, operator-managed VM profile, network/mount/root contract, cleanup transcript, failure transcript, and external/source review |
| `ERG-005` | Trusted-host artifact promotion | `blocked` | Moving sandbox outputs into host staging/approved zones | Artifact hash-binding model, approval model, the state machine in `trusted-host-promotion-state-machine.md`, the negative fixture contract in `trusted-host-promotion-negative-fixtures.md`, the zone contract in `trusted-host-promotion-zone-contract.md`, the implementation-plan skeleton in `trusted-host-promotion-implementation-plan.md`, the source-review handoff in `trusted-host-promotion-source-review.md`, the disposition packet in `trusted-host-promotion-disposition-packet.md`, conflict/replay/path-escape negative transcripts, external/source review, and the decision intake in `trusted-host-promotion-decision-intake.md` |
| `ERG-006` | Production identity and multi-user authorization | `planning_only` | Enterprise identity, RBAC, tenant/team authorization, and remote admin use | The design-only architecture packet in `production-identity-storage-architecture.md`, identity provider design, local-principal mapping, tenant/workspace model, session/admin model, audit attribution model, post-RC decision record, and external architecture review |
| `ERG-007` | Durable runtime storage and retention | `planning_only` | Runtime Postgres, multi-user concurrency, retention policy, backup/restore, and production custody | The design-only architecture packet in `production-identity-storage-architecture.md`, storage architecture decision, migration plan, backup/restore plan, retention model, failure-mode tests, post-RC decision record, and source review |
| `ERG-008` | SIEM-shaped export adapter | `planning_only` | SIEM integration, delivery/retry behavior, and security-ops ingestion | The design-only adapter architecture packet in `siem-export-adapter-architecture.md`, stable event schema, redaction policy, delivery/backpressure model, compatibility tests, signing/verification story, post-RC decision record, and external/source review |
| `ERG-009` | Compliance mapping support | `planning_only` | HIPAA/GLBA/SOX/GDPR or other compliance claims | The design-only architecture packet in `compliance-mapping-architecture.md`, control mapping templates, legal-review boundary, operator responsibility language, evidence reconstruction guide, explicit no-compliance-automation wording, post-RC decision record, and external/source review |
| `ERG-010` | Public/security-product positioning | `blocked` | Marketing as production security control, sandbox, EDR/MDM, SIEM, or compliance system | Independent review, resolved accepted risks, production identity/storage decisions, deployment hardening, support model, and claim review |

## Claim Boundary Summary

Allowed current claims:

- local-preview governed MCP/tool gateway;
- bounded read-only metadata tools and approval-gated patch apply under the current manifests;
- local, tamper-evident evidence and locally signed exports where configured;
- operator workbench and Mission Control handoff packets as evidence/display planning surfaces.

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
decision record before implementation begins. Mission Control display/importer planning (`ERG-002`)
remains the most conservative usability lane because it can improve operator visibility while
keeping Mission Control outside execution, policy, approval, audit authority, local-model
invocation, sandbox orchestration, and trusted-host promotion. Compliance mapping support
(`ERG-009`) now has the planning-only architecture packet in
`compliance-mapping-architecture.md`; it may support future operator control mapping only and still
blocks compliance automation, legal conclusions, and regulated-industry compliance claims.

## Validation

Run:

```sh
make enterprise-readiness-gap-matrix-check
make enterprise-readiness-runway-check
make post-rc-decision-register-check
```

All checks must remain green before `make release-check` can pass.

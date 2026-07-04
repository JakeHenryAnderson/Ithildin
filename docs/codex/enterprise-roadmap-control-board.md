# Ithildin Enterprise Roadmap Control Board

Status: checked enterprise roadmap control board for the v1.0 enterprise-grade target.

This board defines the path from the current local-preview technical MVP to a future
enterprise-grade Ithildin product. It is a roadmap and control surface, not an approval that the
current build is production ready. Every runtime authority increase remains gated by proposal,
implementation plan, source review, response intake, closure evidence, and explicit user approval.

Current governed tool count: `24`
Current selected capability: `not selected`
Current send set: `ERG-005`
Current response count: `0`
Current closure-ready count: `0`
Active resume checkpoint: `ENT-001`

## Enterprise Target Definition

The target end state is a governed local or organization-managed agent workbench where Mission
Control presents operator workflow, Ithildin mediates tools and evidence, and sandbox/VM or
workspace boundaries keep agent work reviewable before artifacts move toward trusted host areas.
The target requires strong identity/storage decisions, evidence export contracts, incident
reconstruction, deployment guidance, and external review. The current repo is not claiming those
properties today.

## Current Resume Scope

The current resumed goal is limited to post-`ENT-001` trusted-host promotion review: use the
recorded `ERG-004` descriptor-only local-development disposition to validate the blocked `ERG-005`
trusted-host promotion review lane. Live sandbox/VM execution, trusted-host promotion runtime
behavior, Mission Control implementation, and capability selection remain blocked.

## Enterprise Milestones

| ID | Milestone | Current status | Entry requirement | Done criteria | Proof command | Still blocked after done |
| --- | --- | --- | --- | --- | --- | --- |
| `ENT-001` | Send current external review packets | done | Fresh `review-candidate`, valid send package, valid receipt template. | `ERG-003` and `ERG-002` sent; send receipt filled and validated. | `make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json` | response normalization and lane closure |
| `ENT-002` | Close `ERG-003` static sandbox/VM preflight | done for static preflight | Raw `EXT-SVP-###` response pasted into ignored inbox. | Static preflight lane closed for local-preview planning. | `make enterprise-dual-response-disposition-record-check` | live VM/container execution |
| `ENT-003` | Close `ERG-002` Mission Control display/import planning | done for design-only continuation | Raw `EXT-MC-DISPLAY-###` response pasted into ignored inbox. | Display/import planning disposition recorded; Mission Control implementation remains separate. | `make enterprise-dual-response-disposition-record-check` | Mission Control execution, policy, approval, or audit authority |
| `ENT-004` | Stage 2 live sandbox/VM proof of concept | descriptor-only local-development disposition recorded | Favorable `ERG-003`, live POC decision record, implementation plan, runtime proposal, draft runtime ticket, internal runtime-ticket review, and descriptor-only local-development disposition. | A small local agent/VM demonstration remains specified and bounded; live runtime work still requires a later explicit gate. | `make sandbox-vm-live-poc-runtime-descriptor-only-response-application-record-check` | live VM/container execution and enterprise sandbox orchestration claims |
| `ENT-005` | Mission Control display/import implementation | blocked | Favorable `ERG-002` plus display-only implementation ticket. | Mission Control can display/import Ithildin status artifacts without polling or mutating Ithildin authority. | Mission Control-side acceptance plus Ithildin fixture checks | Mission Control runtime execution authority |
| `ENT-006` | Trusted-host promotion design | active review lane | Static/live sandbox evidence and promotion evidence contract reviewed. | Promotion state machine, negative fixtures, zone contract, and response kit dispositioned. | `make trusted-host-promotion-disposition-closure-check` | automatic promotion, overwrite/delete/move, broad host writes |
| `ENT-007` | SIEM-shaped export adapter design | planning-only | Evidence schema, redaction rules, and incident reconstruction reviewed. | Export adapter architecture dispositioned without claiming custody-grade SIEM behavior. | `make siem-export-adapter-disposition-closure-check` | hosted SIEM integration or custody claims |
| `ENT-008` | Production identity and storage architecture | planning-only | Local-preview identity/storage limits accepted and enterprise requirements reviewed. | Identity/storage architecture decision recorded. | `make production-identity-storage-disposition-closure-check` | production auth, runtime Postgres, managed tenancy |
| `ENT-009` | Compliance mapping support | planning-only | Control mapping and data-classification docs reviewed. | Mapping-support architecture dispositioned without compliance automation claims. | `make compliance-mapping-disposition-closure-check` | HIPAA/GLBA/SOX/GDPR compliance claims |
| `ENT-010` | Public/security-product positioning | blocked | External review of public claims and product boundary. | Positioning decision record approves exact wording or keeps blocked. | `make public-security-product-positioning-decision-closure-check` | production/security-product claims beyond approved wording |
| `ENT-011` | Enterprise deployment and operations model | not started | Identity/storage, sandbox, SIEM, Mission Control, and promotion decisions are dispositioned. | Installation, upgrade, backup, incident, key-management, and support model documented and reviewed. | future deployment-readiness gate | managed service claims |
| `ENT-012` | v1.0 enterprise-grade release candidate | not started | All required enterprise lanes closed or accepted as deferred with explicit risk. | Release packet, source review, operator trial, deployment evidence, and public claims are aligned. | future enterprise RC gate | claims outside the release packet |

## Dependency Order

1. Keep `ENT-001`, `ENT-002`, and `ENT-003` as recorded dispositions.
2. Treat `ENT-004` descriptor-only local-development disposition as recorded, while keeping live sandbox/VM runtime blocked.
3. Keep Mission Control display/import implementation separate from the `ENT-003` planning disposition.
4. Use `ENT-004` and `ENT-005` to prove the operator-control-plane split.
5. Use `ENT-006` to review trusted-host promotion before any sandbox output can move toward host staging.
6. Only then revisit SIEM adapters, identity/storage, compliance mapping,
   and public positioning.

## Non-Negotiable Gates

- No new governed power class without proposal, implementation plan, implementation gate,
  policy/resource/audit coverage, source-review handoff, and explicit approval.
- No sandbox/VM lifecycle control before `ERG-003` and live POC decision closure.
- No Mission Control execution authority before the display/import lane proves read-only status
  handling.
- No trusted-host promotion until hash-bound artifacts, approval evidence, negative fixtures, and
  operator decision points are reviewed.
- No production identity, runtime Postgres, hosted telemetry, remote MCP, SIEM adapter, compliance
  automation, or public/security-product positioning without separate closure.

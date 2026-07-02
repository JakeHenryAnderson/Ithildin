# Ithildin Technical MVP Execution Board

Status: checked technical-MVP execution board and batch-control map.

This board is the compact source of truth for the current technical MVP path. It does not replace
the detailed ticket map, release evidence, or review packets. It exists so the next sprint can move
specific boxes from blocked, ready, or observed to done with a named proof command instead of
running the full release ceremony after every small edit.

Current governed tool count: `24`
Current selected capability: `not selected`
Latest implemented tool: `sandbox.artifact.write_text`
Technical MVP state: `operator_trial_observed`
Current enterprise next action: `prepare_erg004_runtime_implementation_gate`
Active resume checkpoint: `ENT-001`

## Active Resume Scope

The paused umbrella goal resumes through the post-`ENT-001` runtime implementation-gate prep slice
only: use the recorded `ERG-004` runtime-ticket internal review to draft and validate the explicit
runtime implementation gate. This resume slice does not add runtime behavior, implement Mission
Control integration, start sandbox/VM control, or select a new capability.

## Boundary

The technical MVP is a local-preview governed MCP/tool gateway with operator workbench evidence,
approval/audit evidence, bounded read-only project intelligence, and a small observed sandbox
artifact path. It is not a production identity system, remote MCP platform, SIEM adapter,
compliance automation system, Mission Control runtime, sandbox/VM orchestrator, trusted-host
promotion engine, public/security-product release, or broad write platform.

## Milestones

| ID | Milestone | Current status | Done criteria | Fast proof | Full proof | Blocked authority |
| --- | --- | --- | --- | --- | --- | --- |
| `MVP-001` | Governed gateway foundation | done | MCP ingress, registry, schema validation, policy, scoped executors, audit, and local admin evidence remain wired. | `make readiness-check` | `make release-check` | no remote MCP or production identity |
| `MVP-002` | Policy, registry, and tool-surface invariants | done | Tool count remains `24`; manifest lock and no-new-powers gates pass. | `make tool-surface-invariant-gate` | `make release-check` | no unapproved manifests or executors |
| `MVP-003` | Approval, audit, and patch evidence | done | Approval binding, one-time apply, recovery diagnostics, audit evidence, and signed-evidence helpers remain validated. | `make evidence-check` | `make release-check` | no broad writes or automatic repair |
| `MVP-004` | Read-only Git and project intelligence | done for current scope | Existing bounded metadata tools remain count-only or safe-label-only with policy parity. | `make read-only-project-intelligence` | `make release-check` | no dependency names, scripts, raw paths, or content exposure beyond approved contracts |
| `MVP-005` | Agent Run and operator workbench evidence | done for local preview | Agent Run timeline, evidence export, dashboard readiness, and workbench packet gates pass. | `make workbench-readiness` | `make review-candidate` | no run pause, abort, replay, or repair controls |
| `MVP-006` | Local-preview sandbox artifact path | observed | `sandbox.artifact.write_text` remains bounded and the observed demo reports completed patch apply plus valid audit verification. | `make sandbox-artifact-observed-demo-check` | `make release-check` | no sandbox orchestration or trusted-host promotion |
| `MVP-007` | v1.0 local-preview RC handoff | ready | v1.0 RC packet exists, release transcript passed, packet redaction has zero findings, and artifact freshness is valid. | `make artifact-freshness-check` | `make review-candidate` | no public/security-product positioning |
| `MVP-008` | `ERG-003` static sandbox/VM preflight | disposition recorded | Static preflight is closed for local-preview planning only; live VM/container work still needs a separate `ERG-004` decision packet. | `make enterprise-dual-response-disposition-record-check` | `make release-check` | no live VM/container inspection or lifecycle management |
| `MVP-009` | `ERG-002` Mission Control display/import planning | disposition recorded | Display/import planning may continue as design-only work with `EXT-MC-DISPLAY-001` tracked as low advisory packet coverage. | `make enterprise-dual-response-disposition-record-check` | `make release-check` | no Mission Control execution, policy, approval, or audit authority |
| `MVP-010` | Enterprise response intake waiting room | reset to placeholders | Raw response placeholders are reset after disposition; no active normalized response evidence is present. | `make enterprise-response-waiting-room` | `make handoff-dry-run` | no new external review recorded and no additional lanes closed |

## Current Batch Queue

| Batch | Status | Subtasks | Fast gate | Escalation gate |
| --- | --- | --- | --- | --- |
| Prepare `ERG-004` live-POC runtime implementation gate | active | Validate the runtime-ticket internal review, draft implementation-gate contract, descriptor contract, descriptor-contract internal review, gate-readiness packet, response dry run, and `sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton.md` while keeping runtime blocked. | `make sandbox-vm-live-poc-runtime-ticket-internal-review-check`; `make sandbox-vm-live-poc-runtime-descriptor-contract-check`; `make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check`; `make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run` | `make sandbox-vm-live-poc-runtime-implementation-gate-check`; `make sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check`; `make sandbox-vm-live-poc-runtime-gate-readiness-review-bundle-check` |
| Intake future `ERG-004` response | blocked on external response | Paste raw response, run paste preflight, normalize fixture/dry-run, run lane closure gates. | `make enterprise-response-now` | lane-specific closure gate |
| Track `EXT-MC-DISPLAY-001` | later advisory | Improve Mission Control launch-bundle artifact coverage before implementation, without blocking design-only continuation. | `make reviewer-findings-check` | `make review-findings-summary` |

## Development Validation Ladder

Use full gates only when a batch reaches a handoff or release boundary.

| Tier | Use when | Commands |
| --- | --- | --- |
| Inner loop | docs, scripts, or tests changed inside one lane | `make validation-decision-run ARGS="changed files..."`, focused pytest nodes, `make lint`, `make typecheck` |
| Batch checkpoint | one lane-bounded batch is complete | `make status-now`, `make enterprise-status-slice`, `make handoff-dry-run`, lane-specific gates |
| Handoff freeze | packets or release evidence will be sent or used as proof | `make release-check`, `make review-candidate`, `make artifact-freshness-check` |

## Stop Conditions

Stop batching and report status if a critical/high trust-boundary issue appears, the same focused
gate fails three times, a fix requires changing this boundary, a batch would mix runtime authority
with planning-only docs, or generated artifacts become stale in a way that cannot be repaired by the
documented refresh commands.

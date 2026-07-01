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
Current enterprise next action: `send_erg_003_and_erg_002`
Active resume checkpoint: `ENT-001`

## Active Resume Scope

The paused umbrella goal resumes through `ENT-001` only: send the current `ERG-003` and `ERG-002`
external review packets, record the send receipt, and then wait for reviewer responses. This resume
slice does not add runtime behavior, close review lanes, implement Mission Control integration,
start sandbox/VM control, or select a new capability.

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
| `MVP-008` | `ERG-003` static sandbox/VM preflight | send-ready | Upload batch, prompt, response path, dry-run, and closure gate pointers are present. | `make enterprise-send-now` | `make review-candidate` | no live VM/container inspection or lifecycle management |
| `MVP-009` | `ERG-002` Mission Control display/import planning | send-ready | Upload batches, prompt, response path, dry-run, and closure gate pointers are present. | `make enterprise-send-now` | `make review-candidate` | no Mission Control execution, policy, approval, or audit authority |
| `MVP-010` | Enterprise response intake waiting room | ready and waiting | Placeholder raw-response paths exist for `ERG-003` and `ERG-002`; no response is normalized until real review text is pasted. | `make enterprise-response-waiting-room` | `make handoff-dry-run` | no external review recorded and no lanes closed |

## Current Batch Queue

| Batch | Status | Subtasks | Fast gate | Escalation gate |
| --- | --- | --- | --- | --- |
| Send `ERG-003` and `ERG-002` | ready | Send upload batches, copy/fill send receipt, validate receipt, wait for responses. | `make enterprise-send-now` | `make handoff-dry-run` |
| Intake reviewer responses | blocked on external response | Paste raw responses, run paste preflight, normalize fixture/dry-run, run lane closure gates. | `make enterprise-response-now` | lane-specific closure gate |
| Close `ERG-003` static preflight | blocked on response | Normalize `EXT-SVP-###` findings, run dry run, produce disposition, decide whether live POC planning may continue. | `make sandbox-vm-static-preflight-response-dry-run` | `make sandbox-vm-static-preflight-disposition-closure-check` |
| Close `ERG-002` display/import planning | blocked on response | Normalize `EXT-MC-DISPLAY-###` findings, run dry run, produce display/import decision record. | `make mission-control-display-response-dry-run` | `make mission-control-display-disposition-closure-check` |

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

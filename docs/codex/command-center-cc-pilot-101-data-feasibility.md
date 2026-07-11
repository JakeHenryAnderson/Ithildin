# CC-PILOT-101 Authoritative Data Feasibility Map

Status: preimplementation review for `CC-PILOT-101`; current API and record sources are sufficient
for the bounded UI slice described here.

This map verifies that the first Command Center pilot ticket can be implemented without changing
schemas, APIs, manifests, governed tools, policy semantics, approval behavior, audit behavior, or
runtime authority. It does not approve later Command Center tickets or a new runtime contract.

## Reviewed Slice

`CC-PILOT-101` adds a purpose-led Command Center entry, persistent six-area navigation, explicit
authentication/local-preview posture, and one exception-first Attention item that opens an existing
Agent Run Workbench context.

The UI may group and explain existing records. It must not store a new mission, attention, or
workflow state.

## Field and Action Map

| UI concept | Existing authoritative source | Presentation rule | Feasibility |
| --- | --- | --- | --- |
| Authentication required | Local UI token state plus `401`/`403` response from existing admin endpoints | Distinguish `Sign-in required` from an authenticated local-preview limitation. Never expose the token. | Existing |
| Local-preview posture | `GET /system/status` → `security.preview_label` and `security.production_ready` | Display local-preview scope and state that it is not production readiness. | Existing |
| Product purpose | Current Command Center product-direction contract | Static explanatory copy only; it is not runtime state. | Existing presentation |
| Six navigation areas | Command Center information architecture | Anchor navigation over existing page sections. Empty/future areas may link to the nearest current authoritative surface; no state or permission is implied. | Existing presentation |
| Pending decision count | `GET /approvals/review?status=pending` | Count returned approval reviews. Do not infer other approval states. | Existing |
| Primary approval attention item | First returned pending `ApprovalReview` | Show `approval.summary`, `approval.status`, `approval.tool_name`, `approval.expires_at`, and binding validity. | Existing |
| Required action and consequence | Pending approval status plus `review.valid` | `Review decision` only when binding review is valid; otherwise `Review stale binding evidence`. Do not approve automatically. | Existing derived presentation |
| Workspace | `approval.one_time_scope.workspace_id`, then matched Agent Run `workspace_id` | Always label the value as Workspace. Never show an unlabeled fallback. | Existing |
| Requesting identity | `approval.principal.id` or `approval.one_time_scope.requesting_principal.id` | Label as Requesting identity and retain the stable ID. | Existing |
| Policy reason | `approval.metadata.policy_reason` | Show only when present. Use `Policy reason unavailable` rather than inventing a rationale. | Existing |
| Proposal linkage | `approval.one_time_scope.proposal_id` and `GET /patch-proposals` | Select the exact existing proposal when the operator opens the attention item. | Existing |
| Run linkage | `AgentRun.last_request_id == approval.request_id`; conservative fallback to same workspace and principal only for display, not authority | Prefer exact request correlation. If no exact run exists, open the Agent Runs section without claiming a mission match. | Existing |
| Mission-facing label | Existing safe run metadata when it identifies the guided local demo; otherwise workspace plus short run ID | Label this as presentation context. Do not claim Ithildin created or controls a mission process. | Existing presentation |
| Failed-action attention | `GET /audit-events?limit=100` events whose type ends in `.failed` | Use only when there is no pending approval. Show recorded failure and request ID. | Existing |
| Recovery attention | `GET /patch-apply-diagnostics` with non-`clean` status | Use only when there is no pending approval or recorded failure. Preserve the diagnostic state verbatim. | Existing |
| Proposed-change attention | `GET /patch-proposals` with `status == proposed` | Use only when no higher-priority item exists. `Proposed` is not approval or application. | Existing |
| No attention needed | All four bounded sources above contain no actionable record | Say that no action is identified in the loaded local records. Do not imply global safety. | Existing derived presentation |
| Open Workbench | Local selection of an existing `run_id` and optional `proposal_id`, followed by anchor navigation | Changes presentation selection only. It does not create, mutate, start, pause, or control a run. | Existing presentation |

## Deterministic Priority

The bounded first slice chooses at most one primary Attention item in this order:

1. pending approval returned by the existing approval-review endpoint;
2. recorded audit event whose type ends in `.failed`;
3. non-clean patch-apply diagnostic state;
4. proposed patch record;
5. no action identified in the currently loaded records.

This is a UI priority rule, not a stored Gateway severity or anomaly score. The page must label the
source record and consequence. Later queue generalization belongs to a separate ticket.

## Navigation Mapping for the First Slice

| Navigation label | Current bounded target |
| --- | --- |
| Attention | New derived Attention section described above. |
| Missions / Agent Runs | Existing Agent Runs panel and selected-run evidence view. |
| Artifacts | Existing patch proposal list/detail surface. |
| Approvals | Existing pending approval review surface. |
| Evidence | Existing audit-integrity and recent-audit evidence surfaces. |
| Administration | Existing System Trust, registered tools, policy preview, and policy impact surfaces. |

The navigation does not claim the current page already satisfies the final information architecture.
Later tickets will rehome and refine these specialist surfaces.

## Boundary Review

- Governed tool count remains `24`.
- No API request is added or changed.
- No approval action is added to the Attention item.
- No new mission, attention, severity, role, or workflow state is stored.
- Command Center only selects and explains existing records.
- Gateway remains authoritative for policy, approval, execution, artifacts, and audit.
- Local-preview status remains visible and is not described as production or enterprise readiness.

## Implementation Stop Conditions

Stop `CC-PILOT-101` if implementation requires a missing field, new endpoint, new stored state,
approval mutation outside existing controls, run-control behavior, external notification,
identity/RBAC change, or any inference that cannot be traced to the sources above.

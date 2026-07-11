# CC-PILOT-103 Authoritative Data Feasibility Map

Status: preimplementation review for `CC-PILOT-103`; existing proposal and approval APIs support a
bounded artifact-lifecycle view without a new runtime contract.

This map does not approve new approval semantics, artifact promotion, review-complete state,
arbitrary host writes, schema/API changes, or governed powers.

## Reviewed Slice

`CC-PILOT-103` lets an operator select a patch proposal, understand its recorded proposal and
approval/application state, review a concise change summary before the raw diff, and find the next
available action without treating application as review, promotion, publication, or release.

## Field Map

| Visible field or action | Existing source | Presentation rule |
| --- | --- | --- |
| Proposal and request | `GET /patch-proposals` summary | Keep both machine IDs in the selected detail; abbreviate only in routine list presentation. |
| Workspace and target path | Proposal `workspace_id`, `path` | Label workspace and artifact path separately. Path is a governed-workspace-relative target, not an arbitrary host path. |
| Requesting identity | Matching approval `principal` or `one_time_scope.requesting_principal` | If no approval correlated by `proposal_id` exists, show `Unavailable`; the proposal API intentionally does not expose the stored principal. |
| Proposal state | Proposal `status` | Preserve the machine state. `proposed` means awaiting later lifecycle work; it does not mean approved or applied. |
| Approval state | Existing `GET /approvals` history, correlated by `one_time_scope.proposal_id`; current `GET /approvals/review?status=pending` binding review | Keep pending, approved, denied, expired, executing, executed, or other recorded values distinct. Only a current pending valid review exposes approve/deny actions in the existing Pending Approvals panel. |
| Application state | Proposal `status` plus safe proposal review | `applied` means the patch proposal was recorded as applied. It does not prove operator review, promotion, publication, release, or external effect. |
| Binding/staleness | Proposal `review`; matching approval binding review | Show stale/invalid binding separately from proposal and approval state. Do not turn a post-application stale review into a failure claim. |
| Change summary | Proposal path, workspace, status, timestamps, and unified diff line counts | Show a concise generated summary before raw diff. Label it as a summary, not semantic review. |
| Artifact digest | Proposal `proposal_hash`, `base_file_hash`, and proposal-review `current_base_file_hash` where present | Keep proposal, base, and current artifact digests distinct and in technical details. |
| Time | Proposal `created_at`, `updated_at`, matching approval `expires_at` | Label the object each timestamp belongs to. Do not infer an application timestamp from proposal `updated_at`. |
| Next action | Recorded proposal/approval state and valid pending binding | Link to the existing pending approval controls only for an exact current pending approval; otherwise show review, history, or no-action guidance. |
| Raw change evidence | Proposal detail `unified_diff` | Keep behind a clearly labeled technical disclosure after the operator summary. |

## Existing API Use

- `GET /patch-proposals` supplies the list and safe proposal-review state.
- `GET /patch-proposals/{proposal_id}` supplies the selected unified diff.
- `GET /approvals` supplies read-only approval history; the UI filters exact patch correlations
  using `one_time_scope.proposal_id`.
- `GET /approvals/review?status=pending` remains the source for current actionable binding review.
- Existing `POST /approvals/{approval_id}/approve|deny` actions remain only in the current Pending
  Approvals panel. The artifact lifecycle view does not add a mutation.

The UI must not request unfiltered approval reviews for lifecycle history. Historical/legacy
approval scopes may predate fields required by the current patch binding-review contract. Raw
approval history is safe for read-only state/correlation presentation; only the bounded pending
review request determines whether current approve/deny controls are enabled.

## List and Selection Contract

The proposal list may add client-side search, status filtering, deterministic sorting, and workspace
grouping over the already loaded bounded list. Selection remains keyed by `proposal_id`; filters do
not rewrite, approve, apply, or delete a proposal. Selected detail stays adjacent to the list on wide
screens and follows it on narrow screens.

## Lifecycle Boundaries

- `Proposed` is not approved.
- `Approval required` or `pending` is not approved.
- `Approved` is not necessarily executing or applied.
- `Applied` is not reviewed, promoted, published, or release-ready.
- `Ready for operator review` is presentation guidance for an applied artifact, not a stored state.
- No review-complete mutation exists in the current API, so the UI must not create or imply one.

## Boundary Result

- No new endpoint, field, schema, stored state, mutation, role, permission, or tool is required.
- Tool count remains `24`.
- Command Center remains a presentation and existing-API client.
- Gateway remains authoritative for proposal, approval, application, and audit records.

Stop if implementation requires exposing the proposal's stored principal through an API change,
inventing an application timestamp, adding review/promotion state, broadening write scope, or
changing approval semantics.

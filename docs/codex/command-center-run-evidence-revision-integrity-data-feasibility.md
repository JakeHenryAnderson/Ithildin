# Command Center Run-Evidence Revision Integrity Feasibility Map

Status: approved bounded UI integrity contract using existing read-only responses.

Current governed tool count: `24`.

## Operator Risk

Command Center loads selected run detail and its redacted evidence export with separate requests. A
run can change between those requests. Showing both responses without comparing their revision
fields can make a generated snapshot appear to describe the currently selected detail when it is
older, newer, or otherwise different.

## Existing Authoritative Data

The existing run-detail response and existing `/runs/{run_id}/evidence-export` response both expose:

- run, principal, workspace, and session identity;
- recorded status and tool-call count;
- creation and update timestamps;
- latest policy hash and manifest-lock hash.

The evidence response also already exposes SHA-256 digests for its run, timeline, approvals, and
patch-diagnostic sections. No new endpoint, field, schema, storage, or tool is required.

## Frozen Comparison Contract

Command Center compares the selected detail with the generated snapshot across `run_id`,
`principal_id`, `workspace_id`, `session_id`, `status`, `tool_call_count`, `created_at`, `updated_at`,
`policy_hash`, and `manifest_lock_hash`.

- Exact equality is labeled `Matches generated snapshot`.
- Any missing or different value is labeled `Mismatch - reload before handoff`.
- A mismatch never rewrites either record or implies which response is newer.
- Snapshot loading failure remains `Unavailable`; it is not a match or an empty record.

The technical closeout exposes the existing full section digests so a reviewer can identify the
exact generated sections. Displaying a digest does not verify later custody, receipt, signature,
independent attestation, or endpoint completeness.

## Explicit Non-Approvals

This slice adds no mission dispatch, runner control, Node action, endpoint query, signing behavior,
custody system, storage, API, governed tool, production identity, SIEM adapter, or compliance claim.
It does not prove runner/model enforcement, off-Gateway activity, filesystem isolation, or that a
downloaded file remains unchanged.

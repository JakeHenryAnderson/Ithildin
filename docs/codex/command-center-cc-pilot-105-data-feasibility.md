# CC-PILOT-105 Authoritative Data Feasibility Map

Status: preimplementation review for `CC-PILOT-105`; the existing bounded run query and recent
audit window support an explicitly observed investigation slice without new telemetry or schema.

This map does not approve run control, anomaly detection, process/model telemetry, off-platform
activity claims, new run fields, or an expanded API query contract.

## Reviewed Slice

`CC-PILOT-105` adds investigator-oriented filtering and deterministic grouping before the selected
run timeline. Server-supported filters remain authoritative query inputs; additional filters are
client-side presentation over the loaded 25-run and 100-recent-audit-event windows.

## Filter Map

| Investigator filter | Existing source | Scope/limitation |
| --- | --- | --- |
| Identity | `GET /runs` `principal_id` query | Existing bounded server filter. |
| Workspace | `workspace_id` query | Existing bounded server filter. |
| Tool | `tool_name` query | Existing bounded server filter based on run records. |
| Run status | `status` query | Existing bounded server filter; not a process-control state. |
| Time | Run `updated_at` | Client-side over loaded runs; labels use last recorded update, not mission start/end. |
| Mission context | Safe run metadata plus existing presentation label | `Guided local demo mission` or `<workspace> mediated run` is presentation context, not stored mission authority. |
| Decision | Recent loaded audit events correlated by `metadata.run_id` | `Observed in recent audit window`; absence means not observed in the loaded window, not that the run had no such decision. |
| Outcome | Recent correlated `tool.execution.completed|failed|started` events | Presentation over recent loaded events only. No external process or model outcome is claimed. |
| Attention | Recent correlated failure, denial, or approval-required decision | Deterministic observed-attention grouping, not anomaly detection, risk scoring, or incident declaration. |

## Interaction Contract

- All values remain labeled.
- Active server and client filters appear as individually removable chips.
- `Clear all` resets both filter sets and reloads the bounded unfiltered run query.
- Empty state names that no loaded runs match and reminds the investigator of the bounded window.
- Selection remains keyed by `run_id`; filtering does not mutate or control a run.
- Group summaries state `shown of loaded` and trace observed decision/outcome/attention counts to the
  recent audit-event window.
- The full selected timeline and machine IDs remain in the existing Workbench detail.

## Boundary Result

- No endpoint, query parameter, schema field, telemetry source, state, mutation, or tool is required.
- Tool count remains `24`.
- Server filters remain limited to the current allowlist and `limit=25`.
- Client observation uses only the currently loaded `limit=100` audit events.

Stop if implementation requires N-plus-one run enrichment, unbounded history, new API filters,
model/process telemetry, inferred anomaly/risk scoring, or off-platform activity claims.

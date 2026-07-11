# CC-PILOT-104 Authoritative Data Feasibility Map

Status: preimplementation review for `CC-PILOT-104`; existing read-only run evidence, audit
verification, system signing status, and export APIs support a bounded mission closeout.

This map does not approve audit mutation, custody/immutability claims, SIEM behavior, expanded
export contents, compliance claims, or public security-product positioning.

## Reviewed Slice

`CC-PILOT-104` gives an operator a concise selected-run closeout before technical telemetry and
keeps five states separate: recorded run evidence, evidence completeness, audit-chain verification,
signing availability/reference, and browser export response.

## Field Map

| Closeout question | Existing source | Presentation rule |
| --- | --- | --- |
| What run is in scope? | Selected Agent Run plus `GET /runs/{run_id}/evidence-export` `run` and `summary` | Name the run, requesting identity, workspace, session, and tool-call count. Never imply activity outside this run or outside Ithildin. |
| What decisions were recorded? | Evidence-export `summary.decision_counts` and safe timeline categories/statuses | Summarize counts; retain request/event details in technical drill-down. |
| What approval/application evidence exists? | Redacted evidence-export approvals and timeline; patch diagnostics | Count correlated records. Keep approval, execution/application, and artifact review distinct. |
| Is the evidence complete? | Evidence-export `warning_count`, `warnings`, timeline limit warnings, missing policy/manifest/signing warnings | Use `no reported bundle warnings` only when warning count is zero. Never label the evidence complete merely because the request succeeded. |
| Is the audit chain verified? | Existing `GET /audit-events/verify` | Say `Audit chain verified for the currently loaded local audit chain` only when `valid` is true. Show failure/unavailable separately. This does not prove host-compromise resistance. |
| Is evidence signed? | System `audit_signing.signed_export_available`; run export `signed_export_references` | Signing capability is not a signed run snapshot. Empty references mean no signed evidence reference is included. Command Center does not independently verify a downloaded signature in this slice. |
| Was an export created? | Existing run/audit export response plus ephemeral browser-session result | `Download initiated` means a response was prepared and browser download was requested; it does not prove save location, custody, retention, receipt, or later integrity. Failures remain explicit. |
| What was redacted/excluded? | Evidence-export `redaction_summary.excluded_categories` | Show exclusions before download so the operator knows prompts, raw arguments, contents, diffs, response bodies, secrets, and sensitive paths are not in the run snapshot. |
| What technical evidence is available? | Export ID/time, evidence hashes, policy/manifest hashes, safe timeline, approvals, diagnostics, warnings | Keep under disclosure after the routine closeout. Do not expose omitted raw sensitive fields. |

## Existing API Use

- `GET /runs/{run_id}` remains the selected Workbench timeline.
- `GET /runs/{run_id}/evidence-export` supplies a read-only generated, redacted closeout snapshot.
- `GET /audit-events/verify` remains the global local audit-chain verification result.
- `GET /audit-events/export` and `/signed` remain existing bounded download actions.

Generating a run evidence snapshot creates an ephemeral response identifier/time but does not mutate
approval, policy, execution, or audit state. The UI must label it as a generated snapshot, not a
persisted export record.

## State Separation

- Recorded events are not evidence completeness.
- Zero bundle warnings is not proof that all external activity is represented.
- A valid local hash chain is not host-compromise resistance, immutable custody, or independent
  attestation.
- Signing configured/available is not the same as this run snapshot being signed.
- A signed export response is not signature verification by Command Center.
- A browser download initiation is not proof of file custody, receipt, retention, or future
  integrity.
- `completed` applies only to a named recorded tool execution, never the mission, review, release,
  or enterprise readiness.

## Boundary Result

- No new endpoint, export field, schema, state, mutation, permission, or tool is required.
- Tool count remains `24`.
- The closeout is presentation over existing safe records and download responses.
- Gateway remains authoritative for audit, signing, export generation, and redaction behavior.

Stop if implementation requires new export content, audit writes, signature/custody claims,
off-platform activity claims, SIEM delivery, or a persisted review/closeout state.

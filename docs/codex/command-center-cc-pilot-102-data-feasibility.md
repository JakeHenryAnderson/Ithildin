# CC-PILOT-102 Authoritative Data Feasibility Map

Status: preimplementation review for `CC-PILOT-102`; current records and APIs support a contextual
governed-request explanation without a new runtime contract.

This map does not approve policy, approval, audit, schema, API, or governed-power changes.

## Reviewed Slice

`CC-PILOT-102` explains one recorded request inside the selected Agent Run Workbench and reframes the
existing policy preview as a contextual, explicitly non-mutating request decision preflight.

## Field Map

| Operator question | Existing source | Presentation rule |
| --- | --- | --- |
| What did the agent request? | Selected run timeline `request_id`, `tool_name`, safe `resource`, plus Agent Run identity/workspace | Show safe summary only. Raw arguments are intentionally unavailable and must not be reconstructed. |
| What did Ithildin decide? | Timeline `decision` on the correlated policy event | Map `allow`, `deny`, and `require_approval` to plain language while retaining the machine value. |
| Why? | Matching pending approval `metadata.policy_reason`; otherwise safe timeline metadata `policy_reason` or `reason` | If absent, say the reason is not present in correlated evidence. Never infer it from the tool class. |
| What happened next? | Correlated timeline executor/tool lifecycle events | Keep policy decision separate from execution result. A policy allow is not execution success. |
| Is human action required? | Recorded decision plus exact matching pending approval/binding review | Only show a pending review action when the existing approval review endpoint supplies it. |
| What evidence is available? | Request ID, run policy hash, tool manifest hash, matched-rule metadata where present, event hash, approval binding fields | Put machine evidence in technical drill-down after the operator explanation. |
| Is the tool registered? | Existing `GET /tools` response | State that registration identifies a reviewed tool definition and never implies effective permission. |
| Who and where? | Agent Run `principal_id`, `principal_type`, roles, and `workspace_id` | Label as requesting identity and governed workspace. Do not imply production IAM or process ownership. |

## Decision and Consequence Mapping

| Machine decision | Operator label | Consequence rule |
| --- | --- | --- |
| `allow` | Allowed | Policy allowed the request; show the separately recorded execution state or say it is unavailable. |
| `deny` | Denied | Gateway blocked the governed request; no governed execution should follow that decision. |
| `require_approval` | Approval required | The exact request requires approval. Show `Review pending approval` only when a matching valid pending approval is loaded. |
| missing/other | Decision unavailable / recorded value | Preserve the machine value and avoid a success or failure inference. |

## Contextual Preflight

The existing `POST /policy/preview` endpoint is sufficient. The UI will rename the surface to
**Request Decision Preflight** and state that it:

- evaluates a new hypothetical request against current policy;
- does not execute the tool;
- does not create an approval;
- does not apply or change policy;
- does not replay or reconstruct the selected recorded request;
- keeps raw JSON input as an Administration/policy-troubleshooting function.

Selected Workbench request metadata may be shown as troubleshooting context, but raw arguments are
not present in the safe run evidence and will not be invented or copied into the preflight.

## Boundary Result

- Current API calls remain unchanged.
- No new field, endpoint, stored state, mutation, role, or permission is required.
- Tool count remains `24`.
- Command Center remains a presentation and existing-API client.
- Gateway remains authoritative for the recorded decision and consequence.

Stop if implementation requires raw arguments, a missing policy reason to be inferred, historical
approval reconstruction from incomplete evidence, a new endpoint, or any policy/approval mutation.

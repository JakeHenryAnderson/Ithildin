# CC-PILOT-106 Authoritative Data Feasibility Map

Status: preimplementation review for `CC-PILOT-106`; existing UI state and panels support
presentation lenses without new authorization or runtime behavior.

This map does not approve roles, permissions, authentication changes, policy/export behavior,
configuration mutation, accessibility claims, or new routes/APIs.

## Reviewed Slice

`CC-PILOT-106` adds four explicit presentation lenses over the existing single-page Command Center:
Routine operations, Investigation, Policy administration, and Technical review.

## Surface Map

| Existing surface | Routine | Investigation | Policy administration | Technical review |
| --- | --- | --- | --- | --- |
| Attention, approvals, artifacts, selected Workbench | default | retained | retained as context | retained as context |
| Advanced bounded run filters | hidden | default-visible | hidden | optional context only |
| System trust and registered tools | hidden from routine path | hidden | visible | visible |
| Request Decision Preflight and Candidate Policy Impact | hidden | hidden | visible | hidden |
| Global audit integrity/export controls | closeout remains in selected run | closeout remains | hidden | visible |
| Raw recent audit-event table | hidden | hidden behind selected timeline | hidden | visible |

## Interaction and Authority Contract

- The selected lens is local React presentation state only and is not stored or sent to Gateway.
- Lens names describe intended work, not authenticated roles or effective authorization.
- Existing API calls may remain loaded for responsive switching; hiding a panel does not change
  Gateway permissions or create a security boundary.
- Routine Operations is the default and keeps specialist YAML, raw inventory, raw audit, global
  signing/export, and configuration diagnostics out of the normal path.
- The Administration navigation action opens Policy Administration; the lens switcher provides all
  four views.
- Existing action controls retain their current API checks and disabled states.

## Boundary Result

- No new route, endpoint, role, permission, state, mutation, or tool is required.
- Tool count remains `24`.
- Lens state is reversible presentation only.
- Gateway remains the enforcement and authorization authority.

Stop if implementation requires role inference, access-control claims, API changes, duplicated
mutations, hidden-state security assumptions, or removal of required technical evidence.

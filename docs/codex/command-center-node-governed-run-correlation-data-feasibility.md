# Command Center Node Governed-Run Correlation Feasibility

Status: approved preimplementation map for the bounded Node-to-Agent-Run cockpit slice.

Current governed tool count: `24`.

## Operator Problem

The Gateway can now mediate an existing read-only tool call from an authenticated Node, but the
resulting Agent Run still looks like generic recorded ingress in Command Center. That loses an
important authority distinction: the Node identity and workspace were derived by the Gateway,
while the runner label is correlation supplied by the external client.

This slice makes that distinction durable and visible. It does not create a mission, dispatch an
agent, control a runner, inspect a model, or broaden Node authority.

## Authoritative Correlation

For a governed Node read that reaches the existing Agent Run pipeline, the Gateway may attach only
server-known provenance to the already-created run identified by the exact tuple of:

- Gateway-derived Node principal;
- Gateway-constructed configuration-bound session namespace; and
- enrolled workspace.

The stored provenance is limited to the ingress kind, identity source, Node ID and display name,
read-only authorization profile, exact configuration generation and digest, and explicit false
claims for offline fallback and runner enforcement. The runner session label remains reported
correlation and never becomes identity or mission authority.

No new table, endpoint, query parameter, role, permission, policy rule, executor, or governed tool
is required. Existing Agent Run `metadata_json` is the persistence boundary.

## Command Center Contract

- Node-originated runs say `Gateway-derived Node identity`, not `Reported identity`.
- The mission-facing label identifies a governed Node session without claiming an orchestrated job.
- The selected Workbench shows the exact Node, configuration generation, read-only profile,
  fail-closed offline posture, and the explicit absence of runner enforcement.
- A Node fleet record can open the existing Agent Runs surface with exact principal and workspace
  filters. This is navigation over loaded Gateway records, not Node contact or lifecycle control.
- Run evidence export includes the bounded origin object and its non-claims.
- Generic MCP and guided-demo runs preserve their existing presentation.

## Stop Conditions

Stop if implementation requires mission creation, launch/pause/abort/retry controls, Node writes or
network access, runner or model telemetry, inferred endpoint health, new API filters, a new
governed tool, or any claim that all runner activity passes through Ithildin.

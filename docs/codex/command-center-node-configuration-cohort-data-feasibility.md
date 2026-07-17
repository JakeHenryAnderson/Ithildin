# Command Center Node Configuration Cohort Feasibility Map

Status: approved bounded Command Center aggregation over the existing Node inventory response.

Current governed tool count: `24`.

## Operator Gap

The Nodes surface exposes exact per-Node desired configuration, storage acknowledgment, version,
and accepted-heartbeat posture. At fleet scale, however, an operator should not have to open every
record to determine which loaded Nodes share a desired signed generation or where a rollout has
storage drift, version exceptions, or missing connectivity evidence.

## Existing Authoritative Data

No new API, schema, store, or Node request is required. The existing bounded `GET /nodes` response
provides, for each loaded record:

- Gateway enrollment status, workspace, and Node identity;
- desired configuration generation and digest, plus the Gateway's current configuration signing
  key as a separate trust-posture field;
- Node-reported stored generation/digest and the derived configuration state;
- desired-versus-observed Node version posture; and
- Gateway-accepted heartbeat posture.

Command Center groups currently enrolled records by exact workspace, desired generation, desired
digest, and the current Gateway configuration signing-key field. The signer field does not prove
which historical key signed a desired generation. Revoked records remain visible in inventory and
fleet counts, but are excluded from active rollout cohorts.

## Presentation Contract

Each cohort shows:

- enrolled Node count;
- exact-current storage acknowledgments versus cohort size;
- Nodes awaiting storage acknowledgment;
- configuration-drift count;
- version-exception count; and
- recently accepted heartbeat count versus cohort size.

The deterministic order is: configuration drift or incomplete evidence; storage pending or
unassigned desired state; version/connectivity exceptions; then fully stored-current cohorts.
Workspace and newest desired generation provide stable tie-breakers.

`Stored current not enforced` means the Node attested that it stored the exact Gateway desired
generation and digest. It never means that the Node applied or enforces the configuration. All
counts describe only the bounded records loaded from the current Gateway response. They are not
organization discovery, endpoint inventory, deployment execution, rollout control, or monitoring.

## Non-Claims

This slice does not contact a Node, distribute configuration, change desired state, acknowledge an
exception, start a rollout, retry a failed Node, verify package authenticity, prove runner/model
health, prove host isolation, prove configuration enforcement, or add group assignment. It adds no
endpoint, schema, persistence, governed tool, Node authority, host write, orchestration, telemetry,
SIEM behavior, production identity, or enterprise/security-product claim.

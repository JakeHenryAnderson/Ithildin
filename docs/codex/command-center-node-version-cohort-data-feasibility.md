# Command Center Node Software Version Cohort Feasibility Map

Status: approved bounded Command Center aggregation over the existing Node inventory response.

Current governed tool count: `24`.

## Operator Gap

The Nodes surface exposes each enrolled Node's desired minimum software version and the last
software version reported in an accepted signed heartbeat. At fleet scale, an operator should not
have to open every record to find below-minimum Nodes, missing version evidence, or groups that
share the same desired-versus-observed version posture.

## Existing Authoritative Data

No new API, schema, store, Node request, package channel, or lifecycle authority is required. The
existing bounded `GET /nodes` response provides, for each loaded record:

- Gateway enrollment status, workspace, and Node identity;
- the minimum Node version from signed desired configuration;
- the last Node version reported in a Gateway-accepted signed heartbeat;
- the Gateway-derived desired-versus-observed version posture; and
- accepted-heartbeat recency posture.

Command Center groups currently enrolled records by exact workspace, desired minimum version, and
last observed version. Revoked records remain visible in inventory and fleet counts, but are
excluded from active software-version cohorts.

## Presentation Contract

Each cohort shows its enrolled Node count, desired minimum version, exact-version observation,
meets-minimum count, below-minimum count, never-observed count, and recently accepted heartbeat
count. Below-minimum cohorts sort first, followed by missing desired or observed evidence, stale
connectivity evidence, and cohorts whose loaded records meet the desired minimum. Workspace,
minimum version, and observed version provide stable tie-breakers.

An operator may scope the loaded inventory to the exact cohort key from the same response.
Selecting a software-version cohort clears free-text and posture filters, applies its workspace,
returns ordering to attention-first, replaces any configuration-cohort scope, and selects the first
matching loaded record. Selecting a configuration cohort similarly replaces software-version
scope. A dashboard refresh clears both scopes before loading a new response.

All counts describe only loaded Gateway records. Version strings are compared by authoritative
Gateway posture supplied in the response; Command Center does not independently parse versions or
infer upgrade safety.

## Non-Claims

An observed version is Node-attested heartbeat content accepted by the Gateway. It is not package
authenticity, an installed-artifact measurement, SBOM or vulnerability posture, process health,
runner health, host health, or proof that the reported binary is executing. A desired minimum does
not establish package availability, update compatibility, deployment readiness, or rollback
safety.

This slice does not download, stage, install, execute, retry, schedule, approve, or roll back an
update. It adds no self-update, update ring, deployment group, package repository, endpoint,
schema, persistence, governed tool, Node authority, orchestration, telemetry, SIEM behavior,
production identity, or enterprise/security-product claim. Cohort selection is temporary browser
presentation state, not a rollout target, authorization scope, policy assignment, or durable fleet
group. Maintenance remains operator managed.

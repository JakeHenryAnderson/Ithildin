# Track B Node Manual Rollback Capability Decision

Status: **approved for manual, one-Node-at-a-time rollback by fresh signed generation**.
Automatic rollback, group rollout, and runner enforcement remain unapproved.

Decision date: 2026-07-16

Decision authority: the project owner authorized autonomous project-related evolution toward an
enterprise governance plane. This separate decision narrows that authority into a reviewable
configuration-recovery primitive and does not rewrite or close historical `external_pending` rows.

Current governed tool count: `24`.

## Approved Slice

- An authenticated administrator may inspect immutable configuration history for one Node.
- The administrator may select an earlier evidence-complete generation and name the exact current
  desired generation that it is intended to replace.
- Ithildin copies the earlier closed configuration payload into a new monotonically increasing
  generation, gives it a new configuration ID and validity window, and signs it with the current
  dedicated Gateway Ed25519 configuration key.
- The signed envelope records `manual_rollback` and the source generation. Audit evidence records
  the source, replaced desired generation, new generation, digest, and that the action was not
  automatic.
- Command Center may expose this one-Node action with explicit confirmation and desired-versus-
  stored drift. This is bounded canary targeting, not group rollout.

## Required Safety Semantics

- An old signature is never reactivated or returned as the new desired state.
- `expected_current_generation` is a mandatory compare-and-set precondition. Concurrent assignment
  causes a conflict with no additional generation.
- The source must belong to the same Node, precede the current desired generation, and have complete
  audit evidence. Revoked Nodes and evidence-incomplete state fail closed.
- Rollback assignment remains unavailable to the Node until its new audit event is durable.
- The resulting Node state is drift or awaiting storage until the Node retrieves, verifies, stores,
  and acknowledges the fresh generation as `stored_not_enforced`.

## Explicitly Not Approved

- automatic rollback, health-triggered rollback, scheduling, waves, groups, labels, percentages, or
  bulk assignment;
- reusing an expired signature or lowering the Node client's monotonic-generation protection;
- Node self-update, package distribution, runner lifecycle control, governed action forwarding, or
  claims that rollback changed runner behavior;
- remote MCP, production identity, TLS/mTLS, hosted fleet management, or a new governed tool.

Tests and observed evidence demonstrate software behavior only. They do not approve production
deployment, automatic remediation, runner enforcement, or compliance claims.

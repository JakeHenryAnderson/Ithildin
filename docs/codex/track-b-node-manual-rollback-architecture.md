# Track B Node Manual Rollback Architecture

Status: approved architecture for the bounded manual rollback slice.

Current governed tool count: `24`.

## State Transition

```text
desired generation N + evidence complete
        |
        | admin selects earlier generation S and asserts expected N
        v
BEGIN IMMEDIATE -> validate Node/source/current -> create generation N+1 pending
        |
        | append node.configuration.rollback_assigned audit event
        v
mark N+1 evidence complete -> Node may retrieve -> store -> acknowledge
```

The source payload is reused; the source envelope and signature are not. Generation `N+1` has a new
ID, timestamps, signature, and signed rollback lineage. The configuration digest may equal source
generation `S` because the closed payload is intentionally identical.

## Concurrency And Failure

- The store uses `BEGIN IMMEDIATE` and verifies both source and expected-current state inside the
  transaction.
- A stale expected generation returns conflict and creates no row.
- Failure before audit completion leaves the new row evidence-incomplete, so retrieval fails closed.
- Restart preserves history, desired state, lineage, and drift in SQLite.
- The Node's existing monotonic verification accepts the fresh higher generation and continues to
  reject regression to the historical source generation.

## Operator Meaning

This is a desired-state recovery action, not an execution rollback. Command Center must say that the
fresh generation is assigned, show whether it is stored, and continue to state that runner health
and policy enforcement are unknown. One-Node selection supports a deliberate canary workflow without
adding automatic staged rollout.

## Non-Claims

No automatic rollback, group targeting, orchestration, self-update, runner control, policy
evaluation at the Node, production identity, or remote fleet security is provided by this slice.

# Enterprise E1 Upgrade, Rollback, and Recovery Contract

Status: `E1-M3` bounded recovery contract. This is single-site engineering evidence, not disaster
recovery, high availability, production durability, or permission to overwrite ambiguous state.

## Supported sequence

1. Require one exact clean Git candidate and immutable candidate archive.
2. Stop the Gateway and Command Center before backup.
3. Snapshot Gateway state and configured workspaces; require manifest equality.
4. Before a schema-changing startup, require the existing private SQLite backup and closed receipt.
5. Start the candidate and require Gateway health, authenticated 24-tool inventory, and Command
   Center HTTP readiness.
6. If startup fails, require the API endpoint to remain unavailable and capture the exact failed
   service/exit observation.
7. Stop only the exact site project, restore the verified backup into new private directories, and
   restart the previously verified images.
8. Preserve the failed-attempt and recovery evidence, then remove only exact synthetic resources.

Schema downgrade is `restore_only`. An incompatible or ambiguous database, source identity,
ownership, backup digest, migration receipt, Node identity, or cleanup target is a stop condition.

## Optional Node continuity

Node state is not silently folded into the Gateway backup. A continuing Node must retain its
Gateway-derived identity, pinned configuration trust, private stored configuration, monotonic
generation, and signed heartbeat/acknowledgment semantics. Gateway restart does not turn
`stored_not_enforced` into enforcement.

After restore, the operator compares authoritative Gateway inventory with the Node-held identity
and configuration. If either side is unavailable, divergent, or ambiguous, the supported action is
revoke and re-enroll through the existing workflow. Ithildin does not overwrite a Node volume,
guess identity continuity, automate source rollback, or claim runner/model-provider recovery.

## Validation

```sh
make enterprise-e1-recovery-check
```

The static gate validates the recovery implementation bindings and focused negative tests. Exact
observed receipts and their nonclaims are recorded separately in
[`enterprise-e1-m3-observed-results.md`](enterprise-e1-m3-observed-results.md).

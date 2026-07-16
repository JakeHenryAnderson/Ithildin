# Track B Node Manual Rollback Observed Results

Status: **observed local-preview POC passed** on 2026-07-16.

Evidence root: ignored local path `var/node-config-rollback-poc-20260716`.

Current governed tool count: `24`.

## Observed Sequence

1. A fresh Gateway generated dedicated audit and Node-configuration Ed25519 keypairs, enrolled one
   synthetic Hermes sidecar Node, assigned generation 1, and accepted the Node's
   `stored_not_enforced` acknowledgment and heartbeat.
2. The Gateway assigned generation 2, producing desired-versus-stored drift.
3. The actual Gateway process stopped and restarted on the same SQLite database and keys. The Node
   retrieved, verified, stored, and acknowledged generation 2 after restart.
4. The administrator read immutable history and requested a manual rollback from generation 2 to
   the payload of generation 1.
5. Ithildin created fresh signed generation 3 with `manual_rollback` lineage. The generation 3
   digest equaled generation 1's configuration digest, but its ID, timestamps, envelope, signature,
   and monotonic generation were new.
6. Inventory showed generation 3 desired and generation 2 stored: `configuration_drift`.
7. Repeating the old compare-and-set request was denied with HTTP `409` and created no generation.
8. The Node retrieved, verified, atomically stored, and acknowledged generation 3. Inventory then
   showed `stored_current_not_enforced` for generation 3.
9. Revocation remained authoritative and denied later configuration retrieval.

## Reproducible Check

```sh
make track-b-node-configuration-evidence-check
```

The checker validates three immutable generations, rollback lineage, expected-current conflict,
drift, storage acknowledgment, restart behavior, revocation, audit events, audit-chain integrity,
mode-0600 private files, absence of private-key material from safe output and audit, and the unchanged
24-tool lock.

## What This Does Not Prove

The POC does not prove runner enforcement, policy evaluation at the Node, runner or model health,
automatic rollback, group rollout, production identity, remote transport security, filesystem
non-bypass, or production readiness. Human UAT was neither requested nor performed.

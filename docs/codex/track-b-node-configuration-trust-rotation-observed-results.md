# Track B Node Configuration Trust Rotation: Observed Results

Status: observed local-preview POC evidence; not production readiness or UAT approval.

Observed on: `2026-07-16`.

Current governed tool count: `24`.

## Accepted Evidence

A fresh loopback Gateway on `127.0.0.1:8013` used dedicated K1 and K2 Ed25519 configuration
signing keypairs, a fresh SQLite database, a fresh signed audit chain, and one newly enrolled
synthetic Hermes Node. The ignored evidence root is
`var/node-config-poc-trust-rotation-20260716/` and can be checked without printing enrollment or
private-key material:

```sh
make track-b-node-configuration-trust-rotation-evidence-check
```

The observed run established:

- K1 created one target-bound transition to K2, after which the Node verified it using pinned K1,
  atomically staged K2 in its mode-`0600` state file, and acknowledged `staged_not_active`;
- the K1 Gateway process stopped and a new Gateway process started on K2 against the same durable
  database and audit log;
- a higher K2-signed configuration caused the Node to promote K2 only after full configuration
  verification and storage;
- the Node retained K1 as recovery-only trust with the signed overlap cutoff;
- the K2 Gateway stopped and a new Gateway process started on K1 during the overlap;
- the Node verified and stored a higher K1-signed recovery configuration without demoting K2;
- the acknowledgment separately recorded the configuration verification signer K1 and active Node
  trust K2, so fleet posture remained `active_not_enforced` after recovery;
- generations 1, 2, and 3 persisted with signer sequence K1, K2, K1 and complete audit evidence;
- transition assignment, retrieval, and acknowledgment events and all three configuration lifecycle
  event sets were present in a valid audit chain;
- private files were mode `0600`, private material was absent from safe evidence and audit, and the
  manifest remained at 24 governed tools.

Focused automated tests additionally reject wrong current/target keys, tampering, unknown signed
fields, expiry, replay, revoked Nodes, incomplete audit evidence, arbitrary active-key claims, and
unannounced configuration signers. They also cover restart persistence and prove that previous-key
recovery cannot silently change active trust. Tests are evidence, not permission or release approval.

## Claim Boundary

The accepted claim is limited to manual, per-Node, restart-based configuration signing-trust
rotation and time-bounded recovery in a local-preview environment. `active_not_enforced` means the
Node's signed acknowledgment identifies the staged K2 trust as active after verifying and storing a
K2-signed configuration. It does not mean Hermes or another runner enforced that configuration.

This result does not establish automatic fleet rotation, private-key distribution, certificate or
production PKI, HSM/KMS custody, unattended disaster recovery, runner enforcement, production
identity, remote transport, production storage or telemetry, enterprise readiness, release
approval, or operator UAT acceptance.

## Reproduction Shape

The three-phase live driver is `scripts/node_configuration_trust_rotation_poc.py`. Run `stage-k2`
with a K1 Gateway, explicitly stop/start the Gateway on K2 and run `activate-k2`, then explicitly
stop/start it on K1 during overlap and run `recover-k1`. The checker independently reads persisted
state, signer sequence, transition records, file modes, safe evidence, tool count, and the audit
chain after all Gateway processes have stopped.

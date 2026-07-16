# Track B Ithildin Node Observed Results

Status: the limited local-preview enrollment and identity slice passed its synthetic observed POC on
2026-07-16. This is not approval for Node-carried tool execution, remote MCP, production identity,
filesystem non-bypass, runner lifecycle, or public security-product claims.

Current governed tool count: `24`.

## Observed Topology

- Gateway: real FastAPI process bound to `127.0.0.1:8011`.
- Storage and audit: isolated ignored SQLite and JSONL under `var/node-poc-20260716/`.
- Client: the packaged `ithildin_node` CLI and client library.
- Key: client-generated Ed25519 key stored in an exclusive mode-`0600` local state file.
- Data: synthetic labels and digests only.

## Accepted Evidence

1. An authenticated administrator issued one short-lived enrollment code; SQLite stored only its
   digest and the code was returned once.
2. The Node enrolled with a raw Ed25519 public key. The Gateway assigned the Node ID, principal ID,
   and workspace; the client could not select those identities.
3. A signed heartbeat was accepted and displayed as `observed_connected`.
4. A second signed heartbeat using a fixed nonce was accepted once; replaying the same signed
   request was rejected with HTTP 401.
5. The Gateway process was stopped and restarted against the same database and audit log.
6. The same Node state sent a new signed heartbeat after restart and it was accepted.
7. An authenticated administrator revoked the Node and the durable inventory reported `revoked`.
8. A new correctly signed heartbeat after revocation was rejected with HTTP 401.
9. The API audit verifier and independent audit-chain verifier passed.
10. Audit and safe output artifacts contained neither the one-time enrollment code nor Node private
    key; the private state file remained mode `0600`.

The deterministic checker reports:

```text
claim_level: authenticated_node_identity_and_connectivity
tool_count_unchanged: true
gateway_derived_identity: true
signed_heartbeat_observed: true
replay_denied: true
restart_heartbeat_observed: true
revocation_persisted: true
post_revocation_denied: true
audit_chain_valid: true
```

## Command Center Result

Command Center now has a dedicated Nodes destination showing durable enrollment, revocation,
recently observed, stale, and never-observed state. It labels identity as Gateway-derived and
connectivity as an accepted-heartbeat observation. It explicitly reports runner and model health as
unknown, exposes audit evidence state, and shows an evidence-incomplete recovery posture when a
mutation cannot be paired with durable audit evidence. It exposes no Node launch, shell, process,
Docker, or tool-execution controls.

The evidence-incomplete behavior is covered by deterministic negative tests. It was not induced in
the live synthetic run above, so the observed POC does not claim an actual audit-write outage.

## Remaining Boundary

- Node heartbeats do not yet carry governed tool calls or mission dispatch.
- HTTP on an approved local-preview host provides no remote transport confidentiality claim.
- The Node does not constrain Hermes filesystem access in this slice.
- Static workspace assignment is bound at enrollment, but dynamic enterprise identity and tenancy
  are not implemented.
- The next slice requires a separate decision for policy/configuration distribution or governed
  request forwarding; this evidence does not grant it.

## Reproduction And Safe Verification

The raw ignored fixture includes an enrollment response containing a short-lived synthetic secret
and a private Node state file. Do not publish or commit it. Run only the safe checker output:

```sh
uv run python scripts/node_poc_evidence_check.py
```

Tests and generated evidence remain evidence only. They do not authorize promotion, production use,
external review closure, or expansion of this slice.

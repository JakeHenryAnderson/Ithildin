# Track B Node Governed Access Observed Results

Status: observed local-preview POC passed on 2026-07-17.

Current governed tool count: `24`.

## Observed Sequence

The proof used a fresh SQLite database, dedicated audit and Node-configuration signing keys, the
real FastAPI process on loopback port `8013`, and one synthetic Hermes sidecar identity.

1. An administrator issued a one-time enrollment code and the Gateway derived the Node ID,
   `agent:node.<node_id>` principal, and `default` workspace.
2. The Gateway assigned signed generation 1 with `deny_governed_actions`; the Node retrieved,
   verified, atomically stored, acknowledged `stored_not_enforced`, and reported the exact digest
   in a signed heartbeat.
3. The Node submitted `fs.read` for `demo/README.md` without a workspace argument. The Gateway
   forced `default`, resolved the dedicated `AgentReadOnly` profile, evaluated the existing policy,
   executed the existing read executor, and returned `completed` under the derived Node principal.
4. An `http.fetch` request returned `denied` without reaching network execution. A separately signed
   request attempting workspace `demo` also returned `denied`.
5. The actual Gateway process stopped. A new Node read attempt returned `Gateway is unavailable`;
   evidence recorded no local execution, queue, buffer, or automatic retry.
6. The Gateway restarted on the same database and keys. Reusing the original successful nonce was
   rejected with HTTP 401. A fresh signed read then completed.
7. Audit-chain verification passed after restart. The exact Node principal and configuration-bound
   session namespace were present in audit evidence, while private-key material and raw read content
   were absent from exported POC summaries.

The reproducible local evidence is under ignored path:

```text
var/node-governed-access-poc-20260717/
```

Validate it with:

```sh
make track-b-node-governed-access-evidence-check
```

The checker reports all closed claims true, including 24 unchanged tools, current acknowledged
configuration, reads before and after restart, network/workspace denial, partition failure, durable
replay denial, audit validity, mode-0600 private state, and secret-free evidence.

## What This Proves

This proves one local-preview Node can originate an existing workspace-bound read through
Ithildin's real manifest, principal-risk, resource-scope, policy, audit, redaction, agent-run, and
executor pipeline. Identity and workspace are Gateway-derived; the signed configuration snapshot
is bound into request hashing and correlation; replay survives Gateway restart; partition fails
closed at the Node client.

## What This Does Not Prove

The result does not prove that Hermes enforced the signed configuration, that every Hermes action
must pass through Ithildin, or that filesystem bypass is impossible. It does not grant Node write,
write-proposal, network, approval, shell, process, Docker, Kubernetes, browser, credential, or
arbitrary host authority. It does not establish a Node listener, remote MCP, TLS/mTLS, production
identity/storage, offline operation, fleet-wide rollout, endpoint management, compliance readiness,
UAT acceptance, or public security-product claims.

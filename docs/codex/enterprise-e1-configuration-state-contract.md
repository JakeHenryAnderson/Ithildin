# Enterprise E1 Policy and Node-Configuration State Contract

Status: active `E1-M2` contract. The machine-readable authority is
[`enterprise-e1-configuration-state-contract.json`](enterprise-e1-configuration-state-contract.json).

The existing signed Node configuration is the E1 distribution bundle. Each immutable generation
binds the target Node, principal, workspace, policy version and digest, 24-tool manifest-lock
digest, minimum Node version, allowed read-only risks, offline-deny posture, timestamps, and
expiry. The Gateway signs and selects desired state; the Node can verify, privately store, and
acknowledge it, but cannot choose or broaden it.

Configuration-signing trust rotation remains a separate signed, Node-targeted transition:
staged, Node-acknowledged, then Gateway-activated only after complete evidence. Expiry does not
activate a transition, and rollback still requires a fresh operator-selected transition or
configuration generation.

## State meanings

| State | Authoritative meaning |
| --- | --- |
| `desired` | Latest Gateway-selected, evidence-complete signed generation. |
| `acknowledged` | Node signature attests exact generation/digest storage as `stored_not_enforced`. |
| `stored` | Node atomically persisted the verified bundle mode `0600`; no enforcement claim. |
| `enforced` | One Gateway-governed request passed current generation, digest, policy, manifest, version, workspace, heartbeat, and read-only-profile checks. |
| `stale` | One or more desired/acknowledged/observed/time/policy/manifest/version bindings are no longer current. |
| `rejected` | Verification or Gateway admission failed; no storage acknowledgment or governed action is accepted. |
| `rollback` | An operator compare-and-set creates a new signed monotonic generation from a prior payload. |

These states are intentionally not collapsed. In particular, `stored_not_enforced` never means
runner-wide, model-provider, or host enforcement. The `enforced` state is request-scoped Gateway
admission evidence only.

## Authenticated checkpoint

The contract reuses existing authenticated HTTP routes for admin assignment, observation, history,
and rollback; Node-signed retrieval and acknowledgment; and the existing Node-governed read-only
call route. It adds no MCP tool or host authority.

Validate the contract and the focused authenticated flows from the repository root:

```sh
make enterprise-e1-configuration-check
```

The checkpoint covers signed policy/manifest targeting, private storage semantics, drift,
rejection, trust rotation, manual rollback-as-new-generation, and request-scoped governed
admission. Existing
observed POC results remain supporting lineage; passing tests are not release, production, or UAT
approval.

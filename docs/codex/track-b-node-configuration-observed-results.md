# Track B Node Signed Configuration: Observed Results

Status: observed local-preview POC evidence; not production readiness or UAT approval.

Observed on: `2026-07-16`.

Current governed tool count: `24`.

## Accepted Evidence

A fresh loopback Gateway on `127.0.0.1:8012` used a dedicated Ed25519 configuration-signing
keypair, fresh SQLite database, fresh audit log, and a newly enrolled synthetic Hermes Node. The
ignored evidence root is `var/node-config-poc-20260716/` and can be checked without printing the
enrollment code or private key:

```sh
make track-b-node-configuration-evidence-check
```

The observed run established:

- enrollment pinned the dedicated Gateway configuration key ID/public key and current manifest-lock
  digest into a mode-`0600` Node state file;
- the Gateway created two append-only signed generations with distinct digests and complete audit
  evidence;
- the Node authenticated retrieval, verified the target/signature/digest/manifest/time/generation,
  stored the bundle crash-safely with mode `0600`, and signed `stored_not_enforced` acknowledgments;
- after generation 2 was assigned, inventory reported desired generation 2 and acknowledged
  generation 1 as `configuration_drift`;
- after an actual Gateway stop/start against the same database and keys, the Node retrieved and
  acknowledged generation 2, and inventory reported `stored_current_not_enforced`;
- local tampering of the signed configuration body was rejected;
- revocation survived in the durable record and denied subsequent authenticated configuration
  retrieval;
- all configuration assignment, retrieval, acknowledgment, and heartbeat events were present twice
  in a valid audit chain; and
- the manifest remained at 24 governed tools.

Focused automated tests additionally cover wrong target, signature, expiry, manifest-lock mismatch,
replay, evidence failure, and API conflict behavior. Those tests are evidence, not permission or
production assurance.

## Claim Boundary

The accepted claim is limited to signed configuration distribution and Node-attested storage in a
local-preview environment. `stored_not_enforced` means exactly that the enrolled Node attested that
it stored the verified configuration. It does not prove that Hermes, another runner, or the host
enforced the policy.

This result does not establish:

- configuration or tool-call enforcement at the runner boundary;
- runner health, model health, or chain-of-thought visibility;
- non-bypass on a general-purpose host;
- remote MCP hosting, fleet rollout, group targeting, or self-update;
- production identity, production transport, production storage, or production telemetry; or
- enterprise readiness, release approval, or operator UAT acceptance.

## Reproduction Shape

The two-phase live driver is `scripts/node_configuration_poc.py`. Run `before-restart`, stop and
restart the local Gateway with the same database and signing paths, then run `after-restart`. The
evidence checker independently reads persisted state, generations, file modes, event types, and the
audit chain. It does not depend on the Gateway remaining online.

This document records an implementation-worktree observation. Exact-candidate release and review
gates remain separate and must be run after the implementation is committed.

# Local v1 LV1-004 Failure and Recovery Journey

Status: implementation lane active; no O5 completion, release, or UAT claim.

Current governed tool count: `24`.

## Purpose

`LV1-004` requires one coherent candidate-bound scenario that demonstrates restart continuity,
replay rejection, partition failure, revocation, stale-configuration rejection, and documented
manual rollback. Component tests already cover those mechanisms separately. This journey binds
them into one isolated local Gateway/Node/Mission sequence without adding another runtime or
authority model.

The implementation reuses the reviewed MCC-006 loopback Gateway harness. It uses isolated SQLite,
JSONL audit evidence, generated local signing keys, a synthetic Node, and the existing 24-tool
surface. It starts no Docker service, runner, browser, model provider, external network connection,
or arbitrary host process. The only child service is the fixed loopback Gateway already bounded by
the MCC-006 harness.

## Scenario

On one clean candidate the journey:

1. enrolls and configures one Gateway-derived synthetic Node;
2. admits, claims, and reports one server-owned mission with a correlated governed read;
3. stops the isolated Gateway and proves mediated access fails closed during the partition without
   local fallback, queueing, or automatic retry;
4. restarts the Gateway over the same isolated database and keys, proves mission continuity, and
   rejects a consumed signed nonce;
5. assigns a second configuration, observes drift, and performs a manual rollback to generation
   one by creating fresh signed generation three;
6. rejects both the stale rollback precondition and a stale generation-one acknowledgment;
7. stores and acknowledges generation three as `stored_not_enforced`; and
8. revokes the Node and quarantines its late runner report without advancing Gateway lifecycle.

Gateway truth remains authoritative. Node connectivity, runner-reported state, and model-provider
state remain separate. The scenario does not claim that the runner stopped, that configuration was
enforced on the host, that a provider succeeded, or that activity outside Ithildin was prevented.

## Commands

Run static checks while implementing:

```sh
make local-v1-failure-recovery-static-check
```

The live-local evidence command requires a clean committed candidate:

```sh
make local-v1-failure-recovery-run
```

The command prints the explicit ignored evidence root and checker invocation. Validate only that
selected root against the explicit candidate:

```sh
LOCAL_V1_FAILURE_RECOVERY_EVIDENCE=<printed-root> \
LOCAL_V1_FAILURE_RECOVERY_CANDIDATE=<exact-commit> \
make local-v1-failure-recovery-check
```

The checker never searches for a latest run and never starts a service. A passing check is
candidate-bound evidence only. Closing O5/LV1-004 still requires a separate durable disposition
that binds the selected safe report and keeps release, promotion, production, and UAT false.

## Authority Limits

- The 24-tool surface and governed power classes remain unchanged.
- No Docker, shell tool, browser, Kubernetes, arbitrary HTTP, broad filesystem, or process-control
  capability is added.
- The loopback Gateway child is fixed to the existing MCC-006 harness and isolated state.
- Manual rollback is one Node at a time, requires an exact expected-current generation, and creates
  a fresh signed generation. It is never automatic.
- `stored_not_enforced` remains the only configuration-enforcement claim.
- Tests and generated evidence do not authorize release, promotion, production, credential
  custody, external-system action, or UAT completion.

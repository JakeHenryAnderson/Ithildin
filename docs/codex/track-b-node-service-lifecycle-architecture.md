# Track B Node Service Lifecycle Architecture

Status: approved architecture for the bounded local-preview service lifecycle slice.

Current governed tool count: `24`.

## Cycle And Ordering

```text
load mode-0600 Node identity and optional stored generation
        |
        v
signed pull -> verify immutable configuration and signing trust
        |
        v
persist promoted trust (if any) -> atomically store verified generation
        |
        v
signed stored_not_enforced acknowledgment -> signed heartbeat
        |
        v
wait verified heartbeat interval; on failure use bounded local backoff
```

The service never evaluates the policy, forwards governed actions, launches a runner, or changes
runner state. The Gateway remains authoritative for accepted connectivity, desired generation,
version posture, revocation, audit evidence, and configuration drift. The Node reports only what it
stored and the safe runner label supplied by the operator.

## Restart And Partition Semantics

- A normal service-manager stop sets an in-process stop event and exits without changing identity.
- The service holds a nonblocking local file lease for the lifetime of the loop. A second process
  targeting the same state directory fails closed instead of cloning active use of the identity.
- A crash can occur between any two network or persistence steps. On restart, the service reloads
  the last durable state and repeats idempotent retrieval, storage, acknowledgment, and heartbeat.
- Repeated configuration retrieval may return the current generation. The Node verifies it again;
  it never lowers the stored generation.
- Gateway unavailability cannot produce a connected heartbeat. The service reports
  `degraded_retrying` and uses exponential retry capped by an operator-bounded maximum.
- Gateway restart preserves Node and desired-configuration truth in its existing durable store.
- Revocation remains authoritative: retrieval or heartbeat rejection leaves the service degraded
  and does not trigger re-enrollment, identity replacement, or runner activity.

## Deployment Shape

The optional container is an operator-managed packaging boundary, not an orchestration feature. It
runs the Node module as an unprivileged user with a read-only root and one private named volume for
state. It exposes no listener and receives no access to Docker, host processes, devices, or host
filesystem paths. The operator creates and consumes a one-time enrollment code separately, then
starts the long-running service.

Upgrade and rollback remain external process replacement. The same durable Node volume is reused,
so the server-derived identity remains stable. Ithildin observes only later signed version reports;
it does not select, fetch, verify, install, start, stop, or roll back the artifact.

## Non-Claims

No self-update, binary provenance, service health endpoint, runner health, runner enforcement,
automatic remediation, fleet rollout, production transport, production identity, production
storage, or new governed tool is provided.

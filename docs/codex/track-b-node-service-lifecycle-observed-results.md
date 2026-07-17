# Track B Node Service Lifecycle Observed Results

Status: **observed local-preview Docker POC passed** on 2026-07-16.

Evidence root: ignored local path `var/node-service-lifecycle-poc-20260716`.

Current governed tool count: `24`.

## Observed Sequence

1. A fresh loopback Gateway used a dedicated SQLite database, signed audit chain, and dedicated
   Node-configuration Ed25519 trust root. A synthetic Hermes-labeled Node consumed its one-time
   enrollment code through container stdin and stored its identity in a private Docker volume.
2. The Gateway assigned signed generation 1 with minimum Node version `0.2.0`. An unprivileged,
   read-only-root Node container retrieved, verified, atomically stored, acknowledged
   `stored_not_enforced`, and heartbeated as version `0.1.0`; Gateway posture was `below_minimum`.
3. A long-running container acquired the private service lease and synchronized. A second real
   container targeting the same volume was denied because the identity was already in use. Docker
   then sent the first process SIGTERM, and the service emitted its safe `stopped` posture.
4. The Gateway stopped. A new one-cycle container failed closed with `Gateway is unavailable`,
   exit code 1, bounded retry posture, and no runner or self-update authority.
5. The actual Gateway restarted on the same database and keys. Inventory retained the same
   server-derived Node identity and acknowledged generation 1.
6. A replacement container reusing the same private volume reported `0.2.0`; the Gateway accepted
   the signed heartbeat and derived `meets_minimum`. A later replacement reported `0.1.0`; the
   Gateway derived `below_minimum`, observing an operator-managed rollback without performing it.
7. Final Node status retained the original identity-key fingerprint. State, verified configuration,
   and service lease were all mode `0600`.
8. Revocation became durable and denied a later container cycle with HTTP 401. The audit chain
   remained valid, private signing material was absent from safe evidence and audit, and the
   governed tool count remained 24.

## Reproduce

```sh
make node-service-image
uv run python scripts/node_service_lifecycle_poc.py --replace
make track-b-node-service-lifecycle-evidence-check
```

The `--replace` flag deletes only the selected generated POC evidence root under repository `var/`;
it does not remove user configuration, a production volume, or committed files. The POC removes
its temporary Docker container and named volume on exit.

## Evidence Claim

The highest supported claim is
`operator_managed_node_service_restart_partition_and_identity_continuity`.

This proves local-preview service synchronization, shared-volume identity continuity, duplicate
local-use denial, graceful termination, Gateway partition and restart behavior, signed version
observation, revocation denial, private local file modes, and audit integrity in the observed
fixture.

It does not prove Node self-update, package provenance, automatic upgrade or rollback, runner
execution, runner health, policy enforcement, filesystem non-bypass, production transport,
production identity, production storage, remote fleet management, production readiness, release
approval, or human UAT.

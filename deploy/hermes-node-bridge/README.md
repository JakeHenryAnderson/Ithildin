# Fixed Hermes Node Bridge Profile

Status: implementation candidate only. This profile is not authorized for live execution.

This file is an overlay for the established `deploy/docker-compose.yml` project, default network,
Gateway service, and `ithildin-node-state` volume. It must not be invoked as an independent Compose
project. The profile derives the bridge from the reviewed Hermes OCI index and exposes only the
three fixed no-argument mission affordances over stdio.

The enrolled Node remains UID:GID `10002:10002` and receives supplemental group `20000`. The runner
remains UID:GID `10000:10000` and receives the same supplemental group. The Node creates
`mission-socket/` inside its existing state volume as `10002:20000` mode `0770` and the socket as
mode `0660`. The runner receives only that volume subpath, read-only, at `/run/ithildin-node`; it
does not receive the state-volume root, Node state, or private key. `SO_PEERCRED` UID `10000` plus
the immutable profile digest remains the peer-admission contract. A malicious same-UID process on
the host/container trust boundary remains outside the claim.

The kernel `RLIMIT_FSIZE` ceiling is `16 MiB`. The pinned image must already contain
`/usr/bin/timeout`; its build refuses otherwise. That fixed container-init wrapper bounds the
operator-invoked runner to 900 seconds, then sends `TERM` and, after ten seconds, `KILL`. It is not
an Ithildin runner lifecycle API.

The operator remains responsible for build selection, startup, teardown, container absence, and
rollback. Ithildin does not start, stop, kill, update, retry, or inspect Hermes. A failed or
ambiguous run must be torn down and its tmpfs destroyed before any separately authorized retry.

`profile.json` is the immutable semantic profile. Its canonical-JSON SHA-256 must equal the
`FIXED_PROFILE_DIGEST` constants in both bridge modules before an implementation candidate may be
reviewed. Live Docker, Hermes, provider, and O4 evidence execution require a later, separate
authorization.

The eventual separately authorized operator sequence must use both files and create the socket
subdirectory before the runner mount is resolved:

```sh
docker compose -f deploy/docker-compose.yml -f deploy/hermes-node-bridge/compose.yaml \
  --profile node up -d --wait ithildin-api ithildin-node
docker compose -f deploy/docker-compose.yml -f deploy/hermes-node-bridge/compose.yaml \
  --profile hermes-node-bridge run --rm hermes
```

These commands are documented topology only and are not part of an automatic check or current live
authority.

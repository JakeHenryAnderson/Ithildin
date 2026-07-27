# Local v1 LV1-006 Operations Contract

Status: implementation and evidence contract; no release or UAT authority.

This milestone closes the supported local topology around two outcomes:

- `O1`: initialize isolated local state, start Gateway and Command Center, verify both, and stop
  cleanly.
- `O7`: stop before backup, snapshot Gateway state and configured workspaces, attempt a fixed
  failing service update, restore into a new state directory, verify recovery, and clean up only
  the isolated rehearsal resources.

## Operator path

Normal use remains the documented Compose path in `deploy/README.md`. The rehearsal is a separate
candidate-bound evidence command:

```sh
make local-v1-operations-run
# Run the exact checker command printed by the rehearsal:
make local-v1-operations-check \
  LOCAL_V1_OPERATIONS_REPORT=var/local-v1-operations/<run-id>/local-v1-operations.json \
  LOCAL_V1_OPERATIONS_CANDIDATE=<40-lowercase-hex-commit>
```

The run refuses a dirty candidate, occupied or non-loopback ports, missing Docker Compose, symlinked
evidence paths, existing copy destinations, any pre-existing exact project/image target, and any
backup/restore manifest mismatch. It creates a unique Compose project and unique image tags, builds
and mounts tracked inputs only from an immutable archive of the recorded Git candidate, uses a
process-memory admin token, mounts no Docker socket, and uses only synthetic state below its private
ignored run root.

The first start builds the exact candidate, verifies Gateway health, verifies the authenticated
24-tool inventory, verifies Command Center HTTP, and stops before backup. The fixed failed update
changes only the known API container command to exit 23; the exact service must be observed exited
with code 23 and the endpoint must be unavailable. Recovery copies
the stopped backup into new state and workspace directories, restarts the original exact images,
and repeats the health checks. Successful cleanup removes the exact Compose project, unique images,
private Compose files, token-bearing runtime state, backup, and restored copy before writing one
mode-`0600` safe report.

## Supported ownership and rollback boundary

For Local v1.0 the operator owns:

- `.env` and local credentials;
- `var/` Gateway database, audit log, local keys, and ignored evidence;
- configured `workspaces/`;
- Docker Desktop/Engine and the local Compose lifecycle.

The optional Node state is not included in the Gateway backup. After restoring Gateway state, the
operator must inspect the authoritative Node inventory and use the existing revoke/re-enroll
procedure when Node identity or local state is ambiguous. The rehearsal does not automate source
checkout, Git rollback, credential restore, Node-volume replacement, or external data recovery.

This is synthetic local evidence, not production durability, disaster-recovery certification,
custody proof, release acceptance, or human UAT. It grants no arbitrary host control, production,
promotion, release, external-system, new-tool, or new-power authority.

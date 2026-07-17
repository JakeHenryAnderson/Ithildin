# Track B Node Version Posture Architecture

Status: approved architecture for bounded local-preview implementation.

Current governed tool count: `24`.

## Truth Sources

```text
signed desired configuration -> minimum_node_version
Node-signed heartbeat        -> last_observed_node_version
Gateway stored records       -> version_posture
Command Center               -> display only
operator/service manager     -> all install, restart, and rollback activity
```

The enrollment descriptor is historical enrollment evidence. It is not the current version source
after a heartbeat has been accepted. The Gateway persists the heartbeat's `node_version` in the same
transaction as nonce consumption and the other safe heartbeat fields. Replay, invalid signature,
clock-skew, revocation, or incomplete evidence rejection therefore cannot change version posture.

## Closed Version Contract

`MAJOR.MINOR.PATCH` is parsed as three base-10 integers. Leading zeroes are rejected except for the
single digit `0`. Components are bounded to 32-bit unsigned integers. Comparison is lexicographic
over the integer tuple. This avoids dependency-specific ordering, ranges, prerelease ambiguity, and
string comparison.

Legacy persisted labels that do not satisfy the grammar are not silently ordered. They produce
`evidence_incomplete` until replaced by valid signed input or handled by an explicit recovery path.

## Posture State Machine

Evaluation order is fail-closed:

1. `revoked` when the durable Node administrative state is revoked;
2. `evidence_incomplete` when Node or desired-configuration evidence is pending, or a persisted
   source version cannot be validated;
3. `unassigned` when no desired configuration exists;
4. `never_observed` when a desired minimum exists but no accepted heartbeat version exists;
5. `below_minimum` when the observed tuple is lower than the desired minimum;
6. `meets_minimum` otherwise.

`meets_minimum` is a narrow version-number comparison. It does not prove package authenticity,
installation success, process health, runner health, policy enforcement, or vulnerability status.

## Restart And Observation

Gateway restart preserves the latest observed version and desired generation. A later accepted
heartbeat may move posture in either direction. A higher report can represent an operator-managed
upgrade; a lower report can represent an operator-managed software rollback. Ithildin records the
observation through the existing heartbeat audit lifecycle but does not claim the cause or perform
the maintenance action.

## Boundary

This architecture adds no self-update endpoint, package registry, downloader, installer, command
execution, service control, group rollout, or runner lifecycle authority. The governed tool count
remains `24`.


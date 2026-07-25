# Local v1 LV1-003 O4 Compose Repair Exact Review

Status: `GO`

An independent Sol xhigh read-only review examined exact candidate
`7e6eb9f0fcad35016f611096543fa4a81017259c`, tree
`fef080b85db9b44675150954d6af5afd5d6fec0d`.

## Exact Scope

The candidate changes exactly these five paths:

1. `deploy/docker-compose.yml`
2. `deploy/hermes-node-bridge/compose.yaml`
3. `scripts/local_v1_lv1_003_o4_producer.py`
4. `tests/test_local_v1_lv1_003_o4_producer.py`
5. `tests/test_node_fixed_runner_bridge.py`

The base `ithildin-node` service now owns exactly one bounded owner-only declaration:

```text
/tmp:size=16m,mode=0700,uid=10002,gid=10002
```

The fixed overlay no longer duplicates the Node `/tmp` target. The producer rejects a merged Node
configuration unless that exact singleton survives. The review also covered the focused negative
test, read-only base and base-plus-overlay Compose config validation, unchanged API/UI/Hermes tmpfs
behavior, the retained Attempt 002 evidence boundary, and the unchanged 24-tool/no-new-powers
boundary.

The repaired source digests are:

- base Compose:
  `sha256:895107a268169790024c07fe00556fb5d6df0ce4479f49cbe091ccfc517ceb04`
- fixed overlay:
  `sha256:f6a78f705165354e9908c4512ab551f87dd16cada6e415d59979d78d6f66107c`
- producer:
  `sha256:b4d44f09183fca2df5cab33496571c3ac316420074e8eeba71e506fd92999c4b`

## Findings

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The exact-commit disposition is `GO`. This review permits the accompanying closed Attempt 003
control disposition to derive one exact immediate child of the reviewed repair commit. The review
does not itself execute Attempt 003 and does not authorize retry, release, promotion, production,
UAT, new governed tools or powers, arbitrary host control, shell execution, or Docker-socket
access.

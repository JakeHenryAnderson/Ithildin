# Local v1 LV1-003 O4 Attempt 012 Disposition

Status:
`ATTEMPT_012_CONSUMED_FIXED_NODE_EXITED_NONCANONICAL_CLEANUP_COMPLETE_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-012` consumed its single execution budget on exact reviewed candidate
`7585e401003df796b5a2c7d7b3bc952aaa693fc3`, tree
`86321cd58fcab1b8f3879700deaad366d2f3fc14`. Annotated review tag
`ithildin/lv1-003-o4-attempt012-reviewed` resolves to that exact commit and tree.

The central-manager supervised operator command was
`make local-v1-lv1-003-o4-producer-run`, using exact module command
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
The fresh private run and its privately derived Compose project are bound only by the
domain-separated digests
`sha256:d04d1657d8b576efe73e9616053df7e601fc5d10469208bf6ae3017d586a23d4` and
`sha256:ec95dfe474f7fb57f9ede8828bb7738766176941802428de231950ae51f98e4c`.
No raw run or project identity is reproduced.

The outward and primary failure were both `fixed_node_start_failed`. Highest completed stage was
`11`. Base and bridge builds completed, exactly four image identities were bound, and no raw image,
container, Node, mission, or claim identity is reproduced. The cleanup failure list was empty and
`recovery_required` was false. Cleanup completed without a reported failure under the reviewed
producer semantics. This is not a generic Docker, container, image, process, project, runtime, or
host absence claim.

## Closed Sequential Diagnostic

The normalized thirteen-key fixed-Node-start projection is complete with reason
`fixed_node_start_state_collected` and classification
`fixed_node_exited_observation_noncanonical`. It records container presence `present`, lifecycle
`exited`, running state `not_running`, exit class `nonzero`, health `unhealthy`, and failure signal
`none`. The observation semantics are `sequential_container_then_mission`; mission lifecycle is
`claimed`, delivery is `claim_delivered`, and evidence is `complete`.

This is a sequential observation, not an atomic snapshot and not proof of root cause. It reproduces
no raw identity, stdout, stderr, engine error, log, environment, configuration, provider output,
whole mission object, private receipt content, or arbitrary tool result.

## Retained Receipt Binding

The exact private receipt root, selected only by the domain-separated run digest above, is
owner-only mode `0700`. It contains exactly:

- an owner-only mode `0500` candidate snapshot containing exactly 668 files;
- `candidate-manifest.json`: owner-only mode `0600`, 97,421 bytes,
  `sha256:dd71dec88a7f7c4f1bb12892ce825ed06759c77e8770234c156e86ac5c13fa8f`;
- `diagnostic.json`: owner-only mode `0600`, 7,705 bytes,
  `sha256:00d654d6017a1960d18e879069eccdd8ba04e47b6d551fc699be67ab11e3eef3`;
- `disposition.json`: owner-only mode `0600`, 125 bytes,
  `sha256:dcce687c6e2a0d6f36e36d3c14ac09e25ba4c195e1f16f35bf6ea44521612dd3`.

The closed disposition is exactly `status=quarantined_not_published`,
`failure_code=fixed_node_start_failed`, `release_allowed=false`, and `uat_complete=false`. This
tracked record binds metadata and expected closed content without reproducing private receipt
contents.

The exact run runtime root and exact public report root were absent, and the public report base was
absent at the point of observation. Those are exact-run and point-in-time observations only, not
general runtime or report absence claims.

## Closed Authority

Attempt budget is zero, `attempt_consumed` is true, and retry and automatic retry are false. All 19
authority fields are false. This closure authorizes no retry, recovery, cleanup, successor attempt,
credential custody, runner lifecycle, arbitrary host/process/shell/Docker-socket control, new power
or tool, release, promotion, production, or UAT. The governed tool count remains exactly 24.

The next action is a separately reviewed bounded diagnosis or repair decision for this specific
closed `fixed_node_exited_observation_noncanonical` state. That action is not a retry and is not an
authorized successor attempt. This closure grants no execution authority.

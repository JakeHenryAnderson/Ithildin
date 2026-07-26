# Local v1 LV1-003 O4 Attempt 013 Disposition

Status:
`ATTEMPT_013_CONSUMED_FIXED_NODE_PHASE_NOT_REPORTED_CLEANUP_COMPLETE_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-013` consumed its single execution budget on exact reviewed candidate
`8fa31904570d2179c5661fa44ff0ff3ca00eba43`, tree
`27f5ccbe8b6153ab7dfbcd97c37193d63217a086`. Annotated review tag
`ithildin/lv1-003-o4-attempt013-reviewed` resolves to that exact commit and tree.

The central-manager-supervised operator command was
`make local-v1-lv1-003-o4-producer-run`, using exact module command
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
The private run and its privately derived Compose project are bound only by domain-separated
digests
`sha256:baf8e92b6d4a52c37cbce9a71a176fca523898476196d01f6be1ab373bfa29e6` and
`sha256:96abd1a39e6c2ce325c31c6c53cca27185082e6daa1127b07802507cd22a12cb`.
The raw invocation output is not reproduced; only its 160-byte length and digest
`sha256:fd9673eeb55fe747baba9605650183eea1691ec0ef555327431d83a8718b9445`
are retained. No raw run, project, or output identity is tracked.

The outward and primary failure were both `fixed_node_start_failed`. Highest completed stage was
`11`. Base and bridge builds completed, exactly four image identities were bound, and no raw image,
container, Node, mission, or claim identity is reproduced. The cleanup failure list was empty and
`recovery_required` was false. Cleanup completed without a reported failure under the reviewed
producer semantics. This is not a generic Docker, container, image, process, project, runtime, or
host absence claim.

## Closed Sequential Diagnostic

The normalized fourteen-key fixed-Node-start projection is complete with reason
`fixed_node_start_state_collected` and classification
`fixed_node_exited_observation_noncanonical`. It records container presence `present`, lifecycle
`exited`, running state `not_running`, exit class `nonzero`, health `unhealthy`, and failure signal
`none`. The observation semantics are `sequential_container_then_mission`; mission lifecycle is
`claimed`, delivery is `claim_delivered`, evidence is `complete`, and
`fixed_bridge_last_entered_phase` is `not_reported`.

This is a sequential, nonatomic, noncausal observation. It is not proof of root cause, repair,
safe retry, success, or authority. It reproduces no raw exit, identity, stdout, stderr, process
output, engine error, log, environment, configuration, provider output, whole mission object,
private receipt content, or arbitrary tool result.

## Retained Receipt Binding

The exact private receipt root, selected only by the domain-separated run digest above, is
owner-only mode `0700`. It contains exactly:

- an owner-only mode `0500` candidate snapshot containing exactly 668 files;
- `candidate-manifest.json`: owner-only mode `0600`, 97,421 bytes,
  `sha256:e4ee51fab03ced9515490873b8f401d45a963ac419625888c5832cb1db2e4890`;
- `diagnostic.json`: owner-only mode `0600`, 7,754 bytes,
  `sha256:fadafe39c3dd17ac428c11e44fbb0239649106bbb32bc412fcb613f4aa2ad0b9`;
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

Source inspection explains the projection behavior: the producer retains a named phase only when
the container is exited, not running, has absent health, and reports no OOM, dead, or engine-error
signal. Attempt 013 observed health `unhealthy`, so the conservative terminal-state predicate
withheld the exit-code phase and normalized it to `not_reported`. This does not explain the
underlying fixed-Node exit.

The next action is a separately reviewed source repair or decision for the terminal-health phase
projection. It is not a fixed-Node root-cause claim, retry authority, or successor authorization.
This closure grants no execution authority.

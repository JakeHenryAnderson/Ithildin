# Local v1 LV1-003 O4 Attempt 014 Disposition

Status:
`ATTEMPT_014_CONSUMED_SOCKET_PARENT_VALIDATION_PHASE_OBSERVED_CLEANUP_COMPLETE_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-014` consumed its single execution budget on exact reviewed candidate
`bfb10f037c916a7c7bd5a15a5d748f3d4d3c3a44`, tree
`191ca97beae3d4ba31ef3e22fb1533a8620e8347`. Annotated review tag
`ithildin/lv1-003-o4-attempt014-reviewed` resolves to that exact commit and tree.

The central-manager-supervised operator command was
`make local-v1-lv1-003-o4-producer-run`, using exact module command
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
The private run and its privately derived Compose project are bound only by domain-separated
digests
`sha256:bde3608954025334040e16549f8d7e661b36c7e39a897ce22c14e4c8a72e73ea` and
`sha256:bd1a847bbb200e3cbf66d2597ff408383a811b7691c091184a3ec284a741ecef`.
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
`fixed_bridge_last_entered_phase` is `socket_parent_validation_entered`.

This closed phase proves only that the fixed bridge entered socket-parent validation before the
observed exit. It is a sequential, nonatomic, noncausal marker, not proof of root cause, repair,
safe retry, success, or authority. It reproduces no raw exit, identity, stdout, stderr, process
output, engine error, log, environment, configuration, provider output, whole mission object,
private receipt content, or arbitrary tool result.

## Retained Receipt Binding

The exact private receipt root, selected only by the domain-separated run digest above, is
owner-only mode `0700`. It contains exactly:

- an owner-only mode `0500` candidate snapshot containing exactly 668 files;
- `candidate-manifest.json`: owner-only mode `0600`, 97,421 bytes,
  `sha256:769472b7a2cb6d60a7ee852ed5d4688446b3aa657c860d4d3bff1d8afadedce6`;
- `diagnostic.json`: owner-only mode `0600`, 7,774 bytes,
  `sha256:91fb82f3128149388854f0ae788a5518631346c02d669e19163cdde6ddf99e3e`;
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
or tool, release, promotion, production, or UAT. The governed tool count remains exactly 24. The
retained producer entrypoint now refuses before activity.

The next action is a separately reviewed bounded source diagnosis or repair for the
`socket_parent_validation_entered` phase. It is not a fixed-Node root-cause claim, retry authority,
or successor authorization. This closure grants no execution authority.

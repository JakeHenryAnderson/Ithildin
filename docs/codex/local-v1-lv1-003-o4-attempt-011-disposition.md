# Local v1 LV1-003 O4 Attempt 011 Disposition

Status:
`ATTEMPT_011_CONSUMED_FIXED_NODE_RUNTIME_STATE_INCONSISTENT_CLEANUP_COMPLETE_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-011` consumed its single execution budget on exact reviewed candidate
`e1ea411c46c794130e2196bb0e92267ca8400c35`, tree
`4d1b90ec2d9efc7740ccdb29e5d6945118956252`. Annotated review tag
`ithildin/lv1-003-o4-attempt011-reviewed` resolves to that exact commit and tree.

The central-manager supervised operator command was
`make local-v1-lv1-003-o4-producer-run`, using exact module command
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
The fresh run ID was `20260726T103142Z-a8de0752` and the exact Compose project, derived by the
reviewed producer convention, was `ithildin-local-v1-o4-a8de0752`.

The outward and primary failure were both `fixed_node_start_failed`. Highest completed stage was
`11`. Base and bridge builds completed, exactly four image identities were bound, and no raw image
ID, container ID, or Node ID is reproduced here. The cleanup failure list was empty and
`recovery_required` was false. Cleanup completed without a reported failure under the reviewed
producer semantics. This is not a generic Docker, container, image, process, project, runtime, or
host absence claim.

## Closed Diagnostic

The normalized fixed-Node-start diagnostic completed with classification
`fixed_node_runtime_state_inconsistent` and reason `fixed_node_start_state_collected`. Its closed
mission projection was mission lifecycle `claimed`, delivery `claim_delivered`, and evidence
`complete`. This is an observed closed classification, not proof of root cause. It reproduces no
raw container identity, stdout, stderr, engine error, log, environment, configuration, whole API
object, credential, prompt, provider content, or arbitrary tool result.

## Retained Receipt Binding

The retained exact-run receipt root is owner-only mode `0700`. It contains:

- an owner-only mode `0500` candidate snapshot containing exactly 668 files;
- `candidate-manifest.json`: owner-only mode `0600`, 97,421 bytes,
  `sha256:e8a763a87aec4c71bfef869dca0a12300a2249beadb6bdf7982ede0b6b8f4876`;
- `diagnostic.json`: owner-only mode `0600`, 7,428 bytes,
  `sha256:543baeffd63374d3ad4fdf26a728e57e1a4bce8ffcd1229818c653ef56c45986`;
- `disposition.json`: owner-only mode `0600`, 125 bytes,
  `sha256:dcce687c6e2a0d6f36e36d3c14ac09e25ba4c195e1f16f35bf6ea44521612dd3`.

The closed disposition is exactly `status=quarantined_not_published`,
`failure_code=fixed_node_start_failed`, `release_allowed=false`, and `uat_complete=false`. This
tracked record binds metadata and expected closed content without reproducing raw private receipt
contents.

The exact run runtime root and exact public report root were absent, and the public report base was
absent at the point of observation. Those are exact-run and point-in-time observations only, not
general runtime or report absence claims.

## Closed Authority

Attempt budget is zero, `attempt_consumed` is true, and retry and automatic retry are false. All 19
authority fields are false. This closure authorizes no retry, recovery, cleanup, successor attempt,
credential custody, runner lifecycle, arbitrary host/process/shell/Docker-socket control, new power
or tool, release, promotion, production, or UAT.

The next action is preparation of a separately reviewed bounded refinement or repair for
`fixed_node_runtime_state_inconsistent` using only the existing diagnostic boundary. That action is
not a retry, and the observed classification is not a root-cause claim. This closure grants no
execution authority. The governed tool count remains exactly 24.

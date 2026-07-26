# Local v1 LV1-003 O4 Attempt 015 Disposition

Status:
`ATTEMPT_015_CONSUMED_GATEWAY_MISSION_PROJECTION_INVALID_CLEANUP_COMPLETE_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-015` consumed its single execution budget on exact reviewed candidate
`5bda7496ad69cb9002b41292106a8dd080117400`, tree
`e55b1d60a14bc8bf798b34df452377df8b0b9d7b`. Annotated review tag
`ithildin/lv1-003-o4-attempt015-reviewed` resolves to that exact commit and tree.

The central-manager-supervised operator command was
`make local-v1-lv1-003-o4-producer-run`, using exact module command
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
The private run and its privately derived Compose project are bound only by domain-separated
digests
`sha256:52cda6a5a9b1f54c40b93ec58ee71dd6f5d38e94cd978707c0e6d93aae62ada5` and
`sha256:9ee88459706bbb7385af6474953e7d34c50c3ef876b9eb1759c97c474bafb889`.
The raw invocation output is never reproduced; only its 171-byte length and digest
`sha256:a667ff635a76069c4725e36bf1ef0abe057e837bbda91dbdc2823eabc890d90d`
are retained. No raw run, project, or output identity is tracked.

The outward and primary failure were both `gateway_mission_projection_invalid`. Highest completed
stage was `13`. Base and bridge builds completed, exactly four image identities were bound, and no
raw image, container, Node, mission, or claim identity is reproduced. The cleanup failure list was
empty and `recovery_required` was false. Cleanup completed without a reported failure under the
reviewed producer semantics. This is not a generic Docker, container, image, process, project,
runtime, or host absence claim.

## Bounded Diagnostic

The observed failure is only the bounded producer classification
`gateway_mission_projection_invalid`. It proves no root cause, repair, safe retry, success, or
authority. This record reproduces no raw output, private receipt content, environment,
configuration, provider response, whole mission object, or arbitrary tool result.

## Retained Receipt Binding

The exact private receipt root, represented only by the domain-separated run digest above, is
owner-only mode `0700`. It contains exactly:

- an owner-only mode `0500` candidate snapshot containing exactly 668 files;
- `candidate-manifest.json`: owner-only mode `0600`, 97,421 bytes,
  `sha256:4910bf2b04672e80b6e6caa1167a8c4ace62b243b8f3001245385bdd8e81f8fd`;
- `diagnostic.json`: owner-only mode `0600`, 7,171 bytes,
  `sha256:b23558b7bc6391bc8b028fe8b463d189a054df004e06aeb986a2a8ecf6b8e642`;
- `disposition.json`: owner-only mode `0600`, 136 bytes,
  `sha256:76111fb55e47a53554a22326499aa8a1b98fc9280ffb80b471e953cc4b645762`.

The closed disposition is exactly `status=quarantined_not_published`,
`failure_code=gateway_mission_projection_invalid`, `release_allowed=false`, and
`uat_complete=false`. This tracked record binds metadata and expected closed content without
reproducing private receipt contents.

The exact run runtime root and exact public report root were absent, and the public report base was
absent at the point of observation. Those are exact-run and point-in-time observations only, not
general runtime or report absence claims.

## Closed Authority

Attempt budget is zero, `attempt_consumed` is true, and retry and automatic retry are false. All 19
authority fields are false. This closure authorizes no retry, recovery, cleanup, successor attempt,
credential custody, runner lifecycle, arbitrary host/process/shell/Docker-socket control, new power
or tool, release, promotion, production, or UAT. The governed tool count remains exactly 24. The
retained producer entrypoint now refuses before activity.

The next action is a separately reviewed bounded source diagnosis or repair for
`gateway_mission_projection_invalid`. It is not a root-cause claim, retry authority, or successor
authorization. This closure grants no execution authority.

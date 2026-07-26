# Local v1 LV1-003 O4 Attempt 010 Disposition

Status:
`ATTEMPT_010_CONSUMED_FIXED_NODE_START_FAILED_CLEANUP_COMPLETE_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-010` consumed its single execution budget on exact reviewed candidate
`782bc06faed3440de5dc3fe4c192b01f91a8680a`, tree
`d4afd1b7fe68a65507f1ad230fffd91f6580b676`. Review tag
`ithildin/lv1-003-o4-attempt010-reviewed` resolves to that exact commit and tree.

The central-manager supervised operator command was
`make local-v1-lv1-003-o4-producer-run`, using exact module command
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
The fresh run ID was `20260726T082552Z-8aa38742` and the exact Compose project was
`ithildin-local-v1-o4-8aa38742`.

The outward and primary failure were both `fixed_node_start_failed`. Highest completed stage was
`11`. Base and bridge builds completed, exactly four image identities were bound, and no raw image
ID or Node ID is reproduced here. The cleanup failure list was empty and `recovery_required` was
false. Cleanup completed without a reported failure under the reviewed producer semantics. This is
not a generic Docker, container, image, process, project, runtime, or host absence claim.

The retained exact-run receipt root is owner-only mode `0700`. It contains:

- an owner-only mode `0500` candidate snapshot containing exactly 668 files;
- `candidate-manifest.json`: owner-only mode `0600`, 97,421 bytes,
  `sha256:5f478983f10839431902684a0f40333408a9ef1c16b5a15cbfc303a657e6c7b0`;
- `diagnostic.json`: owner-only mode `0600`, 7,149 bytes,
  `sha256:8b647d26255b90c607eac85528f3f20881c8deda366befabefc500373dd88cc6`;
- `disposition.json`: owner-only mode `0600`, 125 bytes,
  `sha256:dcce687c6e2a0d6f36e36d3c14ac09e25ba4c195e1f16f35bf6ea44521612dd3`.

The closed disposition is exactly `status=quarantined_not_published`,
`failure_code=fixed_node_start_failed`, `release_allowed=false`, and `uat_complete=false`. This
tracked record does not reproduce private diagnostic contents. The exact run runtime root and exact
public report root were absent. Those are exact-run observations only, not general runtime or report
absence claims.

Attempt budget is zero, `attempt_consumed` is true, and retry and automatic retry are false. All 19
authority fields are false. This closure authorizes no retry, recovery, cleanup, successor attempt,
credential custody, runner lifecycle, host/process/shell/Docker-socket control, new power or tool,
release, promotion, production, or UAT.

The next action is preparation of a bounded fixed-node-start diagnostic candidate for separate
exact review. The tracked evidence does not prove a repair, so this closure authorizes neither a
speculative repair nor a retry and grants no execution authority. The governed tool count remains
exactly 24.

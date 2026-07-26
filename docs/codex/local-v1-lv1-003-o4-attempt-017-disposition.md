# Local v1 LV1-003 O4 Attempt 017 Disposition

Status:
`ATTEMPT_017_CONSUMED_GATEWAY_MISSION_PROJECTION_INVALID_CLEANUP_COMPLETE_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-017` consumed its single execution budget on exact reviewed candidate
`6ef2507f4cf8b296c3cf5a1044f75753ef2c697d`, tree
`4231e0e0dc89ac723189dd95c619c40e75650913`, fixed by annotated tag
`ithildin/lv1-003-o4-attempt017-reviewed`.

The supervised commands were `make local-v1-lv1-003-o4-producer-run` and
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
Private run and project identities are represented only by domain-separated digests
`sha256:4efa41c29ab33205b1b8106f8fc21295bddb20b45bb025ef6dbfa1fee19ecb49` and
`sha256:f3e18416ffcd04203f0ac0a31725b98baeea52f293b6139e6b28666aa8416003`.
Raw output is not reproduced; only its 171-byte size and digest
`sha256:a667ff635a76069c4725e36bf1ef0abe057e837bbda91dbdc2823eabc890d90d`
are retained.

The outward and primary failure were `gateway_mission_projection_invalid`; highest completed stage
was `13`. Base and bridge builds completed, four image identities were bound, cleanup failures were
empty, and recovery was false.

## Identity-Free Projections

The Gateway projection is collection `complete`, reason
`gateway_mission_projection_state_collected`, mission identity `matched`, mission lifecycle
`runner_reported_running`, target Node identity `matched`, delivery `present_object`, and
governed-agent-runs `present_object`.

The Node receipt projection is collection `complete`, reason
`node_receipt_projection_state_collected`, receipt shape `exact`, mission identity `matched`, claim
`valid_format`, envelope `valid_digest`, handoff nonce `valid_digest`, next operation
`completion_pending`, and last closed status `failed_closed`.

Together these bounded projections support only a future separately reviewed diagnosis of why
completion failed closed or the Gateway report did not advance. They prove no exact root cause,
repair, safe retry, or success and authorize no Attempt 018 or repair.

## Retained Receipt Binding

The digest-bound private root is mode `0700` and contains exactly:

- `candidate`, mode `0500`, 668 files;
- `candidate-manifest.json`, mode `0600`, 97,421 bytes,
  `sha256:8ce768e66538d932d8ad16cd5112aa6826943450cf46f9d8a7ac9871c9176c5f`;
- `diagnostic.json`, mode `0600`, 7,953 bytes,
  `sha256:9f86efd4b15aad9492b2ef7aa0e5f26b90b0b40e2feab9ece33ae219cb472158`;
- `disposition.json`, mode `0600`, 136 bytes,
  `sha256:76111fb55e47a53554a22326499aa8a1b98fc9280ffb80b471e953cc4b645762`.

Disposition is exactly `quarantined_not_published`, failure
`gateway_mission_projection_invalid`, release false, and UAT false. The exact run runtime root and
exact report root were absent; the report base was absent at the point of observation. These are
not generic absence claims.

## Closed Authority

Attempt budget is zero, `attempt_consumed` is true, retry, automatic retry, concurrent invocation,
and post-attempt retry are false, and all 19 authority fields are false. Recovery, cleanup,
successor attempt, new tool or power, release, promotion, production, and UAT authority remain
false. The governed tool count remains exactly 24. The producer entrypoint refuses before activity.

The next action is only a separately reviewed bounded diagnosis of why completion failed closed or
the Gateway report did not advance. This closure grants no Attempt 018, repair, retry, or execution
authority.

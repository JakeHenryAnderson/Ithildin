# Local v1 LV1-003 O4 Attempt 018 Disposition

Status:
`ATTEMPT_018_CONSUMED_GATEWAY_MISSION_PROJECTION_INVALID_BRIDGE_DISCONNECTED_CLEANUP_COMPLETE_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-018` consumed its single execution budget on exact reviewed candidate
`bae6be514b9c8d47e09a69fb413f097d9af1d7d4`, tree
`2317226c58ea0000435e79b2d7c4efe6dce088e3`, fixed by annotated tag
`ithildin/lv1-003-o4-attempt018-reviewed`.

The supervised commands were `make local-v1-lv1-003-o4-producer-run` and
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
Private run and project identities are represented only by domain-separated digests
`sha256:fe1e0bf962c4ec5fa4bda96d02033c074f584cbf4db65807730ebad657fb6ef6` and
`sha256:1f7a4ce1caa4674ecb5d63822420bfdb18f76f0dfc3ac521655e80c793179511`.
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
`completion_pending`, last closed status `failed_closed`, and stable last closed reason
`bridge_disconnected`.

Together these bounded projections support only a future separately reviewed diagnosis of the
Gateway/runner liveness discrepancy or why the bridge disconnected. The terminal reason is bounded
runner-receipt evidence only: it does not establish causality. The projections prove no exact root
cause, repair, safe retry, or success and authorize no Attempt 019 or repair.

## Retained Receipt Binding

The digest-bound private root is mode `0700` and contains exactly:

- `candidate`, mode `0500`, 668 files;
- `candidate-manifest.json`, mode `0600`, 97,421 bytes,
  `sha256:7faf7c164ded73aeb5fccfdc39940dfeedc3c3144d7b7590f7ad1dbd4c884f17`;
- `diagnostic.json`, mode `0600`, 8,001 bytes,
  `sha256:cc6fb52aa23e60341e0fd54f7812f2ce88bfc1f4d78f1ee5c291939d75e53b32`;
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

The next action is only a separately reviewed bounded diagnosis of the Gateway/runner liveness
discrepancy or why the bridge disconnected. This closure grants no Attempt 019, repair, retry, or
execution authority.

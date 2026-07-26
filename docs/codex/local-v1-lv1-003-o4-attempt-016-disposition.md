# Local v1 LV1-003 O4 Attempt 016 Disposition

Status:
`ATTEMPT_016_CONSUMED_GATEWAY_MISSION_PROJECTION_INVALID_CLEANUP_COMPLETE_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-016` consumed its single execution budget on exact reviewed candidate
`fef4205299c16da702f729ecfd7b66a1c0c5a6cf`, tree
`f246c857c0bf0fa17513bf8d2b45db979d058db6`, fixed by annotated tag
`ithildin/lv1-003-o4-attempt016-reviewed`.

The supervised commands were `make local-v1-lv1-003-o4-producer-run` and
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
Private run and project identities are represented only by domain-separated digests
`sha256:05354c9ad532193142f84cd4abebbefab35a866658d4b30dd47b8c8dc9e5b035` and
`sha256:d1e77d220d1f53a2f99fc1e1b8a46ffa989bfdb4a49a1d7aa4b420c476f95cde`.
Raw output is not reproduced; only its 171-byte size and digest
`sha256:a667ff635a76069c4725e36bf1ef0abe057e837bbda91dbdc2823eabc890d90d`
are retained.

The outward and primary failure were `gateway_mission_projection_invalid`; highest completed stage
was `13`. Base and bridge builds completed, four image identities were bound, cleanup failures were
empty, and recovery was false.

## Identity-Free Projection

The bounded projection is collection `complete`, reason
`gateway_mission_projection_state_collected`, mission identity `matched`, mission lifecycle
`runner_reported_running`, target Node identity `matched`, delivery projection `present_object`,
and governed-agent-runs projection `present_object`.

This shows that the post-Hermes Gateway mission projection was still running at observation time.
It supports a future separately reviewed bounded convergence or polling design, but proves no root
cause, repair, safe retry, or success and authorizes no Attempt 017 or repair.

## Retained Receipt Binding

The digest-bound private root is mode `0700` and contains exactly:

- `candidate`, mode `0500`, 668 files;
- `candidate-manifest.json`, mode `0600`, 97,421 bytes,
  `sha256:8079ac5100afe2fc99c9af07e0aa05dc700f67eb21ee5b82c1749fdd9750a070`;
- `diagnostic.json`, mode `0600`, 7,545 bytes,
  `sha256:c6fae45136de76bb0638e80fc3d58220594e8e94ba3634ebbfb745c25e663b04`;
- `disposition.json`, mode `0600`, 136 bytes,
  `sha256:76111fb55e47a53554a22326499aa8a1b98fc9280ffb80b471e953cc4b645762`.

Disposition is exactly `quarantined_not_published`, failure
`gateway_mission_projection_invalid`, release false, and UAT false. The exact run runtime root and
exact report root were absent; the report base was absent at the point of observation. These are
not generic absence claims.

## Closed Authority

Attempt budget is zero, `attempt_consumed` is true, retry and automatic retry are false, and all 19
authority fields are false. Recovery, cleanup, successor attempt, new tool or power, release,
promotion, production, and UAT authority remain false. The governed tool count remains exactly 24.
The producer entrypoint refuses before activity.

The next action is only a separately reviewed bounded Gateway mission convergence or polling
design. This closure grants no Attempt 017, repair, retry, or execution authority.

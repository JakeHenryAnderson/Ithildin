# Local v1 LV1-003 O4 Attempt 019 Disposition

Status:
`ATTEMPT_019_CONSUMED_GATEWAY_RUN_DETAIL_INVALID_TERMINAL_MISSION_GATE_PASSED_CLEANUP_COMPLETE_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-019` consumed its single budget on exact reviewed candidate
`ae94ec4b57ddd053d60ab8ffddd36b2026ac6184`, tree
`4a5bcb797e7cc6ddb844469728db2bf3cb452360`, fixed by annotated tag
`ithildin/lv1-003-o4-attempt019-reviewed`. Make exited `2`; the producer exited `1`. The outward and
primary failure were `gateway_run_detail_invalid` at stage `13`. Base and bridge builds completed,
four image identities were bound, cleanup failures were empty, and recovery was false.

Private run/project identities and raw output remain digest-only. The run and project bindings are
`sha256:d457ee920144aaeb9bb0dd8271c5e569574303bba0d4269a5c0cc506e9731de9` and
`sha256:17f4845be1b0026285f8f645b5830cf9894495e23dead3a136ef5e7246950dec`.
Raw output is not reproduced; only its 163-byte size and digest
`sha256:11197c6a46d3faa625e50376cfed5926e706de664e6d057ce912861ce9b16fa5`
are retained.

## Bounded Evidence

The identity-free Node receipt projection is collection `complete`, reason
`node_receipt_projection_state_collected`, receipt shape `exact`, mission identity `matched`, claim
`valid_format`, envelope `valid_digest`, handoff nonce `valid_digest`, next operation
`completion_recorded`, last closed status `runner_reported_succeeded`, and last closed reason
`none`.

No Gateway mission projection is stored or reproduced. Reviewed source control flow establishes
only that the terminal mission-level projection gate passed before the later
`gateway_run_detail_invalid` failure. This is bounded control-flow evidence, not a reproduced raw
projection and not proof of overall O4 success. It proves no root cause, repair, or safe retry.

## Retained Receipt Binding

The digest-bound private root is mode `0700` and contains exactly:

- `candidate`, mode `0500`, 668 files;
- `candidate-manifest.json`, mode `0600`, 97,421 bytes,
  `sha256:6d07ee192b53b15877d79feb0f3b252dd007b0fc90f2502029c2124a490a88cb`;
- `diagnostic.json`, mode `0600`, 7,609 bytes,
  `sha256:1efdf13c9ee8741bb357b2776a43cf12f4de640b748fa41c5ae48a317ea8f783`;
- `disposition.json`, mode `0600`, 128 bytes,
  `sha256:2a10f131d5c4e87270b674cd54a96a9d6a932d8b20e44b6f3ff206bd70afe573`.

Disposition is exactly `quarantined_not_published`, failure `gateway_run_detail_invalid`, release
false, and UAT false. The exact runtime and public report roots were absent; the public report base
was absent point-in-time. These are not generic absence claims.

## Closed Authority

Attempt budget is zero, `attempt_consumed` is true, and retry, automatic retry, concurrent
invocation, post-attempt retry, recovery, cleanup, and successor attempt authority are false. All
19 authority fields are false. New tool or power, release, promotion, production, and UAT remain
false. The governed tool count remains exactly 24. The producer entrypoint refuses before activity.

The next action is only a separately reviewed bounded Gateway run-detail status or projection
diagnosis. This closure grants no Attempt 020, repair, retry, or execution authority.

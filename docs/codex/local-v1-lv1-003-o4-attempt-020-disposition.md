# Local v1 LV1-003 O4 Attempt 020 Disposition

Status:
`ATTEMPT_020_CONSUMED_GATEWAY_RUN_DETAIL_INVALID_CLEANUP_COMPLETE_NO_LIVE_AUTHORITY`

Attempt `LV1-003-O4-ATTEMPT-020` consumed its single budget on exact reviewed candidate
`506cc00267bcedbe00f0384b64a3bf11111bd752`, tree
`6bfb7077a9af05f22095740114b39607b9d715c8`, fixed by annotated tag
`ithildin/lv1-003-o4-attempt020-reviewed`. Make exited `2`; the producer exited `1`. The outward and
primary failure were `gateway_run_detail_invalid` at stage `13`. Base and bridge builds completed,
four image identities were bound, cleanup failures were empty, and recovery was false.

Private run/project identities and raw output remain digest-only. The run and project bindings are
`sha256:24284f1fb67d0e387be6864009f4be59779ec4e0143762a2efd76ff31e0cb02b` and
`sha256:c5bd9d9f408d2a0959b157f191c07d50edee16a7e014620c44548574cb674298`.
Raw output is not reproduced; only its 163-byte size and digest
`sha256:11197c6a46d3faa625e50376cfed5926e706de664e6d057ce912861ce9b16fa5`
are retained.

## Bounded Evidence

The identity-free Node receipt projection is collection `complete`, reason
`node_receipt_projection_state_collected`, receipt shape `exact`, mission identity `matched`, claim
`valid_format`, envelope `valid_digest`, handoff nonce `valid_digest`, next operation
`completion_recorded`, last closed status `runner_reported_succeeded`, and last closed reason
`none`.

This evidence proves no root cause, repair, safe retry, overall O4 success, or generic absence. It
does not establish release or UAT readiness.

## Retained Receipt Binding

The digest-bound private root is mode `0700` and contains exactly:

- `candidate`, mode `0500`, 668 files;
- `candidate-manifest.json`, mode `0600`, 97,421 bytes,
  `sha256:7f555ded398766c1e7de482db1612e7950835de754390aad618815367ee0e1b3`;
- `diagnostic.json`, mode `0600`, 7,609 bytes,
  `sha256:51645f1ba272968200c8b77a759ae013fa464207e930ee68978c9e217ee90e39`;
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
diagnosis. This closure grants no Attempt 021, repair, retry, diagnosis execution, or other
execution authority.

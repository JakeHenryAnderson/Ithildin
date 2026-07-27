# Local v1 LV1-003 O4 Execution Authorization Gate

Status:
`ATTEMPT_021_CONSUMED_SUCCESS_O4_LV1_003_COMPLETE_NO_LIVE_AUTHORITY`

This record closes `LV1-003-O4-ATTEMPT-021`, preserves immutable consumed Attempts 001-021 and all
tracked recovery history, and grants no live authority. Its machine contract is
`docs/codex/local-v1-lv1-003-o4-execution-authorization.json`.

## Attempt 021 Consumed Success

The single supervised invocation succeeded on exact reviewed candidate
`cd267b4454af3e28f71d0f7c2e065d6e28c2d55c`, tree
`506c6f61041204debaeef339ec7d8a0fadf51346`, under annotated tag
`ithildin/lv1-003-o4-attempt021-reviewed`. The exact digest-safe evidence is bound by
`docs/codex/local-v1-lv1-003-o4-attempt-021-disposition.json` and its companion Markdown record.

Attempt 021 is consumed with budget zero. Retry, automatic retry, concurrency, post-attempt retry,
recovery, cleanup, successor attempt, and O5 authority are false. All 19 authority fields are false.
This evidence closes only `O4` and `LV1-003`; it does not prove release, promotion, production,
provider state, runner behavior beyond reported evidence, UAT, or acceptance.

The next ordered milestone is `LV1-004`, but it is paused and not started at the user-directed O4
boundary. Tool count remains exactly 24; new tool, new power, release, promotion, production, and
UAT remain false.

Historical preparation remains bound to review record
`bb5b37a39b196ab8dc468a49afc606196d4ee091`, tree
`3b1da5679392ae1beb520d2821f18be0981f247b`, and the exact five-path Gateway session-binding repair
`a9ef905ee2ec3d5ecb63443d5ad567bf6bc09300`, tree
`75816ab55d96be34f8d22c7e41ad925a1beaee24`, parent
`3a9d522f329f348df43168ccd78cacfbdc338a5e`, review digest
`sha256:bd6c8f6b84c2823dd7319d6beb07f1e62adb35d290274f7f73d3e83744eb19a2`.
The reviewed authorization candidate changed exactly six paths; historical review and tag existence
no longer grant live authority.

## Attempt 020 Consumed Result

Attempt `LV1-003-O4-ATTEMPT-020` consumed its single budget on exact reviewed candidate
`506cc00267bcedbe00f0384b64a3bf11111bd752`, tree
`6bfb7077a9af05f22095740114b39607b9d715c8`, fixed by annotated tag
`ithildin/lv1-003-o4-attempt020-reviewed`. Make exited `2`; the producer exited `1`. The outward and
primary failure were `gateway_run_detail_invalid` at stage `13`. Base and bridge builds completed,
four image identities were bound, cleanup failures were empty, and recovery was false.

The identity-free Node receipt projection is collection `complete`, reason
`node_receipt_projection_state_collected`, receipt shape `exact`, mission identity `matched`, claim
`valid_format`, envelope `valid_digest`, handoff nonce `valid_digest`, next operation
`completion_recorded`, last closed status `runner_reported_succeeded`, and last closed reason
`none`. This proves no root cause, repair, safe retry, overall O4 success, or generic absence.

Private run/project identities and raw output remain digest-only. The run and project bindings are
`sha256:24284f1fb67d0e387be6864009f4be59779ec4e0143762a2efd76ff31e0cb02b` and
`sha256:c5bd9d9f408d2a0959b157f191c07d50edee16a7e014620c44548574cb674298`.
The exact manifest, diagnostic, and disposition receipt digests are
`sha256:7f555ded398766c1e7de482db1612e7950835de754390aad618815367ee0e1b3`,
`sha256:51645f1ba272968200c8b77a759ae013fa464207e930ee68978c9e217ee90e39`, and
`sha256:2a10f131d5c4e87270b674cd54a96a9d6a932d8b20e44b6f3ff206bd70afe573`.
The exact runtime and report roots were absent and the report base was absent point-in-time.

Attempt budget is zero, `attempt_consumed` is true, and the immediate consumed disposition is
recorded. Retry, automatic retry, concurrent invocation, post-attempt retry, recovery, cleanup, and
successor-attempt authority are false. All 19 authority fields are false. Tool count remains exactly
24; new tool, new power, release, promotion, production, and UAT remain false. The producer
entrypoint refuses before activity. The next action is only a separately reviewed bounded Gateway
run-detail status or projection diagnosis; this record authorizes no Attempt 021, repair, retry,
diagnosis execution, or other execution.

## Attempt 020 Historical Authorization Boundary

Attempt 020 was a fresh successor, never a retry, recovery, cleanup, continuation, or reopening of
Attempts 001-019. It was bound to committed review record
`cd36de5682d85f850770dedab61a5c11f444d2a5`, tree
`575b546845a8f7fa1afca089a11bf04aacdbb505`, and the exact reviewed AgentRun provenance repair
`73fb131f1f89e4b12374dac26a3f8efe231f5c31`, tree
`d64f5fb43e118c072b099ab2877a34cd287de695`, parent
`468ae2deaba2c55e05997662aeb20f58f3fa91cd`. The durable review record digest is
`sha256:c20a917fc799c468075c360c4b712e4d2b6964c12e47603930526e661792516b`,
with `GO` and Critical 0, High 0, Medium 0, Low 0. Historical review and tag existence no longer
grant live authority.

## Attempt 019 Consumed Result

Attempt `LV1-003-O4-ATTEMPT-019` consumed its single budget on exact reviewed candidate
`ae94ec4b57ddd053d60ab8ffddd36b2026ac6184`, tree
`4a5bcb797e7cc6ddb844469728db2bf3cb452360`, fixed by annotated tag
`ithildin/lv1-003-o4-attempt019-reviewed`. Make exited `2`; the producer exited `1`. The outward and
primary failure were `gateway_run_detail_invalid` at stage `13`. Base and bridge builds completed,
four image identities were bound, cleanup failures were empty, and recovery was false.

The identity-free Node receipt projection is collection `complete`, reason
`node_receipt_projection_state_collected`, receipt shape `exact`, mission identity `matched`, claim
`valid_format`, envelope `valid_digest`, handoff nonce `valid_digest`, next operation
`completion_recorded`, last closed status `runner_reported_succeeded`, and last closed reason
`none`. No Gateway mission projection is stored or reproduced. Reviewed source control flow
establishes only that the terminal mission-level projection gate passed before the later failure;
that is not proof of overall O4 success.

Private run/project identities and raw output remain digest-only. The run and project bindings are
`sha256:d457ee920144aaeb9bb0dd8271c5e569574303bba0d4269a5c0cc506e9731de9` and
`sha256:17f4845be1b0026285f8f645b5830cf9894495e23dead3a136ef5e7246950dec`.
The exact manifest, diagnostic, and disposition receipt digests are
`sha256:6d07ee192b53b15877d79feb0f3b252dd007b0fc90f2502029c2124a490a88cb`,
`sha256:1efdf13c9ee8741bb357b2776a43cf12f4de640b748fa41c5ae48a317ea8f783`, and
`sha256:2a10f131d5c4e87270b674cd54a96a9d6a932d8b20e44b6f3ff206bd70afe573`.
The exact runtime and report roots were absent and the report base was absent point-in-time.

Attempt budget is zero, `attempt_consumed` is true, the immediate consumed disposition is recorded,
and retry, automatic retry, concurrent invocation, post-attempt retry, recovery, cleanup, and
successor-attempt authority are false. All 19 authority fields are false. Tool count remains
exactly 24; release, promotion, production, and UAT remain false. The producer entrypoint refuses
before activity. The next action is only a separately reviewed bounded Gateway run-detail status or
projection diagnosis; this record authorizes no Attempt 020, repair, retry, or execution.

## Attempt 019 Historical Authorization Boundary

Attempt 019 was a fresh successor, not a retry, recovery, repair, cleanup, or continuation of
Attempt 018. It was bound to committed review record
`abbbd64e577dc7e124a09b5ce0befc23e1152e44`, tree
`6e979c75351d7f68b052b51ac6fd73d0a3ffd698`, and the exact reviewed two-operation terminal repair
`897b22de9b3bd82113f37dc894fb8034f1a8799b`, tree
`b0ffb159a5449dfe1a5497c0016e15bafa92f2c1`. The review record is
`docs/codex/local-v1-lv1-003-o4-two-operation-terminal-repair-exact-review.md`, digest
`sha256:2010f5513ff162438e84a513ea489e16941eff270e448d5ba7a94f66afe64582`,
with `GO_CODE_ONLY` and Critical 0, High 0, Medium 0, Low 0. The exact candidate changed exactly six
paths and preserved twelve-path runtime parity. Historical review and tag existence no longer
grant live authority.

## Attempt 018 Consumed Result

Attempt `LV1-003-O4-ATTEMPT-018` consumed its single budget on exact candidate
`bae6be514b9c8d47e09a69fb413f097d9af1d7d4`, tree
`2317226c58ea0000435e79b2d7c4efe6dce088e3`, fixed by annotated tag
`ithildin/lv1-003-o4-attempt018-reviewed`. Make exited `2`, the producer exited `1`, and the outward
and primary failure were `gateway_mission_projection_invalid` at stage `13`. Base and bridge builds
completed, four image identities were bound, cleanup failures were empty, and recovery was false.

The identity-free Gateway projection is collection `complete`, reason
`gateway_mission_projection_state_collected`, mission identity `matched`, mission lifecycle
`runner_reported_running`, target Node identity `matched`, delivery `present_object`, and
governed-agent-runs `present_object`. The identity-free Node receipt projection is collection
`complete`, reason `node_receipt_projection_state_collected`, receipt shape `exact`, mission
identity `matched`, claim `valid_format`, envelope `valid_digest`, handoff nonce `valid_digest`,
next operation `completion_pending`, last closed status `failed_closed`, and stable last closed
reason `bridge_disconnected`. The terminal reason is bounded runner-receipt evidence only and does
not establish causality.

Private run/project identities and output remain digest-only. The exact receipt bindings are
recorded in `docs/codex/local-v1-lv1-003-o4-attempt-018-disposition.json`; no raw private identity
or content is reproduced. The run, project, manifest, diagnostic, and disposition digests are
`sha256:fe1e0bf962c4ec5fa4bda96d02033c074f584cbf4db65807730ebad657fb6ef6`,
`sha256:1f7a4ce1caa4674ecb5d63822420bfdb18f76f0dfc3ac521655e80c793179511`,
`sha256:7faf7c164ded73aeb5fccfdc39940dfeedc3c3144d7b7590f7ad1dbd4c884f17`,
`sha256:cc6fb52aa23e60341e0fd54f7812f2ce88bfc1f4d78f1ee5c291939d75e53b32`,
and `sha256:76111fb55e47a53554a22326499aa8a1b98fc9280ffb80b471e953cc4b645762`.
Exact runtime/report roots were absent and the report base was absent point-in-time, without generic
absence claims.

Attempt budget is zero, `attempt_consumed` is true, retry, automatic retry, concurrent invocation,
and post-attempt retry are false, and all 19 authority fields are false. Tool count remains 24;
release, promotion, production, and UAT remain false. The producer entrypoint refuses before
activity. The next action is only a separately reviewed bounded diagnosis of the Gateway/runner
liveness discrepancy or why the bridge disconnected, not Attempt 019 or repair authority.

## Attempt 018 Historical Authorization Boundary

Attempt 018 is a fresh successor, not a retry, recovery, repair, cleanup, or continuation of
Attempt 017. It is bound to committed review record
`30af9b4694c3826979c868eb7fb9cb2369bd92a9`, tree
`e57c2e31c0a51e191e42c12580cf29813c56051b`, and preserves runtime parity to reviewed
implementation `694e464d79afd00bc6af7f847acd3c7901fa4086`, tree
`2bdb9e12e9ae65ea71064e8caf20ae3ce5fcda58`. The committed review is
`docs/codex/local-v1-lv1-003-o4-mission-liveness-and-terminal-reason-exact-review.md`, digest
`sha256:d7fff00bed23368467f1c05f9fa05c629d2f0d37f12c0ac93c1a0fde58774ccb`,
with `GO_CODE_ONLY` and Critical 0, High 0, Medium 0, Low 0.

The exact candidate was the immediate child of that review record and changed exactly six paths:
`Makefile`, `README.md`, this Markdown record, its JSON contract, the authorization validator, and
its tests. The fixed annotated tag `ithildin/lv1-003-o4-attempt018-reviewed` peeled to that exact
candidate. Historical review and tag existence no longer grant live authority. At the reviewed
pre-run gate, only the five-field maximum live-authority ceiling could be true; the remaining 14
authority fields stayed false. The single invocation is now consumed permanently.

## Attempt 017 Consumed Result

Attempt `LV1-003-O4-ATTEMPT-017` consumed its single budget on exact candidate
`6ef2507f4cf8b296c3cf5a1044f75753ef2c697d`, tree
`4231e0e0dc89ac723189dd95c619c40e75650913`, fixed by annotated tag
`ithildin/lv1-003-o4-attempt017-reviewed`. Make exited `2`, the producer exited `1`, and the outward
and primary failure were `gateway_mission_projection_invalid` at stage `13`. Base and bridge builds
completed, four image identities were bound, cleanup failures were empty, and recovery was false.

The identity-free Gateway projection is collection `complete`, reason
`gateway_mission_projection_state_collected`, mission identity `matched`, mission lifecycle
`runner_reported_running`, target Node identity `matched`, delivery `present_object`, and
governed-agent-runs `present_object`. The identity-free Node receipt projection is collection
`complete`, reason `node_receipt_projection_state_collected`, receipt shape `exact`, mission
identity `matched`, claim `valid_format`, envelope `valid_digest`, handoff nonce `valid_digest`,
next operation `completion_pending`, and last closed status `failed_closed`.

Private run/project identities and output remain digest-only. The exact receipt bindings are
recorded in `docs/codex/local-v1-lv1-003-o4-attempt-017-disposition.json`; no raw private identity
or content is reproduced. The run, project, manifest, diagnostic, and disposition digests are
`sha256:4efa41c29ab33205b1b8106f8fc21295bddb20b45bb025ef6dbfa1fee19ecb49`,
`sha256:f3e18416ffcd04203f0ac0a31725b98baeea52f293b6139e6b28666aa8416003`,
`sha256:8ce768e66538d932d8ad16cd5112aa6826943450cf46f9d8a7ac9871c9176c5f`,
`sha256:9f86efd4b15aad9492b2ef7aa0e5f26b90b0b40e2feab9ece33ae219cb472158`,
and `sha256:76111fb55e47a53554a22326499aa8a1b98fc9280ffb80b471e953cc4b645762`.
Exact runtime/report roots were absent and the report base was absent point-in-time, without
generic absence claims.

Attempt budget is zero, `attempt_consumed` is true, retry, automatic retry, concurrent invocation,
and post-attempt retry are false, and all 19 authority fields are false. Tool count remains 24;
release, promotion, production, and UAT remain false. The producer entrypoint refuses before
activity. The next action is only a separately reviewed bounded diagnosis of why completion failed
closed or the Gateway report did not advance, not Attempt 018 or repair authority.

## Attempt 017 Historical Authorization Boundary

Attempt 017 was authorized only as the exact six-path child of
`0ecdb532d364ee9cf53f343fbc1a9d3e3bf64f32`, tree
`fc2156f9cabad4df04998fe533a4bc6a61a75a5a`, preserving runtime parity to reviewed candidate
`f222091c86b71162a3eef5e7518ef0f032cc65ec`, tree
`7683d2de4dbca2367189e2b807818e641f1e3e8b`. Historical review and tag existence no longer grant
live authority.

## Attempt 016 Consumed Result

Attempt `LV1-003-O4-ATTEMPT-016` consumed its single budget on exact candidate
`fef4205299c16da702f729ecfd7b66a1c0c5a6cf`, tree
`f246c857c0bf0fa17513bf8d2b45db979d058db6`, fixed by annotated tag
`ithildin/lv1-003-o4-attempt016-reviewed`. Make exited `2`, the producer exited `1`, and the outward
and primary failure were `gateway_mission_projection_invalid` at stage `13`. Base and bridge builds
completed, four image identities were bound, cleanup failures were empty, and recovery was false.

The identity-free projection is collection `complete`, reason
`gateway_mission_projection_state_collected`, mission identity `matched`, mission lifecycle
`runner_reported_running`, target Node identity `matched`, delivery `present_object`, and
governed-agent-runs `present_object`. It shows only that the post-Hermes Gateway projection was
still running at observation time. It supports a future separately reviewed bounded convergence or
polling design but proves no root cause, repair, safe retry, or success.

Private run/project identities and output remain digest-only. The exact receipt bindings are
recorded in `docs/codex/local-v1-lv1-003-o4-attempt-016-disposition.json`; no raw private identity
or content is reproduced. The run, project, manifest, diagnostic, and disposition digests are
`sha256:05354c9ad532193142f84cd4abebbefab35a866658d4b30dd47b8c8dc9e5b035`,
`sha256:d1e77d220d1f53a2f99fc1e1b8a46ffa989bfdb4a49a1d7aa4b420c476f95cde`,
`sha256:8079ac5100afe2fc99c9af07e0aa05dc700f67eb21ee5b82c1749fdd9750a070`,
`sha256:c6fae45136de76bb0638e80fc3d58220594e8e94ba3634ebbfb745c25e663b04`,
and `sha256:76111fb55e47a53554a22326499aa8a1b98fc9280ffb80b471e953cc4b645762`.
Exact runtime/report roots were absent and the report base was absent point-in-time, without generic
absence claims.

Attempt budget is zero, `attempt_consumed` is true, retry, automatic retry, recovery, cleanup, and
successor authority are false, and all 19 authority fields are false. Tool count remains 24;
release, promotion, production, and UAT remain false. The producer entrypoint refuses before
activity. The next action is only a separately reviewed bounded Gateway mission convergence or
polling design, not Attempt 017 or repair authority.

## Attempt 016 Historical Authorization Boundary

Attempt 016 was authorized only as the exact six-path child of
`fb3d0ac5a495d39bf440755d86464de4db401ab3`, tree
`e86f7fe03e0bdb5076ded9e5baeb651910198cf6`, preserving runtime parity to reviewed candidate
`41f2eb11d8b1572ac428e024d5060faaf616af56`, tree
`26a4f89de85fd5fd21e29c313ef5dd4f57fe9166`. Historical review and tag existence no longer grant
live authority.

## Attempt 015 Consumed Result

`LV1-003-O4-ATTEMPT-015` remains consumed. The exact execution candidate was
`5bda7496ad69cb9002b41292106a8dd080117400`, tree
`e55b1d60a14bc8bf798b34df452377df8b0b9d7b`, fixed by annotated tag
`ithildin/lv1-003-o4-attempt015-reviewed`. Its single central-manager-supervised invocation used
`make local-v1-lv1-003-o4-producer-run` and
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
The private run and Compose project are represented only by domain-separated digests
`sha256:52cda6a5a9b1f54c40b93ec58ee71dd6f5d38e94cd978707c0e6d93aae62ada5` and
`sha256:9ee88459706bbb7385af6474953e7d34c50c3ef876b9eb1759c97c474bafb889`.
The raw invocation output is never reproduced; only its 171-byte length and digest
`sha256:a667ff635a76069c4725e36bf1ef0abe057e837bbda91dbdc2823eabc890d90d`
are retained.

The outward and primary failure were `gateway_mission_projection_invalid`; highest completed stage
was `13`. Base and bridge builds completed, exactly four image identities were bound, cleanup
failures were empty, `recovery_required` was false, and cleanup completed under reviewed producer
semantics. This is a bounded observation, not a root-cause, repair, safe-retry, success, generic
absence, or authority claim.

The owner-only mode `0700` receipt root contains exactly a mode `0500` candidate snapshot with 668
files; a mode `0600`, 97,421-byte manifest with
`sha256:4910bf2b04672e80b6e6caa1167a8c4ace62b243b8f3001245385bdd8e81f8fd`; a mode `0600`,
7,171-byte diagnostic with
`sha256:b23558b7bc6391bc8b028fe8b463d189a054df004e06aeb986a2a8ecf6b8e642`; and a mode `0600`,
136-byte disposition with
`sha256:76111fb55e47a53554a22326499aa8a1b98fc9280ffb80b471e953cc4b645762`.
The exact run runtime root and exact public report root were absent; the public report base was
absent at the point of observation.

Attempt budget is zero, `attempt_consumed` is true, and retry, automatic retry, recovery, cleanup,
and successor authority are false. All 19 authority fields are false. Release, promotion,
production, and UAT remain false; the governed tool count remains exactly 24. The retained producer
entrypoint now refuses before activity. The exact closure is
`docs/codex/local-v1-lv1-003-o4-attempt-015-disposition.json`.

The next action is a separately reviewed bounded source diagnosis or repair for
`gateway_mission_projection_invalid`. It is not a root-cause claim, retry authority, or successor
authorization.

## Attempt 015 Historical Authorization Boundary

Attempt 015 was authorized only as the clean exact six-path immediate child of review-record commit
`c30aa3c43a0e51403c04696c473333fd3bc0551a`, tree
`dbd58923a662977a61d1498cb14b0d1cec04895d`. Its reviewed runtime repair was commit
`8f2191a4b3a6b5559f5a9083973c8b2797fe7f45`, tree
`c5634835d7c2f2280ee2555866cf6c32c346f540`, direct parent
`f889449420c865299f8d2a08fe62cc323a994fab`, bound by
`docs/codex/local-v1-lv1-003-o4-socket-parent-mode-exact-review.md`, digest
`sha256:a2dec414e5dd5dbfb1eff972195d3450f8c36c73efcfbab5dc09dfeb665fe43b`.
The review disposition was `GO_CODE_ONLY` with Critical 0, High 0, Medium 0, Low 0. Historical
review and tag existence no longer grant live authority.

## Attempt 014 Consumed Result

`LV1-003-O4-ATTEMPT-014` remains closed by
`docs/codex/local-v1-lv1-003-o4-attempt-014-disposition.json`. Exact execution candidate
`bfb10f037c916a7c7bd5a15a5d748f3d4d3c3a44`, tree
`191ca97beae3d4ba31ef3e22fb1533a8620e8347`, remains fixed by annotated review tag
`ithildin/lv1-003-o4-attempt014-reviewed`. The sole supervised invocation used
`make local-v1-lv1-003-o4-producer-run` and
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
The private run and Compose project are represented only by domain-separated digests
`sha256:bde3608954025334040e16549f8d7e661b36c7e39a897ce22c14e4c8a72e73ea` and
`sha256:bd1a847bbb200e3cbf66d2597ff408383a811b7691c091184a3ec284a741ecef`.
The raw invocation output is not reproduced; only its 160-byte length and digest
`sha256:fd9673eeb55fe747baba9605650183eea1691ec0ef555327431d83a8718b9445`
are retained.

The outward and primary failure were `fixed_node_start_failed`; highest completed stage was `11`.
Base and bridge builds completed, exactly four image identities were bound, cleanup failures were
empty, `recovery_required` was false, and cleanup completed under reviewed producer semantics.

The exact fourteen-key normalized projection is collection `complete`, reason
`fixed_node_start_state_collected`, classification
`fixed_node_exited_observation_noncanonical`, container presence `present`, lifecycle `exited`,
running state `not_running`, exit class `nonzero`, health `unhealthy`, failure signal `none`,
observation semantics `sequential_container_then_mission`, mission lifecycle `claimed`, delivery
`claim_delivered`, evidence `complete`, and phase `socket_parent_validation_entered`. It is a
sequential, nonatomic, noncausal marker and proves no root cause, repair, safe retry, success, or
authority.

The owner-only mode `0700` receipt root contains exactly a mode `0500` candidate snapshot with 668
files; a mode `0600`, 97,421-byte manifest with
`sha256:769472b7a2cb6d60a7ee852ed5d4688446b3aa657c860d4d3bff1d8afadedce6`; a mode `0600`,
7,774-byte diagnostic with
`sha256:91fb82f3128149388854f0ae788a5518631346c02d669e19163cdde6ddf99e3e`; and a mode `0600`,
125-byte disposition with
`sha256:dcce687c6e2a0d6f36e36d3c14ac09e25ba4c195e1f16f35bf6ea44521612dd3`.
The exact run runtime root and exact public report root were absent; the public report base was
absent at the point of observation.

Attempt budget is zero, `attempt_consumed` is true, and retry, automatic retry, recovery, cleanup,
and successor authority are false. All 19 authority fields are false. Release, promotion,
production, and UAT remain false; the governed tool count remains exactly 24. The retained live
target now refuses before activity.

The next action is a separately reviewed bounded source diagnosis or repair for the
`socket_parent_validation_entered` phase. It is not a fixed-Node root-cause claim, retry authority,
or successor authorization.

## Attempt 014 Historical Authorization Boundary

Attempt 014 was authorized only as the clean six-path immediate child of review-record commit
`fe4ac6b0da0e38b6feb18b9fb5c7b7c0ad096051`, tree
`0c212ab813222dece38b49f067cf978adcee583e`. Its reviewed runtime repair was commit
`338dc059fa251299502ff31f9274f2a1ffc9c9ea`, tree
`3428f0148520e629fd5fe50788469fcd55ad2dba`, direct parent
`0e2ed89b744bcf9a98fd09a5b39a0705656aa001`, bound by
`docs/codex/local-v1-lv1-003-o4-terminal-health-phase-projection-exact-review.md`, digest
`sha256:573dd1063364cbbd89ca9f865765dc4c7c28001044a17cd5fa7e3e7f40f6a039`.
The reviewed producer and test digests were
`sha256:036ff3fe0baf2c2d4f8f89f72b6edbcbcf01fff55371ef8752118ded74492292`
and
`sha256:2eaba1dfe1835f8ae507af93d74c2d78ae192cf93ae4330e7b296ba94727f50f`.
The review disposition was `GO_CODE_ONLY` with Critical 0, High 0, Medium 0, Low 0. Historical
review and tag existence no longer grant live authority.

## Attempt 013 Consumed Result

`LV1-003-O4-ATTEMPT-013` is closed by
`docs/codex/local-v1-lv1-003-o4-attempt-013-disposition.json`. Exact execution candidate
`8fa31904570d2179c5661fa44ff0ff3ca00eba43`, tree
`27f5ccbe8b6153ab7dfbcd97c37193d63217a086`, remains fixed by annotated review tag
`ithildin/lv1-003-o4-attempt013-reviewed`. The sole supervised invocation used
`make local-v1-lv1-003-o4-producer-run` and
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
The private run and Compose project are represented only by domain-separated digests
`sha256:baf8e92b6d4a52c37cbce9a71a176fca523898476196d01f6be1ab373bfa29e6` and
`sha256:96abd1a39e6c2ce325c31c6c53cca27185082e6daa1127b07802507cd22a12cb`.
The raw invocation output is not reproduced; only its 160-byte length and digest
`sha256:fd9673eeb55fe747baba9605650183eea1691ec0ef555327431d83a8718b9445`
are retained.

The outward and primary failure were `fixed_node_start_failed`; highest completed stage was `11`.
Base and bridge builds completed, exactly four image identities were bound, cleanup failures were
empty, `recovery_required` was false, and cleanup completed under reviewed producer semantics. No
raw image, container, Node, mission, claim, run, project, or invocation output is tracked. This is
not a generic Docker, image, container, process, project, runtime, or host absence claim.

The exact fourteen-key normalized projection is collection `complete`, reason
`fixed_node_start_state_collected`, classification
`fixed_node_exited_observation_noncanonical`, container presence `present`, lifecycle `exited`,
running state `not_running`, exit class `nonzero`, health `unhealthy`, failure signal `none`,
observation semantics `sequential_container_then_mission`, mission lifecycle `claimed`, delivery
`claim_delivered`, evidence `complete`, and phase `not_reported`. It is sequential, nonatomic, and
noncausal; it proves no root cause, repair, safe retry, success, or authority.

The owner-only mode `0700` receipt root contains exactly a mode `0500` candidate snapshot with 668
files; a mode `0600`, 97,421-byte manifest with
`sha256:e4ee51fab03ced9515490873b8f401d45a963ac419625888c5832cb1db2e4890`; a mode `0600`,
7,754-byte diagnostic with
`sha256:fadafe39c3dd17ac428c11e44fbb0239649106bbb32bc412fcb613f4aa2ad0b9`; and a mode `0600`,
125-byte disposition with
`sha256:dcce687c6e2a0d6f36e36d3c14ac09e25ba4c195e1f16f35bf6ea44521612dd3`.
The exact run runtime root and exact public report root were absent; the public report base was
absent at the point of observation. Those are exact-run and point-in-time observations only.

Source inspection explains only the phase projection: a named phase survives when the container is
exited, not running, has absent health, and reports no OOM, dead, or engine-error signal. Attempt
013 observed health `unhealthy`, so the conservative terminal-state predicate normalized the phase
to `not_reported`. This does not explain the underlying fixed-Node exit.

Attempt budget is zero, `attempt_consumed` is true, and retry, automatic retry, recovery, cleanup,
and successor authority are false. All 19 authority fields are false. Release, promotion,
production, and UAT remain false; the governed tool count remains exactly 24. The retained live
target now refuses before activity.

The next action is a separately reviewed source repair or decision for the terminal-health phase
projection. It is not a fixed-Node root-cause claim, a retry, or successor authorization, and
grants no execution authority.

## Attempt 013 Historical Authorization Boundary

Attempt 013 was authorized only as the clean six-path, single-parent immediate child of review
record `27a4819213b78536aa0008bd0e62b7c6c7435aad`, tree
`1f984a114976d2c99b78a5e397318018092809fe`. Its reviewed runtime candidate was
`4972606a0677164d8de96a4b3e14ce5bead75033`, tree
`a7e5cbfb849f974a142c6861f79af26498bebb3d`, bound by
`docs/codex/local-v1-lv1-003-o4-fixed-bridge-phase-diagnostic-exact-review.md`, digest
`sha256:97c26627c81e19cdba4949a718ddc45b364377a550fb7af8db085bba50d1f51b`.
The rejected direct parent `f8af8a0ec471f607490df094ce5df4f4de3e9381` remains `NO_GO`.
Historical review and tag existence no longer grant live authority.

## Preserved Consumed Attempt 012

`LV1-003-O4-ATTEMPT-012` remains consumed with budget zero, all 19 authority fields false, retry
and automatic retry false, and its private digest bindings unchanged at
`docs/codex/local-v1-lv1-003-o4-attempt-012-disposition.json`. Nothing in Attempt 013 reopens
Attempt 012 or derives successor authority from its result.

## Attempt 012 Consumed Result

Exact execution candidate `7585e401003df796b5a2c7d7b3bc952aaa693fc3`, tree
`86321cd58fcab1b8f3879700deaad366d2f3fc14`, remains fixed by annotated review tag
`ithildin/lv1-003-o4-attempt012-reviewed`. The sole supervised invocation used
`make local-v1-lv1-003-o4-producer-run` and
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
The fresh private run and its privately derived Compose project are represented only by
domain-separated digests
`sha256:d04d1657d8b576efe73e9616053df7e601fc5d10469208bf6ae3017d586a23d4` and
`sha256:ec95dfe474f7fb57f9ede8828bb7738766176941802428de231950ae51f98e4c`;
no raw run or project identity is tracked or printed.

The outward and primary failure were `fixed_node_start_failed`; highest completed stage was `11`.
Base and bridge builds completed and exactly four image identities were bound without recording raw
image, container, Node, mission, or claim identities. Cleanup failures were empty,
`recovery_required` was false, and cleanup completed under the reviewed producer semantics. This
does not establish generic Docker, image, container, process, project, runtime, or host absence.

The exact thirteen-key normalized projection is collection `complete`, reason
`fixed_node_start_state_collected`, classification
`fixed_node_exited_observation_noncanonical`, container presence `present`, lifecycle `exited`,
running state `not_running`, exit class `nonzero`, health `unhealthy`, and failure signal `none`.
Observation semantics are `sequential_container_then_mission`; mission lifecycle is `claimed`,
delivery is `claim_delivered`, and evidence is `complete`. This is a sequential observation, not an
atomic snapshot or root-cause proof.

The owner-only mode `0700` receipt root is selected privately by the first domain-separated digest.
It contains exactly a mode `0500` candidate snapshot with 668 files; a mode `0600`, 97,421-byte
manifest with
`sha256:dd71dec88a7f7c4f1bb12892ce825ed06759c77e8770234c156e86ac5c13fa8f`; a mode `0600`,
7,705-byte diagnostic with
`sha256:00d654d6017a1960d18e879069eccdd8ba04e47b6d551fc699be67ab11e3eef3`; and a mode `0600`,
125-byte disposition with
`sha256:dcce687c6e2a0d6f36e36d3c14ac09e25ba4c195e1f16f35bf6ea44521612dd3`.
The exact run runtime root and exact public report root were absent; the public report base was
absent at the point of observation. Those are bounded exact-run and point-in-time observations, not
generic absence claims.

Attempt budget is zero, `attempt_consumed` is true, and retry, automatic retry, recovery, cleanup,
and successor authority are false. All 19 authority fields are false. Release, promotion,
production, and UAT remain false; the governed tool count remains exactly 24. The retained live
target now refuses before activity.

The next action is only a separately reviewed bounded diagnosis or repair decision for this
specific closed `fixed_node_exited_observation_noncanonical` state. It is not a retry or an
authorized successor attempt and grants no execution authority.

## Attempt 012 Historical Authorization Boundary

Attempt 012 was authorized only as the clean six-path, single-parent immediate child of
`00caa1918678982a4f2680d5f12cc62c37c11ba5`, tree
`c2f7cd890ac7fc6b24b2a91791c2e0fe1f2ed69b`, whose sole parent is reviewed runtime candidate
`2683641c619e8ae5ac93bdec0d9503f83dd79a35`, tree
`0bfa56ac2fb4c614c5fcc5695d05a664f804beac`. The reviewed record is
`docs/codex/local-v1-lv1-003-o4-fixed-node-state-projection-exact-review.md`, digest
`sha256:17dc6c53922a3cc5c10bba79ecae44ef8145605771a730f7574bc7b9bff97c94`;
it binds producer digest
`sha256:e2e7e91e2314fd7322a6dcee8f02e14fb61f02c4afa007e8c29cdd66a1302ae8`
and producer-test digest
`sha256:1d704b16729f28f2cc2cecb1957f4478850323c58f89a9279e215df713eb60ea`.
Independent Sol xhigh review was `GO_CODE_ONLY` with Critical 0, High 0, Medium 0, and Low 0. The
immutable tag is exact, but historical review and tag existence no longer grant live authority.

## Attempt 011 Consumed Result

Consumed `LV1-003-O4-ATTEMPT-011` is immutable history.

Exact execution candidate `e1ea411c46c794130e2196bb0e92267ca8400c35`, tree
`4d1b90ec2d9efc7740ccdb29e5d6945118956252`, is fixed by annotated review tag
`ithildin/lv1-003-o4-attempt011-reviewed`. The sole supervised invocation used
`make local-v1-lv1-003-o4-producer-run` and
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Make exited `2`; the producer exited `1`.
Fresh run `20260726T103142Z-a8de0752` used exact project
`ithildin-local-v1-o4-a8de0752` under the reviewed producer convention.

The outward and primary failure were `fixed_node_start_failed`; highest completed stage was `11`.
Base and bridge builds completed and four image identities were bound without placing any raw image
ID, container ID, or Node ID in tracked closure records. Cleanup reported no failure,
`recovery_required` was false, and cleanup completed under the reviewed producer semantics. This
does not establish generic Docker, image, container, process, project, runtime, or host absence.

The new normalized diagnostic is complete: classification
`fixed_node_runtime_state_inconsistent`, reason `fixed_node_start_state_collected`, mission
`claimed`, delivery `claim_delivered`, and evidence `complete`. This is a closed observed
classification, not root-cause proof, and it grants no retry or repair authority.

The owner-only `0700` receipt root contains a `0500` candidate snapshot of exactly 668 files. Its
`0600` manifest is 97,421 bytes with
`sha256:e8a763a87aec4c71bfef869dca0a12300a2249beadb6bdf7982ede0b6b8f4876`; its `0600`
diagnostic is 7,428 bytes with
`sha256:543baeffd63374d3ad4fdf26a728e57e1a4bce8ffcd1229818c653ef56c45986`; and its closed
`0600` disposition is 125 bytes with
`sha256:dcce687c6e2a0d6f36e36d3c14ac09e25ba4c195e1f16f35bf6ea44521612dd3`.
That disposition is exactly `quarantined_not_published`, failure `fixed_node_start_failed`,
release false, and UAT false. The exact runtime root and exact report root were absent, and the
report base was absent at the point of observation. These are bounded observations only.

Attempt budget is zero, `attempt_consumed` is true, retry and automatic retry are false, and all 19
authority fields are false. No retry, recovery, cleanup, successor, release, promotion,
production, or UAT authority remains. The durable disposition is
`docs/codex/local-v1-lv1-003-o4-attempt-011-disposition.json`.

The reviewed fixed-Node state projection above supersedes the previously generic diagnostic only
for a separately authorized successor. Attempt 011 remains immutable consumed history; its receipt
bindings, failure, and closed observed classification do not authorize Attempt 012, retry,
additional cleanup, or a root-cause claim.

## Attempt 011 Historical Authorization Boundary

Attempt 011 was authorized only as a clean, single-parent immediate child of
`0aee84f160fb3ce4d80a0772389d529594847013`, tree
`4041d61f4fd9685e7de3fe17c5a0c01e817693df`. Its producer/test bytes remain bound by
`docs/codex/local-v1-lv1-003-o4-fixed-node-start-diagnostic-exact-review.md`. At that exact
authorization point, five bounded live authority fields were true and the remaining 14 were false.
That historical authority was consumed by the single invocation and is no longer current.

## Rejected Attempt 011 Authorization Candidate

Authorization candidate `af88dbf4cb5df36d14403185c7ac8e0f24739303`, tree
`7a7e3077f983dabb50d6dae57138044a9cef2883`, was rejected `NO_GO` with Critical 0, High 0,
Medium 1, and Low 1. The Medium finding was that three parameterized fail-closed cases did not
mutate current Attempt 011 truth: `attempt_consumed` remained false and the active producer/Docker
authority fields remained true. The Low finding was that the diagnostic review transposed the
durable `M1` and `L1` descriptions. This rejected candidate grants no authority and is not the
candidate eligible for the Attempt 011 review tag.

## Attempt 010 Consumed Result

Consumed `LV1-003-O4-ATTEMPT-010` now permits only the separately reviewed fixed-node-start
diagnostic preparation represented by the Attempt 011 parent; it does not authorize another
Attempt 010 invocation.

Exact reviewed candidate `782bc06faed3440de5dc3fe4c192b01f91a8680a`, tree
`d4afd1b7fe68a65507f1ad230fffd91f6580b676`, is fixed by review tag
`ithildin/lv1-003-o4-attempt010-reviewed`. Make exited `2`; the producer exited `1`. Fresh run
`20260726T082552Z-8aa38742` used project `ithildin-local-v1-o4-8aa38742`.

The outward and primary failure were `fixed_node_start_failed`; highest completed stage was `11`.
Base and bridge builds completed, and exactly four bound image identities were recorded without
placing any raw image ID or Node ID in tracked closure records. Cleanup reported no failure,
`recovery_required` was false, and cleanup completed without reported failure under reviewed
producer semantics. This does not establish generic Docker, image, container, project, process,
runtime, or host absence.

The exact owner-only receipt root is mode `0700`. Its owner-only mode `0500` candidate snapshot
contains exactly 668 files. Its `0600` `candidate-manifest.json` is 97,421 bytes with digest
`sha256:5f478983f10839431902684a0f40333408a9ef1c16b5a15cbfc303a657e6c7b0`.
Its `0600` `diagnostic.json` is 7,149 bytes with
digest `sha256:8b647d26255b90c607eac85528f3f20881c8deda366befabefc500373dd88cc6`.
Its exact closed `0600` `disposition.json` is 125 bytes with digest
`sha256:dcce687c6e2a0d6f36e36d3c14ac09e25ba4c195e1f16f35bf6ea44521612dd3`.
The exact run runtime root and exact public report root were absent. These bounded observations do
not claim general runtime or report absence. The durable tracked disposition is
`docs/codex/local-v1-lv1-003-o4-attempt-010-disposition.json`.

Attempt budget is zero, `attempt_consumed` is true, retry and automatic retry are false, and all 19
authority fields are false. There is no retry, recovery, cleanup, successor, release, promotion,
production, or UAT authority.

The candidate preserves all nine consumed attempt histories, the consumed and closed Attempt 003
image recovery, the immutable Attempt 009 preflight failure and closure, and the completed tracked
Attempt 008 recovery lineage. Attempt 009 remains consumed at exact candidate
`26a003f7949e4bef5f3c0f66c9e1490b37103d9b`, tree
`a5403df311e3d6c7769a975d75433bca2442c435`, with immutable closure
`8211ba3ee0064dcf63d5eb80060d6ae4129fa4e1`, tree
`c5bf9fd82d76e9d48fdf93c0ea624f6e696bcd39`, after
`required_loopback_port_unavailable`. This is a fresh successor authorization, not a retry or
recovery authority derived from those histories.

## Attempt 010 Exact Candidate Boundary

The exact parent is `660309ba00b9f7cea6fe2cbc5b34000474c2cd8e`, tree
`dbcada823a66447714fe00233be5cc6f77e63442`, itself the single child of
`7b92a1dbcadcf8a076e0de71c3e53e11dba3ca59`. The durable review record
`docs/codex/mission-command-runner-bridge-authorization-index-reconciliation-exact-review.md`
records `GO_CODE_ONLY`, zero Critical, High, Medium, and Low findings, all seven accepted runtime
checkpoints, and zero allowed-runtime drift from authorized runtime tip
`8cd307e3ce2ca20e6fdc1b53fc1937bfa5568685`. Rejected candidates `7735634` and
`01a38ce` remain `NO_GO`. That review grants no live authority by itself.

The tracked Attempt 008 port-release closure, failed quarantine disposition, reviewed recovery
tags, and successful two-container revocation disposition show that predecessor recovery is
closed. The terminal reviewed tag is
`ithildin/lv1-003-o4-attempt008-two-container-revocation-reviewed`. This binding does not grant
successor authority and does not claim cleanup, full project removal, or general absence.
Historically, the next bounded action was a separately reviewed exact-project Attempt 008
reconciliation/recovery lane with no generic process control, broad Docker cleanup, or ambient
credential inspection. It was not another O4 attempt.

At that Attempt 010 authorization point, exactly five bounded live authority fields were true:
existing producer code, its closed Docker lifecycle, live Hermes execution, model-provider access,
and O4 evidence execution. The remaining 14 authority fields were false, including credential
custody, runner lifecycle API, arbitrary host or process control, shell or general Docker-socket
control, non-bypass claims, new powers or tools, release, promotion, production, and UAT. The
governed tool count remains exactly 24.

The gate preserves the reviewed fixed bridge and bounded producer implementation at
`5dab3654391c14fe214a9dfe302c099d0fe5fbf8`. The current code-only authorization record retains
historical origin commit `da17fbc86369ed5a6e7f9de7c1098322bcda4ac9` while binding the later
producer review at `docs/codex/local-v1-lv1-003-o4-producer-exact-review.md`. The separate
post-review disposition is
`docs/codex/local-v1-lv1-003-o4-post-review-disposition.json`. It authorizes only a clean,
single-parent immediate child of code-authorization commit
`86e75f0cf7f92ceb33218f2a66a00668f4da9e12`, with the exact closed six-path control diff and
byte parity across every reviewed runtime, producer, bridge, and covered test path. The gate derives
that child commit and tree only after every check passes; it contains no future self-reference.
That authorization was exercised once by candidate
`9a9e10a083ee9019b58d49d5099040e18bfbb7f2`, tree
`aa3eecea481dd5c92925ceec3421c051c63cb3cf`, and is no longer live.

The machine contract's generic `candidate_parent_commit` and `candidate_parent_tree` fields now
refer only to the Attempt 013 review-record parent
`27a4819213b78536aa0008bd0e62b7c6c7435aad`, tree
`1f984a114976d2c99b78a5e397318018092809fe`. Attempt 012 remains explicit consumed historical
lineage at `7585e401003df796b5a2c7d7b3bc952aaa693fc3`, tree
`86321cd58fcab1b8f3879700deaad366d2f3fc14`. Attempt 011 remains explicit consumed historical
lineage at `e1ea411c46c794130e2196bb0e92267ca8400c35`, tree
`4d1b90ec2d9efc7740ccdb29e5d6945118956252`. Attempt 010 remains explicit consumed historical
lineage at `782bc06faed3440de5dc3fe4c192b01f91a8680a`, tree
`d4afd1b7fe68a65507f1ad230fffd91f6580b676`. The reviewed runtime-native repair
`49db93d80a71855d9ae223826a9849749377c376`, tree
`23950855584316daba76acd65be0bfdfd20fbcb9`, remains the explicit historical Attempt 004
authorization parent. The older
`86e75f0cf7f92ceb33218f2a66a00668f4da9e12`, tree
`11d9a752b8e08b483e1d8b9a347a06b5d8bf9af7`, remains explicit historical post-review lineage and
code-authorization identity only; it is not the current execution candidate parent.

The machine contract names all inherited Attempt 001 lineage with explicit `attempt_001_*` keys.
Those fields are historical only. The validator's public current-attempt fields bind the consumed
Attempts 001 through 009 as history while the public current-attempt fields bind the dynamic
Attempt 010 child. Attempts 001 through 009 remain explicit history, so generic report labels cannot
silently substitute an earlier attempt for the current attempt.

## Attempt 001 Result

The exact command `uv run python scripts/local_v1_lv1_003_o4_producer.py` exited `1` before gate
authorization or producer runtime entry. Module import failed at
`scripts/local_v1_lv1_003_o4_producer.py:36` with
`ModuleNotFoundError: No module named 'scripts'`. The durable exact disposition is
`docs/codex/local-v1-lv1-003-o4-attempt-001-disposition.json`.

Read-only post-failure checks found the receipt, runtime, and constrained-journey report roots
absent. Attempt 001 therefore performed no runtime creation, Docker, Ollama or provider, API, Node,
Hermes, credential, network journey, or evidence action. This is a bounded observation about this
failed invocation, not a general non-bypass claim.

## Entrypoint Repair Candidate

The operator-visible live, gate-protected entrypoint is now
`make local-v1-lv1-003-o4-producer-run`, with the exact recipe
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Importing that module does not execute its
`main` function. The failed command `uv run python scripts/local_v1_lv1_003_o4_producer.py` is not
an authorized future invocation.

This repair does not restore the consumed Attempt 001. The repaired candidate
`88c707f1c90d5807a81412ea7790b3a0b94e2f85`, tree
`5316f8f270eb55af38dd032ec7723edef8a423c5`, received independent exact review with zero Critical,
High, Medium, or Low findings. The distinct Attempt 002 disposition is
`docs/codex/local-v1-lv1-003-o4-attempt-002-disposition.json`. The live Make target remains outside
release, milestone, static, and authorization-check dependencies.

## Attempt 002 Result

Candidate `02c78966f9096870e0f8744ba42116bb364ecfcd`, tree
`a26b90fee43120a0b9a34f09fc4b75f6fcf07e99`, was invoked through the exact operator and module
commands. Make exited `2`; the producer exited `1` with `fixed_compose_invalid`. The exact run and
project identities were `20260725T114755Z-c46245d0` and `ithildin-local-v1-o4-c46245d0`.

The gate and runtime were entered, and private runtime, receipt, and candidate-snapshot material was
created. Only Docker/Compose version queries and Compose config validation occurred. The base config
passed; fixed-overlay config failed because the base-plus-overlay `tmpfs` list merge duplicated the
`/tmp` mount target. No overlay repair is included here.

No Docker mutation/build/resource creation, provider call, API start, Node enrollment, Hermes
invocation, credential output, or successful evidence occurred. Exact project-label and run-image
inspection found zero residue, but cleanup is not claimed.

The runtime run directory and plaintext are absent; the empty owner-only runtime base remains. The
owner-only quarantined receipt and 663-file snapshot remain intentionally retained. The disposition
and candidate-manifest digests are bound in
`docs/codex/local-v1-lv1-003-o4-attempt-002-closure.json`; no published report exists.

The gate validates that retained evidence directly and independently of Git ignore state. It uses
no-follow reads and requires exact owner identity, modes, sizes, digests, manifest paths, snapshot
contents, an empty runtime base, and an absent published report. The current closure repair scope is
exactly seven tracked paths, including `.gitignore`; its three exact evidence-root child patterns do
not create a broad `var` ignore and do not suppress gate inspection.

## Compose Repair Review And Attempt 003 Result

The exact Compose-repair candidate
`7e6eb9f0fcad35016f611096543fa4a81017259c`, tree
`fef080b85db9b44675150954d6af5afd5d6fec0d`, received independent Sol xhigh read-only review with
zero Critical, High, Medium, or Low findings and disposition `GO`. The durable review is
`docs/codex/local-v1-lv1-003-o4-compose-repair-exact-review.md`.

The repaired base Compose, overlay, and producer digests are respectively
`sha256:895107a268169790024c07fe00556fb5d6df0ce4479f49cbe091ccfc517ceb04`,
`sha256:f6a78f705165354e9908c4512ab551f87dd16cada6e415d59979d78d6f66107c`, and
`sha256:b4d44f09183fca2df5cab33496571c3ac316420074e8eeba71e506fd92999c4b`.
The base Node owns exactly one bounded
`/tmp:size=16m,mode=0700,uid=10002,gid=10002` declaration, the overlay no longer duplicates that
target, and the producer rejects any non-exact merged Node tmpfs set.

The accompanying historical
`docs/codex/local-v1-lv1-003-o4-attempt-003-disposition.json` authorized no static future candidate.
Only after every check passed did the prior gate derive a clean, single-parent immediate child of
the reviewed repair commit whose committed diff was exactly the seven-path control allowlist. That
derived candidate was `7f819bb91c475b4b9fa69b975e629810a7254020`, tree
`7ff30d4625e6b086809703889376d34cdb0998b5`.

The exact operator invocation consumed Attempt 003. Make exited `2`; the producer exited `1` with
`recovery_required`. The exact run and project identities were
`20260725T125344Z-6460809b` and `ithildin-local-v1-o4-6460809b`.

The gate and producer runtime were entered. The Docker mutation and image-build phase was entered,
three base-service image outputs were observed afterward, and cleanup did not complete. This record
does not claim that an earlier primary error existed or assign a value to one. The final
`recovery_required` may have replaced an earlier error or may have originated in cleanup itself.
The missing run-specific Hermes image makes bridge image-build failure a hypothesis, not a proven
diagnosis. No later runtime phase is claimed.

A point-in-time exact-run-scoped read-only observation found zero project-labeled containers,
volumes, and networks, no run-specific Hermes image, and three retained sole-tag `linux/arm64`
base-service images with zero containers and exact project/service labels. Their exact references,
image IDs, and labels are recorded in
`docs/codex/local-v1-lv1-003-o4-attempt-003-closure.json`. This is not current live truth, general
Docker absence, completed cleanup, or authority to remove an image.

The owner-only Attempt 003 receipt retains a 119-byte exact quarantine disposition, a 96,628-byte
manifest bound to the attempted commit/tree, and a 663-file exact candidate snapshot. The runtime
run directory was absent and the runtime base was empty `0700` at closure, before the separately
authorized recovery. The report base remains absent. The validator directly and independently
validates the exact Attempt 002 and Attempt 003 retained receipts and rejects any missing, changed,
unknown, extra, symlink, or special run, file, directory, manifest, or snapshot entry.

## Attempt 003 Image Recovery Closure

The one-shot image recovery was consumed by exact recovery candidate
`2051a136e13bacbee4e3fcec332fc4ef78698e73`, tree
`e0cb7285e720c38a1e071536d7bd25e2bc7caa4e`, and durably closed at commit
`bdde370917f11fd9763954a53885d81a4a28b864`, tree
`465de2881a782e30af0696b8bb534161a0336acd`. The durable recovery closure is
`docs/codex/local-v1-lv1-003-o4-image-recovery-closure.json`.

The owner-only `0700` runtime base now contains exactly one retained entry:
`var/local-v1-lv1-003-o4-runtime/attempt-003-image-recovery-001-consumed.json`. That owner-only
`0600` regular file is exactly 336 bytes with digest
`sha256:df7ce1a69c5fc3b27011f788f846bb5b385ed6f3d348ceb6c78d12de9366ca3c`.
It binds recovery ID `LV1-003-O4-ATTEMPT-003-IMAGE-RECOVERY-001`, the exact recovery candidate,
status `consumed_before_docker_inspection`, and retry false.

The validator requires that exact receipt and rejects a missing, changed, extra, symlink, or special
runtime entry with descriptor-anchored no-follow reads. The receipt remains durable consumption
evidence, not successful O4 evidence. Receipt deletion or mutation is not authorized.

The successful recovery result removed the three exact Attempt 003 image IDs and separately
observed the three IDs, four run references, and exact-project containers, volumes, and networks
absent. Those were exact-run-scoped point-in-time postconditions, not ongoing live truth, general
Docker absence, or a non-bypass claim. The recovery budget remains zero and recovery retry remains
false.

## Runtime-Native Repair Review

Exact commit `49db93d80a71855d9ae223826a9849749377c376`, tree
`23950855584316daba76acd65be0bfdfd20fbcb9`, received independent GPT-5.6 Sol xhigh read-only
review with Critical: 0, High: 0, Medium: 0, Low: 0 and exact-commit disposition `GO`. The durable
review is `docs/codex/local-v1-lv1-003-o4-runtime-native-repair-exact-review.md`.

The repaired bridge Dockerfile digest is
`sha256:a175feecf1fe08bb1f750fecda51ea57ec17cdfd117f0bb36cddfc7f59bc356e`.
It creates the Ithildin virtual environment with `/usr/bin/python3` inside the exact pinned Hermes
runtime lineage and asserts Python 3.12 or later plus the native interpreter relationship in both
stages. It does not transplant a virtual environment from a foreign build image.

The repaired producer digest is
`sha256:d191f58f1b63245499b1447e5e67f21dc638b6a8ad3881a777574c9a7d010f55`.
After every successful build it binds each run image to the exact inspected full image ID,
reference, project/service labels, platform, config, and layers. Cleanup reconciles those identities,
refuses drift or ancestor-container residue, removes only exact bound IDs without force, and proves
the exact bound IDs and references absent. A bounded secret-free diagnostic receipt preserves stable
primary and cleanup failure classifications separately without persisting raw command output,
credentials, provider/model content, arbitrary paths, or tool results.

## Attempt 004 Result And Closure

Attempt `LV1-003-O4-ATTEMPT-004` was consumed by exact candidate
`6452111a1d78f218a24432aaf833004195679318`, tree
`e8ea86cbd577a2d1323c27b2c3326b3c99ff7804`. The exact run and project were
`20260725T162319Z-329e129a` and `ithildin-local-v1-o4-329e129a`.

Both base and bridge builds completed, all four exact image identities were bound, and the highest
completed stage was `7`. The stable primary failure was `base_services_start_failed`; the separate
cleanup classifier was `owned_image_id_absence_probe_failed`; and the outward code was
`recovery_required`.

The cleanup classifier has a verified narrow explanation: Docker's absent-image-ID response
included a stdout newline while the producer required empty stdout. A separate read-only
exact-run-scoped postcheck found all four exact run references and IDs absent, with zero
exact-project containers, volumes, and networks. That is not a general Docker absence or
cleanup-completed claim.

The Attempt 004 runtime run directory is absent. The owner-only runtime base retains exactly the
prior `attempt-003-image-recovery-001-consumed.json` receipt. The exact owner-only Attempt 004
quarantine contains a 119-byte disposition, a 6,885-byte diagnostic, a 96,772-byte candidate
manifest, and a read-only 664-file exact candidate snapshot. The durable disposition is
`docs/codex/local-v1-lv1-003-o4-attempt-004-disposition.json`.

On this exact evidence no image recovery is required or authorized. No evidence deletion, producer
repair, retry, or further execution is authorized. The next action is a separate reviewed producer
repair for Docker not-found output normalization plus a bounded diagnostic for the earlier
`base_services_start_failed` primary failure.

No future closure child commit or tree is stated. The closure validator accepts only a clean,
single-parent immediate child of the attempted candidate whose committed diff is the exact
eight-path closure allowlist recorded in the Attempt 004 disposition. That closure is now durable
at commit `1cbef32d467246a2638ed1205de3aea2d6d952d6`, tree
`237d2ff767d7a625b48518e77e8cd7d0d7bec047`.

## Diagnostic Repair Review And Attempt 005 Result

Exact diagnostic-repair commit `dea1e48acb411e9afd3c6e2c777c05c08e0c5386`, tree
`40e1a7c862b1031dbab1bba9a7f7a30af0beb976`, received independent GPT-5.6 Sol xhigh read-only
review with Critical: 0, High: 0, Medium: 0, Low: 0 and exact-commit disposition `GO`. The durable
review is `docs/codex/local-v1-lv1-003-o4-diagnostic-repair-exact-review.md`.

The reviewed repair changes exactly the producer and its focused test. Their exact SHA-256 digests
are respectively
`sha256:f484e2005f16b006c2251a53af728e6c62bee812d8c3616ccd059468e6069e14`
and `sha256:ef8b455cece020d76892e6ee19775bc0099414dbbff9ff9c24aa15128702bc33`.
The exact absent-image-ID probe accepts only the closed stdout set `{empty, newline}` and the exact
known daemon-error set. A failed base-service start may run only the fixed Compose `ps --all`
diagnostic for `ithildin-api` and `ithildin-ui`, using the exact
`{{.Service}}\t{{.State}}\t{{.Health}}\t{{.ExitCode}}` format. Combined output is bounded to 1,024
bytes, parsed through closed service/state/health/exit-code rules, and never retained as raw
diagnostic evidence.

Attempt `LV1-003-O4-ATTEMPT-005` was consumed by exact candidate
`affba0570ae15e897f92629966d445ad563ec5ff`, tree
`8b262e7efa55db72b5402f6924ec938e2d06d85f`. The exact run and project were
`20260725T172408Z-b806c1bd` and `ithildin-local-v1-o4-b806c1bd`.

Both base and bridge builds completed, all four exact image identities were bound, and the highest
completed stage was `7`. The primary and outward failure was `base_services_start_failed`; the
cleanup failure list was empty; and `recovery_required` was false. The bounded diagnostic completed
and classified the API as `service_exited_nonzero` and the UI as `service_created`. This does not
state why the API exited and assigns no root cause.

The reviewed diagnostic records successful in-run cleanup for the exact bound Attempt 005
resources. A separate read-only exact-run-scoped postcheck found all four exact run references and
IDs absent, with zero exact-project containers, volumes, and networks. Those postconditions are
point-in-time exact-run observations, not ongoing live truth or generic Docker absence.

The Attempt 005 runtime run directory and plaintext are absent. The owner-only runtime base retains
only the prior 336-byte `attempt-003-image-recovery-001-consumed.json` receipt. The exact owner-only
Attempt 005 quarantine contains a 128-byte disposition, a 7,059-byte diagnostic, a 96,772-byte
candidate manifest, and a read-only 664-file exact candidate snapshot. The durable disposition is
`docs/codex/local-v1-lv1-003-o4-attempt-005-disposition.json`.

The gate directly validates all four retained Attempt 002 through Attempt 005 receipt roots and
rejects any missing, mutated, extra, symlink, or special entry. On this exact evidence no image
recovery is required or authorized, no evidence deletion is authorized, and no earlier attempt or
recovery authority is reopened.

No future closure child commit or tree is stated. The closure validator accepts only a clean,
single-parent immediate child of the attempted candidate whose committed diff is the exact
eight-path closure allowlist recorded in the Attempt 005 disposition.

The next action is a separate reviewed API-exit diagnostic repair. This closure does not guess the
cause of `service_exited_nonzero`, includes no producer change, and grants no execution authority.

## API Container-State Diagnostic Review And Attempt 006 Result

Exact API container-state diagnostic commit
`3f207b8f390742b956ed62cea674b0e5c557b514`, tree
`e3bc1d84ab798e34b297b659fa4698003f3423fe`, received independent GPT-5.6 Sol xhigh read-only
review with Critical: 0, High: 0, Medium: 0, Low: 0 and exact-commit disposition `GO`. The durable
review is
`docs/codex/local-v1-lv1-003-o4-api-container-state-diagnostic-exact-review.md`.

The review preserves the rejected lineage. Commit
`77356340bbabbbedff658abba70800a823f3c1ec`, tree
`4e9f5effd40ea8666df17bb6d57b6a897eafc19d`, was `NO_GO` with one Medium orphan-on-interruption
finding. Commit `01a38cee52a1d9eb73e21bfeed8a047dd56a07c6`, tree
`00f408ed329e0bdb7cae341161a66b4563984dc6`, was `NO_GO` with one Medium
unbounded-or-swallowed-reap finding. The final candidate resolves both findings. The producer and
focused-test SHA-256 digests are respectively
`sha256:412b10a4216add1f999f6c1b09e89c29b901512647e9a0c2537bd571a84948be` and
`sha256:1899f3fd2af0b1b9613095d6e35e1d77f55e94f094b46c53206ef17050c56b03`.

The new diagnostic is reachable only after base-service `up` fails and the closed base-service
diagnostic classifies the API as `service_exited_nonzero`. It runs the exact Compose
`ps --all --quiet ithildin-api` identity query and may then inspect only the exact validated and
bound 64-character container ID. Each command has a ten-second ceiling and a hard incremental
512-byte combined stdout-plus-stderr cap. Parsing is closed over exact identity, project, service,
state, Boolean, exit-code, and health scalars.

No raw output, container ID, daemon error, log, environment, mount, configuration, command,
credential, prompt, provider content, or tool result is persisted. Timeout, overflow, malformed
output, missing or ambiguous identity, command failure, and interruption produce only closed
fallback classifications. Process teardown uses bounded kill, wait, and poll attempts and does not
silently swallow an interruption. The primary failure remains `base_services_start_failed`;
diagnostic collection does not alter cleanup classification or cleanup behavior. This gate makes
no root-cause claim and does not claim Attempt 006 will succeed.

Attempt `LV1-003-O4-ATTEMPT-006` is authorized only for a clean, single-parent immediate child of
the reviewed commit and tree. No future child commit or tree is stated here. The gate derives the
execution candidate only after every check passes and requires its committed diff to equal exactly:

1. `Makefile`
2. `README.md`
3. `docs/codex/local-v1-lv1-003-o4-api-container-state-diagnostic-exact-review.md`
4. `docs/codex/local-v1-lv1-003-o4-execution-authorization.json`
5. `docs/codex/local-v1-lv1-003-o4-execution-authorization.md`
6. `scripts/local_v1_lv1_003_o4_execution_authorization_check.py`
7. `tests/test_local_v1_lv1_003_o4_execution_authorization_check.py`

The execution budget is one, `attempt_consumed` is false, and retry and automatic retry are false.
The sole operator command is `make local-v1-lv1-003-o4-producer-run`, whose exact module command
remains `uv run python -m scripts.local_v1_lv1_003_o4_producer`. The gate does not claim atomic,
tamper-proof, persistent cross-process budget consumption. Any invocation outcome consumes Attempt
006 and requires an immediate separate post-attempt disposition before any further execution.

The gate directly validates all four retained Attempt 002 through Attempt 005 receipt roots and the
consumed Attempt 003 recovery receipt. It rejects missing, mutated, extra, symlink, or special
entries. No earlier attempt, recovery, retry, or evidence-deletion authority is reopened.

The exact authorized candidate was
`d4c1d322a9d3faf24422009b7bc40f73544250af`, tree
`9acbfc6ee270613518c4c5cc74b2719604946c46`. Its sole invocation consumed Attempt 006 with run
`20260725T183846Z-b00570b3` and Compose project
`ithildin-local-v1-o4-b00570b3`.

Both image builds completed, all four image identities were bound, and producer stage `7` was
reached. The primary and outward failure remained `base_services_start_failed`. The base-service
diagnostic classified the API as `service_exited_nonzero` and the UI as `service_created`. The API
state diagnostic completed with `api_application_exit_nonzero_no_engine_error` and health
`unhealthy`. It found no OOM-killed or engine-error condition, but the exact application root cause
remains unknown.

The cleanup failure list is empty and `recovery_required` is false. A separate exact-run-scoped
point-in-time postcheck found all four exact references and IDs absent, the exact-project
containers, volumes, and networks absent, and the temporary Docker configuration cleaned. These
facts do not claim generic or ongoing Docker absence.

The owner-only retained Attempt 006 receipt contains a 128-byte disposition with digest
`sha256:5a84070039cc153416cf6fcc3a12c9f13bbd921befa97ee4b33a861a309b9d7a`, a 7,270-byte diagnostic
with digest `sha256:5203fad9e028b6596c46358de00ab5a24e78ab314dbb582f9c3184ad4ac296b5`, a
96,772-byte manifest with digest
`sha256:001e9c51992339079de8560d372a463ce7b30b4d9ff1be38cd516e7148f78fcd`, and a
664-file exact candidate snapshot. The durable disposition is
`docs/codex/local-v1-lv1-003-o4-attempt-006-disposition.json`.

No future closure child commit or tree is stated. The closure validator accepts only a clean,
single-parent immediate child of the attempted candidate whose committed diff is the exact
eight-path closure allowlist recorded in the Attempt 006 disposition.

The next action is a separately reviewed application-emitted closed startup-stage diagnostic.
It must not scrape logs or persist raw application output. This closure assigns no root cause,
includes no producer change, and grants no execution authority.

## Application Startup-Stage Diagnostic Review And Attempt 007 Authority

Exact implementation commit `cce80b5cc71e9387237d18b588d294c39351a362`, tree
`4701443cd266cd86d6654a295f6277caddc117f2`, received independent GPT-5.6 Sol xhigh read-only
review with Critical: 0, High: 0, Medium: 0, Low: 0 and exact-commit disposition `GO`. The durable
review is
`docs/codex/local-v1-lv1-003-o4-application-startup-stage-diagnostic-exact-review.md`.

The review binds exactly six implementation and test paths and their SHA-256 digests:

1. `apps/api/src/ithildin_api/app.py` —
   `sha256:be8ad59f62dc71180e327ad044c481a4c916cbc42d043bfd88d749d4fbf30730`
2. `apps/api/verified_launch.py` —
   `sha256:9c7a71bcc9c4643e203a578486b04ea392df1985b99b0da06a89973b20a96408`
3. `scripts/local_v1_lv1_003_o4_producer.py` —
   `sha256:76f74c3c2b75ae8b320c5c12c3087b51a714ec1f9230a373a3d9335e9df0aca0`
4. `tests/test_api_service.py` —
   `sha256:4c74e040294ccf216436bd729ab5f84536912d7cd17d5a3d587a57c7c5a69d2c`
5. `tests/test_local_v1_lv1_003_o4_producer.py` —
   `sha256:d7f0df7e818c43d83abe42b4e1c5d9d97e4fa05d8a7ef64927549a511d9f3a45`
6. `tests/test_runtime_candidate_bootstrap.py` —
   `sha256:68cdceb283d5968ede0d589d46b96e0a9319bffd83a037105320ec4a21139896`

The application writes only one of 12 closed startup stages to canonical ASCII JSON through an
owner-matching `0700` no-follow directory and an atomically replaced `0600` file. The producer may
read that marker only after Compose `up` fails, the API is `service_exited_nonzero`, and the
container-state diagnostic is exactly `api_application_exit_nonzero_no_engine_error`. The
descriptor-anchored no-follow read is capped at 256 bytes and retains only normalized collection
status, reason code, and last emitted stage. Missing or unsafe material becomes closed `unknown`.

The stage marker does not authorize log scraping or persistence of raw application output,
exceptions, tracebacks, error messages, environment, configuration, credentials, provider/model
content, prompts, or tool results. It localizes the last successful application-emitted stage only;
it does not establish root cause or predict Attempt 007 success. Primary failure, cleanup,
recovery, and the governed 24-tool surface remain unchanged.

The exact candidate passed 389 focused tests, Ruff, strict mypy, no-new-powers, the exact 24-tool
invariant, and the agent-workflow check. Those checks are evidence, not execution or release
authority.

Attempt `LV1-003-O4-ATTEMPT-007` is authorized only for a clean, single-parent immediate child of
the reviewed commit and tree. No future child commit or tree is stated. The gate derives the
candidate only after every check passes and requires this exact seven-path control allowlist:

1. `Makefile`
2. `README.md`
3. `docs/codex/local-v1-lv1-003-o4-application-startup-stage-diagnostic-exact-review.md`
4. `docs/codex/local-v1-lv1-003-o4-execution-authorization.json`
5. `docs/codex/local-v1-lv1-003-o4-execution-authorization.md`
6. `scripts/local_v1_lv1_003_o4_execution_authorization_check.py`
7. `tests/test_local_v1_lv1_003_o4_execution_authorization_check.py`

The budget is one, `attempt_consumed` is false, and retry and automatic retry are false. The sole
operator command is `make local-v1-lv1-003-o4-producer-run`, whose exact module command remains
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Any invocation outcome consumes Attempt
007 and requires an immediate separate post-attempt disposition.

The validator preserves and directly checks retained Attempts 002 through 006 receipts and the
consumed Attempt 003 recovery receipt. No earlier attempt, recovery, retry, evidence-deletion, or
application-diagnostic authority is reopened.

The exact candidate `a2f0338a045dd15352c77cb1841f2098013b1f86`, tree
`04a5dbe34b604c95eb5a63bbfc9610b1033bf521`, was invoked once. Run
`20260725T194808Z-1993a10f`, project `ithildin-local-v1-o4-1993a10f`, failed with
`base_services_start_failed` after both builds and stage `7`.

The API was `service_exited_nonzero`, the UI was `service_created`, and the API container-state
classification was `api_application_exit_nonzero_no_engine_error` with health `unhealthy`. The new
application-stage diagnostic was `inconclusive`: reason `application_startup_stage_missing`, stage
`unknown`. Marker absence means failure before the first checkpoint or an unusable diagnostic
channel; it does not prove either explanation or establish root cause.

Cleanup failures are empty and `recovery_required` is false. The separate exact-run postcheck found
all four exact references and IDs, project containers, volumes, and networks absent; the temporary
Docker configuration and runtime plaintext were absent. The retained receipt binds the 128-byte
disposition, 7,438-byte diagnostic
`sha256:add06ef7d609b220e52d3ab0053a8521262d1dbc253b0d972cae83442f97cf10`,
96,772-byte manifest
`sha256:73219848ccef6715ee7c1f3fb5356ecced8db36eea58bc449cf64d37e7197998`,
and 664-file snapshot.

Attempt 007 is consumed. Its closure accepts only a clean direct child of the attempted candidate
with the exact eight-path closure allowlist recorded in
`docs/codex/local-v1-lv1-003-o4-attempt-007-disposition.json`.

The next action is a separately reviewed pre-launch Docker image-readability repair investigation.
It must not scrape logs or claim a proven root cause. This closure grants no execution authority.

## Image-Readability Repair Review And Attempt 008 Authority

Exact repair commit `7cc1da575074895a7210c5f15a34ae136f4f932a`, tree
`b448eb922619e59af74275cf1070deb33b6813ef`, received exact read-only review with Critical: 0,
High: 0, Medium: 0, Low: 0 and exact-commit disposition `GO`. The durable review is
`docs/codex/local-v1-lv1-003-o4-image-readability-repair-exact-review.md`.

The review binds exactly five repair and test paths:

1. `deploy/Dockerfile.api` —
   `sha256:b0fba85ea070c8d2100d79b69db202f2a2ef35adae4e2497c3f0fe320341744a`
2. `deploy/Dockerfile.node` —
   `sha256:28f989781bcfce6373a6eff8d13e68334f742c528c35c42a7463fcf01edadd21`
3. `deploy/Dockerfile.ui` —
   `sha256:e562a3721c9750b747820f79b77c6d554be1d096d1f6a4dd0d371d83ce1aaa0a`
4. `deploy/hermes-node-bridge/Dockerfile` —
   `sha256:82d992e42fa471cea5bbbd92c28d593e17368561f4442ed518cf53b148c6ca5d`
5. `tests/test_container_image_runtime_readability.py` —
   `sha256:43295b57b2d7e368c5f6e735e812bc61349687aa84ee05b788a559fad9aab056`

The repair normalizes runtime readability and traversal only: `a+rX` cannot add write permission.
The one writable location is the exact owner-only Hermes scratch directory. The final runtime
identities remain non-root, and all readability assertions use valid unary tests with exactly one
operand. No Compose file or runtime snapshot behavior changed. The candidate passed 190 focused
tests, Ruff, strict mypy, exact-24-tool, no-new-powers, and agent-workflow checks. Those results are
review evidence only.

Attempt 008 permits one exact supervised child of the reviewed repair. Its ID is
`LV1-003-O4-ATTEMPT-008`. No
future child commit or tree is stated. The gate derives the candidate only after every check
passes and requires this exact seven-path control allowlist:

1. `Makefile`
2. `README.md`
3. `docs/codex/local-v1-lv1-003-o4-execution-authorization.json`
4. `docs/codex/local-v1-lv1-003-o4-execution-authorization.md`
5. `docs/codex/local-v1-lv1-003-o4-image-readability-repair-exact-review.md`
6. `scripts/local_v1_lv1_003_o4_execution_authorization_check.py`
7. `tests/test_local_v1_lv1_003_o4_execution_authorization_check.py`

The execution budget is one, `attempt_consumed` is false, and retry and automatic retry are false.
The sole operator command is `make local-v1-lv1-003-o4-producer-run`; its exact module command is
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. Any invocation outcome consumes Attempt
008 and requires an immediate separate post-attempt disposition.

At that Attempt 008 authorization point, exactly five bounded live authority fields were true:
producer code, Docker lifecycle, live Hermes, model-provider access, and O4 evidence execution. The
remaining 14 authority fields were false. Credential custody, runner lifecycle, arbitrary host
control, generic process control, shell execution, general Docker-socket product authority,
network/filesystem non-bypass claims, new powers, new tools, release, promotion, production, and UAT
remained unauthorized. This was invocation authority for the existing reviewed Make/module command
only, not a new product power or a claim that Attempt 008 would succeed.

## Attempt 008 Result And Closure

The exact candidate `ae6824bd6d81f58efc5a3383d63341d20ae3467a`, tree
`8e5a0d45369ca559e271aa3fd58c19e6bb57e33c`, was invoked once. Run
`20260726T001909Z-d801f37b` used project `ithildin-local-v1-o4-d801f37b`.

Both base and bridge builds completed, all four image identities were bound, and stage `7` was
reached. The primary failure was `subprocess_output_rejected`; the cleanup failure list is exactly
`[enrollment_outcome_ambiguous]`; the outward failure is `recovery_required`; and recovery remains
required.

Exact candidate code analysis identifies a deterministic code-path incompatibility. The Node CLI
enrollment result uses `NodeState.safe_summary()`, which always emits the key
`private_key_present`. The producer `_FORBIDDEN_OUTPUT` pattern contains `private[_ -]?key`, and
`_require_success()` applies that lexical scan before the enrollment JSON projection is parsed and
validated. This conclusion is supported by exact candidate source plus stage and return-path
evidence. It is not retained raw stdout proof: raw stdout was not inspected for this disposition,
no raw stdout is retained or quoted, and its exact bytes are not claimed.

Cleanup success is not claimed. No image ID, run image reference, container, volume, network,
runtime plaintext, or general Docker absence is claimed. The exact `0700` receipt root
`var/local-v1-lv1-003-o4-receipts/20260726T001909Z-d801f37b` retains:

- 119-byte disposition
  `sha256:03bceb292828f68440c2183438f856edd4b291130d6f276b9418a3d2ad967992`
- 7,174-byte diagnostic
  `sha256:cf303eb045cf522e62c5fa5b2f35fc54d5ecd5981e1c0c1428d4584d6a165b28`
- 96,772-byte manifest
  `sha256:04d64359cbc275181d90b50cef3534c550a0d7e446ae12caee3f5fe7bcb19c54`
- 664-file exact candidate snapshot

The durable disposition is
`docs/codex/local-v1-lv1-003-o4-attempt-008-disposition.json`. The closure accepts only a clean
direct child of the attempted candidate with the exact eight-path closure allowlist. Its next
action is a separately reviewed enrollment-output projection repair, not a retry. Recovery and
evidence deletion remain unauthorized. At this Attempt 008 closure, all 19 authority fields are
false.

## Enrollment-Output Projection Repair Review And Attempt 009 Authority

The durable exact review is
`docs/codex/local-v1-lv1-003-o4-enrollment-output-projection-repair-exact-review.md`.
Its rejected lineage records candidate
`dd96e47adba2baf49b890d821098e326bad93f84`, tree
`9e57f240ac65ffad38a66387648836bd1afdc489`, with one Medium finding (`M1`).
The final candidate `8cd307e3ce2ca20e6fdc1b53fc1937bfa5568685`, tree
`4dacc4015a51d61b29dc3e089900b2e12ab1d7b6`, received final disposition `GO` with
Critical: 0, High: 0, Medium: 0, Low: 0.

The final repair binds exactly five paths:

- `apps/node/src/ithildin_node/__main__.py`:
  `sha256:b7b3e9988f9351b25f24cf000f424bce1390cbb6be3010c41dce767987ac358d`
- `docs/codex/local-v1-lv1-003-o4-producer-contract.md`:
  `sha256:e972cf112ca0bc659f889cc50d2902d9d68137724e3f4d508bcc8e149d4af18b`
- `scripts/local_v1_lv1_003_o4_producer.py`:
  `sha256:cd5be3b081afda05a93ef29013a8d67bbac683d0f4118b77111939396c490bd4`
- `tests/test_local_v1_lv1_003_o4_producer.py`:
  `sha256:299fe6d8c5dbf1de2ebcdef1f745223d460b649312ad693a34bf7133a82c59d7`
- `tests/test_node_cli.py`:
  `sha256:8446ca4b6328d395cb93018ff765961a1ba81b9a5e2e7f5b690f712306abd100`

The Node CLI now emits a closed canonical projection with exactly three string fields: `node_id`,
`principal_id`, and `workspace_id`. The producer requires the derived principal semantics
`principal_id == agent:node.{node_id}`. It captures subprocess streams as bytes, performs strict
UTF-8 decoding, and validates the exact canonical projection without reintroducing
`private_key_present` or reflecting rejected bytes. Any repair-path drift, including Node CLI drift
outside the legacy runtime-path allowlist, fails the gate.

Attempt 009 is `LV1-003-O4-ATTEMPT-009`. The attempted candidate is
`26a003f7949e4bef5f3c0f66c9e1490b37103d9b`, tree
`a5403df311e3d6c7769a975d75433bca2442c435`; run
`20260726T014141Z-f6681bd3` used exact project
`ithildin-local-v1-o4-f6681bd3`. It ended at stage `4` with primary and outward failure code
`required_loopback_port_unavailable`. Base and bridge builds did not complete, bound image
identities and cleanup failure codes are exactly empty, and recovery is not required.

Exact producer order checks the required loopback port before snapshot validation and before
Docker, Compose, provider, or executor actions. This supports the bounded conclusion that no Docker
mutation occurred. The exact Attempt 009 runtime root is absent after cleanup. This closure does
not identify which port, a port owner or process, general loopback-port state, general runtime
absence, or general Docker state, and it does not inspect ambient credentials.

Attempt 009 is consumed. The execution budget is zero, `attempt_consumed` is true, retry and
automatic retry are false, and the immediate disposition is recorded. All 19 authority fields are
false.

Attempt 008 remains consumed with `recovery_required` and ambiguous enrollment. This authorization
makes no cleanup, revocation, image/container/volume/network/runtime absence, raw-stdout, or
evidence-deletion claim about Attempt 008. Its retained receipts and owner-only runtime posture
remain evidence, not authority.

## Historical Attempt Ceiling

The consumed Attempt 003 authorization limited the producer to one uniquely named isolated Compose project and
one server-owned `synthetic_read_review_v1` mission. It could create ephemeral local admin and enrollment
values, but they must remain in memory or owner-only anchored runtime files and must never be
printed, returned in receipts, or copied into evidence. The ordinary authenticated Node must become
eligible before mission admission. The same enrolled Node state may then be restarted through the
reviewed fixed overlay with `max_cycles=1`. Hermes may be invoked exactly once with no supplied
arguments after the fixed socket healthcheck succeeds.
Hermes stdout and stderr must be connected directly to `DEVNULL` when its subprocess is created.
They are never captured, materialized, scanned, returned, or persisted; only exit, timeout, or
interruption classification may survive.

Gateway mission detail and Gateway Agent Run detail/timeline are the only operation-correlation
authority. Runner-authored counts, runner prose, and model-provider output are never accepted as
Gateway evidence. Gateway truth, Node connectivity, runner-reported state, and provider state remain
separate.
For this journey, actual Gateway truth is mission lifecycle `runner_reported_succeeded`, Agent Run
record status `active`, and exactly two `tool.execution.completed` timeline events. Synthesizing
Agent Run completion is forbidden.

## Historical Build And Evidence Boundary

Attempt 001 would have had to produce actual bounded image artifact and repository-license source
inventories if it had entered the producer runtime.
Image config/layer metadata is not an SBOM. The candidate producer and assembler now use
`image_artifact_inventory_digest` and `license_source_inventory_digest`, preserve actual Gateway
Agent Run status `active`, and require exactly two distinctly identified Gateway completion events.
The independently reviewed runtime candidate remains byte-bound for Attempt 002; Attempt 001
remains consumed and is not reopened. The inventories are not placeholder hashes and do not claim
SBOM coverage, license completeness, compliance, provenance custody, or provider truth.
Static fake evidence proves closed private-snapshot enumeration and rejects observed path
replacement. It does not prove absence of transient malicious same-UID mutation while Docker reads
the build context; that threat remains outside the Local-v1 evidence boundary, consistent with the
golden-path limitation.

## Cleanup And Stop Lines

Cleanup must revoke the synthetic Node, tear down the exact Compose project with volumes, remove
only reconciled run-specific images, and prove project containers, volumes, network, persistent
profile volume, run-specific images, and runtime plaintext absent. Any ambiguity retains the
anchored runtime for recovery, reports `recovery_required`, and stops. There is no automatic retry.
Before invoking enrollment, the producer must record the attempt as ambiguous. A nonzero exit,
timeout, interruption, or malformed response before validated Node identity retains the exact
anchored runtime and Node volume, performs no destructive cleanup, and makes no revocation or
absence claim. Only validated identity clears ambiguity, and only a closed successful revocation
response confirms revocation. Post-rename report rollback is successful only when the public name
is absent or hidden-quarantined and the held base directory is durably synchronized; permission
removal alone is insufficient, and compound rollback or sync failure requires recovery.
If a validated Node ID exists but revocation is unavailable, invalid, or interrupted, destructive
cleanup is forbidden. The producer must write and verify one bounded owner-only secret-free
`node-revocation-recovery.json` containing the exact Node, project, and Node-volume identity needed
for reconciliation, attempt only the existing exact fixed-Node stop, and retain the Node volume and
anchored runtime. That private recovery receipt is quarantined staged material, not successful
published evidence; it contains no token, enrollment value, private key, prompt, provider output,
or raw tool result. Revocation, volume absence, runtime-plaintext absence, and full cleanup remain
unclaimed, and `recovery_required` remains true.

Ambient Docker hosts, contexts, configuration, credential helpers, registry credentials, proxy
variables, cloud credentials, arbitrary providers/models/tools/commands/arguments/paths, Docker
socket mounts, or host-control APIs are rejected.
Provider preflight was host-local only at `http://127.0.0.1:11434` and required the exact model
inventory entry `gemma4:e4b`. This closure makes no provider-route success or absence claim.

## Current Disposition

Attempts 001 through 009 are consumed. Attempt 003 image recovery is consumed and closed. Attempt
008's separately reviewed recovery sequence is closed in tracked dispositions without a cleanup,
full-project-removal, or general-absence claim. Attempt 009 has budget zero; its
`attempt_consumed` was true, and retry and automatic retry remain false.

Attempt 010 is consumed with execution budget zero. Its `attempt_consumed` is true, retry and
automatic retry are false, and its immediate post-attempt disposition is recorded. The review tag
`ithildin/lv1-003-o4-attempt010-reviewed` remains immutable at the exact attempted candidate commit
and tree, but grants no live authority.

Attempt 011 is consumed with execution budget zero. Its exact annotated review tag remains fixed at
the attempted candidate but grants no live authority. `attempt_consumed` is true; retry, automatic
retry, recovery, cleanup, and successor authority are false. Credential custody, runner lifecycle,
arbitrary host control, generic process control, shell execution, general Docker socket authority,
network/filesystem non-bypass claims, new powers, new tools, evidence deletion, release, promotion,
production, and UAT remain unauthorized. All 19 authority fields are false. The
24-tool/no-new-powers boundary is unchanged and the governed tool count remains exactly 24.

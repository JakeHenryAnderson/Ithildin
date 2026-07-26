# Local v1 LV1-003 O4 Execution Authorization Gate

Status:
`ATTEMPT_011_EXACT_CHILD_ONE_SHOT_EXECUTION_AUTHORIZED`

This record prepares fresh `LV1-003-O4-ATTEMPT-011` from the consumed Attempt 010 closure. Its
machine contract is
`docs/codex/local-v1-lv1-003-o4-execution-authorization.json`.

## Attempt 011 Exact One-Shot Authorization

The authorization candidate must be a clean, single-parent immediate child of
`0aee84f160fb3ce4d80a0772389d529594847013`, tree
`4041d61f4fd9685e7de3fe17c5a0c01e817693df`, whose sole parent is
`791894e007225090720ba2040c12628c09488adf`. It changes exactly these seven control paths:

1. `Makefile`
2. `README.md`
3. `docs/codex/local-v1-lv1-003-o4-execution-authorization.json`
4. `docs/codex/local-v1-lv1-003-o4-execution-authorization.md`
5. `docs/codex/local-v1-lv1-003-o4-fixed-node-start-diagnostic-exact-review.md`
6. `scripts/local_v1_lv1_003_o4_execution_authorization_check.py`
7. `tests/test_local_v1_lv1_003_o4_execution_authorization_check.py`

The producer and its tests must remain byte-identical to the exact reviewed parent, with digests
`sha256:2edf9f36f15b1126d60e64863d2c1430509f099cada7a821e952288d90349d76` and
`sha256:9d276d4e5c71ba84885415f4ec5646a36afb25baaa695400a68952e8051e6690`.
The durable review is
`docs/codex/local-v1-lv1-003-o4-fixed-node-start-diagnostic-exact-review.md`. It records final
`GO`, Critical 0, High 0, Medium 0, and Low 0 after the intermediate M1 and L1 findings were fixed.
Relative to MCC-authorized runtime tip `8cd307e3ce2ca20e6fdc1b53fc1937bfa5568685`, only
`scripts/local_v1_lv1_003_o4_producer.py` and
`tests/test_local_v1_lv1_003_o4_producer.py` may differ among allowed runtime paths.

Before the future annotated, nonforce tag
`ithildin/lv1-003-o4-attempt011-reviewed` peels to the exact authorization candidate commit and
tree, the gate is invalid, the execution budget collapses to zero, and all live authority fields
collapse to false. After every check passes and that exact tag exists, the fresh attempt budget is
one, `attempt_consumed` is false, retry and automatic retry are false, and exactly the five
existing bounded authority fields are true: existing producer code, its closed Docker lifecycle,
live Hermes execution, model-provider access, and O4 evidence execution. The other 14 authority
fields remain false. The existing sole operator entrypoint and exact module command remain
`make local-v1-lv1-003-o4-producer-run` and
`uv run python -m scripts.local_v1_lv1_003_o4_producer`.

Any invocation consumes Attempt 011 and requires an immediate tracked disposition; it is never an
automatic retry. This authorization adds no governed tool or power, authorizes no arbitrary host,
shell, generic process, general Docker-socket, credential, promotion, production, release, or UAT
action, and does not itself execute Attempt 011. The governed tool count remains exactly 24.

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
refer only to the Attempt 011 authorization parent
`0aee84f160fb3ce4d80a0772389d529594847013`, tree
`4041d61f4fd9685e7de3fe17c5a0c01e817693df`. Attempt 010 remains explicit consumed historical
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

Attempt 011 is a fresh successor, not retry, recovery, or cleanup authority. Before its exact
annotated review tag, its budget is zero and all 19 authority fields are false. After exact review
and tag binding, only the existing five bounded live fields are true and the other 14 remain false.
Any invocation consumes the one-shot budget and requires immediate disposition. Credential custody,
runner lifecycle, arbitrary host control, generic process control, shell execution, general Docker
socket authority, network/filesystem non-bypass claims, new powers, new tools, evidence deletion,
release, promotion, production, and UAT remain unauthorized. The 24-tool/no-new-powers boundary is
unchanged and the governed tool count remains exactly 24.

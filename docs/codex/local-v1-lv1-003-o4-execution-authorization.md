# Local v1 LV1-003 O4 Execution Authorization Gate

Status: `ATTEMPT_005_CONSUMED_API_EXIT_DIAGNOSTIC_REQUIRED_NO_LIVE_AUTHORITY`

This gate preserves all five consumed attempt histories, the consumed and closed Attempt 003 image
recovery, and the consumed Attempt 005 failure evidence. It authorizes no execution, retry,
recovery action, evidence deletion, release, promotion, production action, or UAT action. Its
machine contract is
`docs/codex/local-v1-lv1-003-o4-execution-authorization.json`.

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
refer only to the current Attempt 005 closure parent
`affba0570ae15e897f92629966d445ad563ec5ff`, tree
`8b262e7efa55db72b5402f6924ec938e2d06d85f`. The reviewed runtime-native repair
`49db93d80a71855d9ae223826a9849749377c376`, tree
`23950855584316daba76acd65be0bfdfd20fbcb9`, remains the explicit historical Attempt 004
authorization parent. The older
`86e75f0cf7f92ceb33218f2a66a00668f4da9e12`, tree
`11d9a752b8e08b483e1d8b9a347a06b5d8bf9af7`, remains explicit historical post-review lineage and
code-authorization identity only; it is not the current execution candidate parent.

The machine contract names all inherited Attempt 001 lineage with explicit `attempt_001_*` keys.
Those fields are historical only. The validator's public current-attempt fields bind the consumed
Attempt 005 candidate while Attempts 001 through 004 remain explicit history, so generic report
labels cannot silently substitute Attempt 001 for the current attempt.

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

Attempts 001 through 005 are consumed. Attempt 003 image recovery is consumed and closed. The
Attempt 005 budget is zero, retry and automatic retry are false, and all 19 authority fields are
false.

Credential custody, runner lifecycle, arbitrary host control, generic process control, shell
execution, general Docker socket authority, network/filesystem non-bypass claims, new powers, new
tools, evidence deletion, release, promotion, production, and UAT remain unauthorized. The
24-tool/no-new-powers boundary is unchanged and the governed tool count remains exactly 24.

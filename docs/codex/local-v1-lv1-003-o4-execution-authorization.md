# Local v1 LV1-003 O4 Execution Authorization Gate

Status: `ATTEMPT_CONSUMED_PRE_GATE_IMPORT_FAILURE`

This is the closed execution gate after the sole supervised Local-v1 `O4` invocation was consumed.
Its machine contract is
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

## Historical Attempt Ceiling

The consumed authorization limited the producer to one uniquely named isolated Compose project and
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
The independently reviewed code-only candidate was usable only for the now-consumed supervised
attempt when the dynamic immediate-child gate passed. The inventories are not placeholder hashes
and do not claim SBOM coverage, license completeness, compliance, provenance custody, or provider
truth.
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
Provider preflight is host-local only at `http://127.0.0.1:11434` and must confirm the exact model
inventory entry `gemma4:e4b`. Container routing through `host.docker.internal` remains unknown until
the sole attempt; a routing failure consumes that attempt and permits no retry.

## Current Disposition

`producer_code_authorized`, `docker_lifecycle_authorized`, `live_hermes_execution_authorized`,
`model_provider_access_authorized`, and `o4_evidence_execution_authorized` are now false. Every other
authority field is also false. The attempt budget is zero. Release, promotion, production, UAT,
credential custody, runner lifecycle, arbitrary host control, generic process control, shell
execution, Docker socket access, non-bypass claims, new powers, and new tools remain unauthorized.
The governed tool count remains exactly 24.

No retry is authorized. A retry requires a repaired candidate, independent exact review of that
candidate, and a separate post-review execution disposition. Repairing the import path does not
restore the consumed authority. A descendant control-only commit may record this closure; this
document does not bind or derive its own closure commit or tree.

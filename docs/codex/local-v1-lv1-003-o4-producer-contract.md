# Local v1 LV1-003 O4 Producer Contract

Status: `entrypoint_repair_candidate_pending_exact_review_and_separate_attempt_disposition`

This contract defines the only acceptable live producer for the fixed `MCC-007` bridge. The
candidate producer and reconciled assembler now implement this contract with injected, fake-tested
external seams. That implementation does not authorize Docker, API, provider, network, credential,
Hermes, Node, or `O4` execution. Attempt 001 is consumed after the failed file-path invocation, and
the separate execution-authorization contract has attempt budget zero until a repaired candidate
receives independent exact review and a separate new-attempt disposition.

The candidate constrained-mission assembler now preserves the authoritative Gateway Agent Run
status `active`, requires exactly two distinctly identified Gateway `tool.execution.completed`
events, and names bounded image metadata `image_artifact_inventory_digest`. It remains unusable for
live producer evidence until this producer-and-assembler candidate receives independent exact review
and the separate execution gate binds that exact candidate with attempt budget one.

## Entry Gate

The only supported operator entrypoint is:

```text
make local-v1-lv1-003-o4-producer-run
```

Its exact live, gate-protected recipe is
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. The failed file-path command
`uv run python scripts/local_v1_lv1_003_o4_producer.py` is not an authorized future entrypoint.
Importing the module does not execute `main`.

The producer must observe a clean candidate commit and tree, then call the execution-authorization
validator before it creates a runtime directory or performs Docker, API, provider, network, or
credential work. The validator must bind that exact commit/tree to an independent exact review and
a separate post-review disposition with an attempt budget of exactly one. Refusal is a stable safe
error and performs zero executor, API, provider, or runtime-filesystem calls. The current consumed
Attempt 001 disposition refuses this repaired entrypoint; the Make target itself does not grant
retry authority.

## Closed State Machine

One invocation has these exact ordered stages:

1. Observe the clean exact candidate and pass the separate execution gate.
2. Reject ambient Docker host/context/config, credential-helper, registry-auth, proxy, cloud-key,
   and provider/model variables.
3. Create a unique `ithildin-local-v1-o4-<8 lowercase hex>` Compose project, a descriptor-anchored
   owner-only `0700` runtime, and an independent owner-only `0700` receipt directory. Materialize
   the exact authorized Git tree's bounded build/config inputs into a descriptor-anchored private
   snapshot using verified Git blob identities; candidate files are owner-readable `0400` or
   executable `0500`, every snapshot directory is sealed owner-readable `0500`, and recursive
   descriptor-relative enumeration must equal the exact directory and file manifests. Extra files,
   directories, symlinks, or special entries fail closed before any whole-directory build copy.
   Static tests prove snapshot enumeration and path-replacement rejection only. They do not prove
   absence of transient malicious same-UID mutation while Docker reads the build context; that
   threat remains outside the Local-v1 evidence boundary, aligned with the golden-path limitation.
4. Write only owner-controlled `0600` Compose environment, override, Docker configuration, signing
   key, authority placeholder, and staged receipt files. Ephemeral admin and enrollment values are
   never emitted. All candidate workspace/profile/config reads come from the private snapshot.
5. Prove one local Docker socket, Docker/Compose availability, free loopback ports `8000` and
   `5173`, exact snapshot source/profile digests, merged Compose build contexts and bind sources
   confined to the private snapshot/runtime, host-local Ollama reachability at
   `http://127.0.0.1:11434`, and exact host model inventory entry `gemma4:e4b`. Container routing
   through `host.docker.internal` remains a runtime-only fact for the sole Hermes attempt.
6. Prove all four unique image references absent, then explicitly build the base API/UI/Node images
   and reviewed fixed Hermes bridge image.
7. Inspect exact image reference, ID, platform, config digest, and ordered layer digests. Record that
   bounded image metadata only as `image_artifact_inventory_digest`, never as an SBOM. Build the
   license-source inventory from the exact private snapshot with no-follow reads and a fixed size ceiling;
   current discovery is exactly `pyproject.toml` and `uv.lock`, with zero tracked `LICENSE*`,
   `NOTICE*`, or `COPYING*` files. Mark complete SBOM, license completeness, compliance, custody,
   and provider truth claims false.
8. Start only base API/UI, prove their closed health projections, enroll one Node once through stdin,
   assign and acknowledge one signed configuration, and start the ordinary Node. Immediately before
   the enrollment subprocess, record `enrollment_attempted=true` and
   `enrollment_outcome_ambiguous=true`; clear ambiguity only after the returned Node identity,
   principal, and workspace are closed and validated.
9. Prove Gateway-derived identity, workspace, signed configuration, and ordinary Node eligibility
   while runner and provider health remain unknown.
10. Admit exactly one server-owned `synthetic_read_review_v1` mission with one run-bound idempotency
    key. No objective, operations, arbitrary payload, or second admission is allowed.
11. Stop the ordinary Node.
12. Restart the same enrolled state through the reviewed fixed overlay with `max_cycles=1` and wait
    for the exact Unix-socket healthcheck.
13. Invoke the fixed Hermes service exactly once through Compose `run --rm -T --no-deps hermes`
    with no additional arguments. At subprocess creation, route stdout and stderr directly to
    `DEVNULL`; neither stream may be materialized, scanned, returned, or included in exceptions.
    Retain only exit, timeout, or interruption classification. Increment the attempt counter before
    invocation. Container-to-`host.docker.internal` routing failure consumes that sole attempt.
    There is no automatic retry after success, failure, timeout, interruption, routing failure, or
    ambiguous result. Future fake negative tests must prove both streams are `DEVNULL` and cannot
    enter memory or evidence.
14. Query `GET /missions/{mission_id}` and exactly one correlated `GET /runs/{run_id}` detail.
    Gateway truth is the mission lifecycle `runner_reported_succeeded`, the Agent Run record status
    `active`, and exactly two distinct `tool.execution.completed` timeline events bound to
    `project.structure.summary` then `project.test.summary`. Preserve `active`; never synthesize
    `completed`, and never trust runner-authored operation counts or output.
15. Copy and validate only the closed Node mission receipt needed for the handoff nonce digest. It
    cannot override Gateway mission, claim, run, request, tool, count, lifecycle, or status truth.
16. Revoke the Node. Only a closed, shape-valid successful revocation response permits the complete
    cleanup path: stop the fixed Node, tear down the exact project with volumes, reconcile and remove
    only the exact inspected run-specific images, and prove project containers, volumes, network,
    profile volume, images, and runtime plaintext absent. If revocation is unavailable, invalid, or
    interrupted, write and re-read one bounded owner-only secret-free recovery identity receipt,
    attempt only the existing exact fixed-Node stop, retain the Node volume and anchored runtime,
    and require recovery without claiming full cleanup.
17. Write closed `0600` build and journey receipts into private staging, then invoke only the
    reconciled constrained-mission assembler and checker against the same exact snapshot. Publish
    the complete checked JSON/Markdown report with one descriptor-relative atomic rename; an
    assembler, checker, write, or signal failure leaves no success-shaped report and retains an
    explicit quarantined or verified-but-not-published disposition. Their schema must use
    `image_artifact_inventory_digest`, `license_source_inventory_digest`, Agent Run status `active`,
    exactly two Gateway `tool.execution.completed` events, and mission lifecycle
    `runner_reported_succeeded`. Static fake tests do not authorize this live stage.

Any out-of-order transition, duplicate stage, unknown response field used as authority, or second
Hermes call fails closed.

## Exact Command Shapes

Every Docker call uses a tuple built internally; no caller supplies a command, argument, path,
provider, model, service, profile, tool, or image. Dynamic values are limited to the validated run
ID, derived unique project, descriptor-anchored paths, unique image references, and exact inspected
image IDs.

The only Compose files are private exact-candidate snapshot copies of
`deploy/docker-compose.yml` and the reviewed `deploy/hermes-node-bridge/compose.yaml`, plus one
generated owner-only override. The override replaces every base API bind target with an exact
private-snapshot or private-runtime source. The initial
API/UI/ordinary-Node stages omit the reviewed overlay. Fixed-bridge stages add that overlay before
the generated override. Allowed command tails are exactly the action vocabulary in the JSON gate:
version/config checks, explicit builds, bounded image metadata inspection, API/UI start, one stdin enrollment,
ordinary Node start/stop, reviewed fixed Node start with wait, one no-argument Hermes run, closed
Node-receipt copy, fixed Node stop, project down with orphan/volume removal, project resource
queries, exact owned-image removal, and absence queries.

No `exec`, shell, arbitrary `run` argument, logs, Docker socket mount, registry login/pull/push,
system prune, generic container ID, broad label deletion, ambient Compose project, or host path
outside the anchored runtime/private exact-candidate snapshot is allowed.

## Closed API Operations

The producer may issue only:

- unauthenticated `GET /healthz`;
- authenticated `GET /system/status`, `GET /workspaces`, and `GET /nodes/{node_id}`;
- authenticated `POST /nodes/enrollment-codes`;
- authenticated `POST /nodes/{node_id}/configurations` and
  `POST /nodes/{node_id}/revoke`;
- authenticated `POST /missions`;
- authenticated `GET /missions/{mission_id}`; and
- authenticated `GET /runs/{run_id}`.

Admission is exactly one object with the eligible Node ID, template
`synthetic_read_review_v1`, timeout `300`, and the run-derived client request ID. Node
configuration remains the existing fixed Local-v1 assignment. HTTP uses a proxy-free,
redirect-denying local opener and closed projections; response bodies, headers, enrollment value,
admin value, prompt, model output, raw tool results, and subprocess output are not evidence. The
host-local Ollama preflight uses only `127.0.0.1:11434`; it does not claim that container
`host.docker.internal` routing works.

## Receipt Contracts

The producer-and-assembler candidate replaces the prior build-receipt schema and binds
candidate
commit/tree, clean observations around both builds, current bridge/Node/lock/profile source
digests, pinned Hermes OCI/platform digests, actual inspected bridge and Node image IDs, platform,
and canonical digests of:

- `image_artifact_inventory_digest`: bounded metadata containing exact reference, image ID,
  platform, config digest, and ordered layer digests for the four run-specific images; and
- `license_source_inventory_digest`: an exact-candidate private-snapshot inventory produced with
  no-follow, size-limited reads. Current discovery records exactly `pyproject.toml` and `uv.lock`, plus zero
  tracked `LICENSE*`, `NOTICE*`, or `COPYING*` files.

Image config/layer metadata is not an SBOM. Both inventories declare SBOM completeness, license
completeness, and compliance claims false.

The journey receipt preserves the Gateway Agent Run status `active`, exactly two
Gateway `tool.execution.completed` events, and mission lifecycle `runner_reported_succeeded`.
Mission, claim, envelope, correlated run, session, request IDs, tool names, and lifecycle come from
the Gateway mission/run projections. No synthesized run completion is allowed. The closed Node
receipt supplies only the handoff-nonce digest after its mission/claim/envelope binding matches
Gateway truth. Cleanup fields become true only after direct absence probes.

## Cleanup And Recovery

Cleanup runs once from the first post-gate filesystem creation, including prepare, socket,
executor-factory, API-factory, and controlled-signal failures. Every independently safe exact-owned
revocation, stop, down, resource probe, inspected-image removal, image probe, and descriptor-relative
plaintext removal is attempted monotonically; one failure never suppresses later safe cleanup.
Before the first Docker mutation milestone, cleanup performs only descriptor-owned local plaintext
removal and makes zero Docker, API, or provider calls. Docker cleanup becomes eligible only after
the producer records that mutation may have begun; enrollment and admission are separately tracked.
An enrollment subprocess nonzero exit, timeout, interruption, or malformed response before a
validated Node ID leaves `enrollment_outcome_ambiguous=true`, makes no revocation or absence claim,
performs no destructive project, volume, image, or runtime cleanup, and retains the exact anchored
runtime and Node volume for reconciliation. Only a validated Node identity clears enrollment
ambiguity, and only a later closed successful revocation response confirms Node revocation.
When a shape-valid Node ID is known but revocation is unavailable, invalid, or interrupted, cleanup
writes and verifies `node-revocation-recovery.json` in the owner-only anchored receipt directory.
The closed receipt contains only schema/kind, run and exact-candidate identity, workspace and Node
identity, derived Compose project and Node-volume names, false revocation/release/UAT claims,
retention booleans, and one fixed reconciliation next action; it contains no token, enrollment
value, private key, prompt, output, or model-provider material and is never published as successful
evidence. The producer then attempts the exact fixed-Node stop but skips project down, absence
claims, image removal, and runtime deletion. Thus `node_revoked`, `volumes_absent`,
`persistent_profile_volume_absent`, `runtime_plaintext_absent`, and full cleanup remain false and
`recovery_required` remains true.
Revocation failure, image-identity ambiguity, resource residue, volume residue, runtime removal
failure, or source-anchor replacement sets `recovery_required`. No ambiguous or broad deletion is
allowed. Staged receipts remain non-success evidence until assembler/checker equality and atomic
publication. A failure or signal after rename removes or quarantines the exact public run-ID object
through its held descriptors, and rollback succeeds only after the exact public name is absent or
hidden-quarantined and the held report-base directory is durably synchronized. Permission removal
alone is never rollback success; removal-plus-quarantine failure or directory-sync failure requires
`report_publication_recovery_required`. The returned report path is revalidated against the anchored
report base. Failures carry an explicit non-release, non-UAT quarantine disposition.

The producer never declares release, promotion, production, UAT, non-bypass, sandbox, provider
truth, output correctness, or process-stop evidence.

## Runtime-Only Facts Still Unproven

This static implementation and its fake tests cannot establish Docker/Compose availability, merged profile
behavior on the target host, local Ollama reachability, `gemma4:e4b` presence, image build success,
actual OCI platform selection, container routing from Hermes to
`host.docker.internal:11434`, socket ownership/health, Hermes behavior, Gateway mission outcome,
artifact inventory values, or residue-free cleanup. A container routing failure consumes the sole
attempt and permits no retry. Those facts require the later exact-reviewed, separately authorized
one-attempt run. The sealed private snapshot and descriptor checks reject observed static drift and
path replacement, but they do not establish operating-system immutability or exclude a malicious
same-UID process mutating content transiently during Docker's whole-context read.

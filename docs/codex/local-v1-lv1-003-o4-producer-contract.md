# Local v1 LV1-003 O4 Producer Contract

Status: `design_blocked_on_assembler_reconciliation_pending_implementation_and_exact_review`

This contract defines the only acceptable future live producer for the fixed `MCC-007` bridge. It
does not implement the producer and does not authorize Docker, API, provider, network, credential,
Hermes, Node, or `O4` execution. The separate execution-authorization contract remains
`PREPARE_REVIEW`.

The current constrained-mission assembler is not usable by this future producer. It requires a
synthesized Agent Run status of `completed` even though the authoritative Gateway Agent Run record
remains `active`, and it names image metadata as `sbom_digest`. Before any live authority, the
future exact producer-and-assembler candidate must change the assembler schema, checker, renderer,
and tests to preserve actual Gateway truth and accurate artifact-inventory terminology.

## Entry Gate

The producer must observe a clean candidate commit and tree, then call the execution-authorization
validator before it creates a runtime directory or performs Docker, API, provider, network, or
credential work. The validator must bind that exact commit/tree to an independent exact review and
a separate post-review disposition with an attempt budget of exactly one. Refusal is a stable safe
error and performs zero executor, API, provider, or runtime-filesystem calls.

## Closed State Machine

One invocation has these exact ordered stages:

1. Observe the clean exact candidate and pass the separate execution gate.
2. Reject ambient Docker host/context/config, credential-helper, registry-auth, proxy, cloud-key,
   and provider/model variables.
3. Create a unique `ithildin-local-v1-o4-<8 lowercase hex>` Compose project, a descriptor-anchored
   owner-only `0700` runtime, and an independent owner-only `0700` receipt directory.
4. Write only owner-controlled `0600` Compose environment, override, Docker configuration, signing
   key, authority placeholder, and receipt files. Ephemeral admin and enrollment values are never
   emitted.
5. Prove one local Docker socket, Docker/Compose availability, free loopback ports `8000` and
   `5173`, exact source/profile digests, host-local Ollama reachability at
   `http://127.0.0.1:11434`, and exact host model inventory entry `gemma4:e4b`. Container routing
   through `host.docker.internal` remains a runtime-only fact for the sole Hermes attempt.
6. Prove all four unique image references absent, then explicitly build the base API/UI/Node images
   and reviewed fixed Hermes bridge image.
7. Inspect exact image reference, ID, platform, config digest, and ordered layer digests. Record that
   bounded image metadata only as `image_artifact_inventory_digest`, never as an SBOM. Build the
   license-source inventory from the tracked Git tree with no-follow reads and a fixed size ceiling;
   current discovery is exactly `pyproject.toml` and `uv.lock`, with zero tracked `LICENSE*`,
   `NOTICE*`, or `COPYING*` files. Mark complete SBOM, license completeness, compliance, custody,
   and provider truth claims false.
8. Start only base API/UI, prove their closed health projections, enroll one Node once through stdin,
   assign and acknowledge one signed configuration, and start the ordinary Node.
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
16. Revoke the Node, stop the fixed Node, tear down the exact project with volumes, reconcile and
    remove only the exact inspected run-specific images, and prove project containers, volumes,
    network, profile volume, images, and runtime plaintext absent.
17. Write closed `0600` build and journey receipts, then invoke only the future reconciled
    constrained-mission assembler and checker from the same exact candidate. Their schema must use
    `image_artifact_inventory_digest`, `license_source_inventory_digest`, Agent Run status `active`,
    exactly two Gateway `tool.execution.completed` events, and mission lifecycle
    `runner_reported_succeeded`. The current assembler/checker cannot satisfy this stage.

Any out-of-order transition, duplicate stage, unknown response field used as authority, or second
Hermes call fails closed.

## Exact Command Shapes

Every Docker call uses a tuple built internally; no caller supplies a command, argument, path,
provider, model, service, profile, tool, or image. Dynamic values are limited to the validated run
ID, derived unique project, descriptor-anchored paths, unique image references, and exact inspected
image IDs.

The only Compose files are `deploy/docker-compose.yml`, the reviewed
`deploy/hermes-node-bridge/compose.yaml`, and one generated owner-only override. The initial
API/UI/ordinary-Node stages omit the reviewed overlay. Fixed-bridge stages add that overlay before
the generated override. Allowed command tails are exactly the action vocabulary in the JSON gate:
version/config checks, explicit builds, bounded image metadata inspection, API/UI start, one stdin enrollment,
ordinary Node start/stop, reviewed fixed Node start with wait, one no-argument Hermes run, closed
Node-receipt copy, fixed Node stop, project down with orphan/volume removal, project resource
queries, exact owned-image removal, and absence queries.

No `exec`, shell, arbitrary `run` argument, logs, Docker socket mount, registry login/pull/push,
system prune, generic container ID, broad label deletion, ambient Compose project, or host path
outside the anchored runtime is allowed.

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

The future producer-and-assembler candidate must replace the current build-receipt schema and bind
candidate
commit/tree, clean observations around both builds, current bridge/Node/lock/profile source
digests, pinned Hermes OCI/platform digests, actual inspected bridge and Node image IDs, platform,
and canonical digests of:

- `image_artifact_inventory_digest`: bounded metadata containing exact reference, image ID,
  platform, config digest, and ordered layer digests for the four run-specific images; and
- `license_source_inventory_digest`: a tracked-Git-tree inventory produced with no-follow,
  size-limited reads. Current discovery records exactly `pyproject.toml` and `uv.lock`, plus zero
  tracked `LICENSE*`, `NOTICE*`, or `COPYING*` files.

Image config/layer metadata is not an SBOM. Both inventories declare SBOM completeness, license
completeness, and compliance claims false.

The future journey receipt must preserve the Gateway Agent Run status `active`, exactly two
Gateway `tool.execution.completed` events, and mission lifecycle `runner_reported_succeeded`.
Mission, claim, envelope, correlated run, session, request IDs, tool names, and lifecycle come from
the Gateway mission/run projections. No synthesized run completion is allowed. The closed Node
receipt supplies only the handoff-nonce digest after its mission/claim/envelope binding matches
Gateway truth. Cleanup fields become true only after direct absence probes.

## Cleanup And Recovery

Cleanup runs once in a `finally` path after any mutation. Revocation failure, image-identity
ambiguity, resource residue, volume residue, runtime removal failure, or source-anchor replacement
sets `recovery_required`. Ambiguous resources are retained for operator recovery rather than
broadly removed. Successful cleanup removes runtime plaintext only after extracting closed
non-secret receipts into the independent receipt directory.

The producer never declares release, promotion, production, UAT, non-bypass, sandbox, provider
truth, output correctness, or process-stop evidence.

## Runtime-Only Facts Still Unproven

Static implementation and fake tests cannot establish Docker/Compose availability, merged profile
behavior on the target host, local Ollama reachability, `gemma4:e4b` presence, image build success,
actual OCI platform selection, container routing from Hermes to
`host.docker.internal:11434`, socket ownership/health, Hermes behavior, Gateway mission outcome,
artifact inventory values, or residue-free cleanup. A container routing failure consumes the sole
attempt and permits no retry. Those facts require the later exact-reviewed, separately authorized
one-attempt run.

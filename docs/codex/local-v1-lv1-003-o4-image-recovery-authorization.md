# Local v1 LV1-003 O4 Attempt 003 Image Recovery Authorization

Status: `AUTHORIZE_ATTEMPT_003_IMAGE_RECOVERY_ONE_SHOT_IMMEDIATE_CHILD`

This is a recovery-only authorization. It is not Attempt 004 and does not reopen O4 execution,
release, promotion, production, or UAT authority.

## Exact Candidate Binding

The authorization parent is commit `e703237fb22355c1ebc5aee509b6301970812dc3`, tree
`2fd7bdd86b2e2d37ecf7d1b9607c988fef6b5446`. The exact Attempt 003 closure bindings are:

- JSON:
  `sha256:2dec56200e564decd398fd5c0e1539e60e1c87ebaf453c7093346ca61155db8a`
- Markdown:
  `sha256:b91cc06f5e88b35a4df18299405c60fa3868303d40c17d900ee101720feffe56`

No future child commit or tree is stated. The static gate derives authority only for a clean,
single-parent immediate child whose committed diff is exactly the five-path recovery allowlist.
All other paths remain byte-identical to the parent.

## Fixed Operator Entry Point

The only operator command is:

```text
make local-v1-lv1-003-o4-image-recovery-run
```

Its exact no-argument module command is
`uv run python -m scripts.local_v1_lv1_003_o4_image_recovery`. Arguments, stdin data, concurrent
invocations, and automatic retries are unauthorized. The Make target remains outside release,
milestone, static, producer, and O4-authorization dependencies.

Before any Docker socket, metadata, resource, or image inspection and before any Docker mutation,
the fixed process must consume the recovery budget durably. It descriptor-anchors the repository,
`var`, and the existing owner-only `0700` `var/local-v1-lv1-003-o4-runtime` directory; requires that
runtime base to be empty; and atomically creates
`attempt-003-image-recovery-001-consumed.json` with `O_EXCL` and no-follow flags.

The exact owner-only `0600` receipt contains only the recovery ID, dynamically derived current
candidate commit and tree, status `consumed_before_docker_inspection`, and retry false. The process
fsyncs the file and runtime directory before continuing. Any existing receipt or any other runtime
entry permanently refuses concurrent or subsequent recovery start. The receipt remains after every
preflight, inspection, removal, postverification, interruption, or local-runtime failure and is not
successful O4 evidence. Receipt deletion is not authorized.

## Exact Recovery Target

The recovery process is bound to Compose project `ithildin-local-v1-o4-6460809b`, run
`20260725T125344Z-6460809b`, platform `linux/arm64`, and Compose version label `5.1.4`.
It may inspect only the exact project resources, exact run image references, exact image IDs, and
ancestor-container relationships needed for this recovery.

The three removal targets, in fixed order, are:

1. `ithildin/api-o4:6460809b` —
   `sha256:19dc658884e9298b7966e5fb10c80874afaa33956e565b55dd0a30e8a02bd5d6`
2. `ithildin/ui-o4:6460809b` —
   `sha256:4b530eb0fc350c433089d88ddd75d03042e633a5b23a0fdeaaeb77c58f75b6b7`
3. `ithildin/node-o4:6460809b` —
   `sha256:0d85000f6172508554524f276d4051170e53a6c3fc79cbc5dc1b0c051b682c81`

Each image must have exactly its one stated tag, the exact project label, its exact service label,
Compose version label `5.1.4`, and zero ancestor containers. The Hermes reference
`ithildin/hermes-node-bridge-o4:6460809b` and exact-project containers, volumes, and networks must
remain absent.

## Runtime Boundary

The fixed process rejects ambient Docker host/context/config, Compose project, proxy, registry,
cloud, model-provider, and credential authority. It proves one unique default local Docker socket
and uses an owner-only temporary Docker configuration containing no authentication or credential
helper configuration.

Immediately before mutation, the same process revalidates every full ID, sole tag, required label,
platform, ancestor-container absence, Hermes-tag absence, and exact-project resource absence. Any
missing target, drift, ambiguity, extra tag, label mismatch, platform mismatch, container
reference, resource presence, query error, or forbidden output stops before mutation.

The only mutation command is one non-force command:

```text
docker --config <owner-only-empty-config> image rm <api-full-id> <ui-full-id> <node-full-id>
```

All three explicit full IDs must occur exactly once and in fixed order. Force, prune, tag-based
removal, project-resource mutation, arbitrary Docker arguments, and raw subprocess output are
forbidden. A nonzero, timeout, unavailable, or ambiguous removal result is a stable recovery
failure and grants no retry. Once a removal call may have started, the process always attempts the
same bounded read-only postverification before returning failure.

After the command, read-only checks must prove the three IDs and three tags absent, Hermes still
absent, and exact-project containers, volumes, and networks still absent. Success is reported only
when all postconditions pass. Output is limited to stable secret-free status or error codes.

## Authority And Evidence Limits

The recovery budget is one and retry is false. Only
`durable_consumption_receipt_authorized`, `recovery_inspection_authorized`, and
`exact_image_removal_authorized` are true. All 19 O4 authority fields remain false. The filesystem
authority is limited to creating and fsyncing that one exact receipt in the already-existing empty
runtime base. This record does not authorize receipt removal, other filesystem mutation, Docker
lifecycle generally, provider or Hermes access, project resource mutation, arbitrary host control,
new governed powers, or a new governed tool.

Separate Docker CLI inspection and removal cannot prove absence of same-host, same-user mutation in
the interval between calls. The single fixed process minimizes that TOCTOU interval but does not
claim atomic inspection/removal, Docker non-bypass, general Docker absence, or adversarial
same-user exclusion.

The durable receipt prevents a cooperative second invocation from consuming the same budget, but it
is not claimed atomic with Docker action, tamper-proof, filesystem non-bypass, or proof against an
adversarial same-user process.

This recovery creates no successful O4 evidence and does not complete release or UAT.

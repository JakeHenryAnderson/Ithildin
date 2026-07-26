# Local v1 LV1-003 O4 Fixed-Node Startup Diagnostic Exact Review

Status: `GO`

Date: 2026-07-26

## Exact Candidate

- Commit: `0aee84f160fb3ce4d80a0772389d529594847013`
- Tree: `4041d61f4fd9685e7de3fe17c5a0c01e817693df`
- Parent commit: `791894e007225090720ba2040c12628c09488adf`
- Full diagnostic base commit: `0973319499de5c509c03b398de5504b219ffce58`
- Full diagnostic base tree: `1e56d647c9c67c5ff9c17a0f35ea5fd4bb34bd69`
- `scripts/local_v1_lv1_003_o4_producer.py`:
  `sha256:2edf9f36f15b1126d60e64863d2c1430509f099cada7a821e952288d90349d76`
- `tests/test_local_v1_lv1_003_o4_producer.py`:
  `sha256:9d276d4e5c71ba84885415f4ec5646a36afb25baaa695400a68952e8051e6690`

Relative to the full diagnostic base, the exact candidate changes only those two runtime paths.

## Review Lineage And Result

The intermediate candidate `791894e007225090720ba2040c12628c09488adf`, tree
`2a2516fff6ae24996d55c6d1f19d9bdaee742f64`, received `NO_GO` with one Medium
finding (`M1`) and one Low finding (`L1`).

- `M1`: a post-bind or pre-discard anchor-validation failure could leave the diagnostic container
  identity bound after the diagnostic should have relinquished it.
- `L1`: a successful fixed-Node start result did not pass through the existing forbidden-output
  validation before Hermes could run.

The exact candidate rolls back the bound container identity on post-bind validation failure,
discards it despite a pre-discard anchor failure, and applies the existing success-output check
before advancing to Hermes. The final independent read-only review found:

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The exact-commit disposition is `GO`. The earlier `M1` and `L1` remain durable rejected-candidate
history; they are resolved only in the exact final candidate.

## Reviewed Diagnostic Boundary

The diagnostic is reachable only immediately after the exact fixed-overlay
`compose up --detach --no-deps --wait ithildin-node` returns nonzero at completed stage 11 and
before the existing one-time cleanup. Its fixed action is
`collect_bounded_fixed_node_start_diagnostic_on_wait_failure`, and it collects at most once:

1. the exact fixed-overlay Compose `ps --all --quiet ithildin-node` query;
2. one scalar `docker container inspect` for the single exact validated 64-character container
   identity, bound only while that inspect is authorized and then discarded; and
3. one already-allowlisted exact `GET /missions/{known_mission_id}` projected immediately to
   `mission_lifecycle_state`, `delivery_state`, and `evidence_state`.

The scalar inspect is closed to the expected Compose project and service labels, state status,
running boolean, exit code, OOM boolean, dead boolean, engine-error-presence boolean, and health
status. The retained result is a closed classification distinguishing missing, created, runtime
error, nonzero exit before claim, nonzero exit after claim, running unhealthy/socket-health
contract, zero exit, no queued mission, and inconsistent claim or runtime state.

Missing, ambiguous, malformed, hostile, oversized, non-ASCII, secret-like, interrupted, timed-out,
or failed collection normalizes to `inconclusive` or `output_rejected`. Diagnostic failure never
masks primary `fixed_node_start_failed`. The producer performs no Hermes attempt or retry after
that primary failure and proceeds to the existing cleanup exactly once.

The diagnostic does not publish or retain the raw container identity, raw stdout or stderr, daemon
error text, logs, environment, mounts, configuration, whole API objects, volume contents, commands,
digests, timestamps, requester data, credentials, prompts, provider content, or arbitrary tool
results. It adds no shell, process, broad filesystem, network, general Docker-socket, arbitrary
host-control, governed-tool, or governed-power authority.

## Runtime Parity

Relative to reviewed runtime tip `8cd307e3ce2ca20e6fdc1b53fc1937bfa5568685`, only
`scripts/local_v1_lv1_003_o4_producer.py` and
`tests/test_local_v1_lv1_003_o4_producer.py` may differ. Every other Mission Command Center allowed
runtime path must remain byte-identical to that reviewed tip.

The exact producer and focused-test bytes used by any Attempt 011 authorization must remain equal
to commit `0aee84f160fb3ce4d80a0772389d529594847013`.

## Evidence Limits

The implementation, focused tests, and exact-candidate review are evidence only. They do not prove
that Attempt 011 will succeed, establish a fixed-Node root cause, inspect or reproduce private
Attempt 010 receipt contents, establish generic Docker, process, runtime, project, image,
container, network, volume, credential, or host absence, or complete cleanup, release, promotion,
production acceptance, or UAT.

The review does not execute a producer, invoke Docker or a provider, take credential custody,
inspect retained private evidence, reconcile or delete prior evidence, retry Attempt 010, reopen
Attempts 001 through 010 or any consumed recovery, or authorize automatic retry, recovery, cleanup,
release, promotion, production, or UAT.

## Authority

This review permits preparation of a separate exact Attempt 011 one-shot execution authorization
only. Attempt 011 must use the existing gate-first
`make local-v1-lv1-003-o4-producer-run` entrypoint and exact module command
`uv run python -m scripts.local_v1_lv1_003_o4_producer`. It must be a fresh isolated attempt with a
producer-generated run ID, Compose project, suffix, runtime root, receipt root, and evidence path.
Any invocation consumes Attempt 011 and requires an immediate durable disposition.

This review grants no live execution by itself. A separate exact authorization candidate and a
future annotated nonforce review tag must both validate before the existing five bounded authority
fields can become live for one supervised invocation. It does not execute Attempt 011 and does not
grant release or UAT acceptance. The governed tool count remains exactly 24.

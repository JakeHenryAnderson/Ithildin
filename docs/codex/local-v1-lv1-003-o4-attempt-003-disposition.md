# Local v1 LV1-003 O4 Attempt 003 Disposition

Status: `AUTHORIZE_SUPERVISED_ONE_ATTEMPT_IMMEDIATE_CHILD`

This disposition authorizes at most one central-manager-supervised invocation for
`LV1-003-O4-ATTEMPT-003`. It does not execute the attempt and does not authorize concurrent
invocation, automatic retry, or a post-attempt rerun.

## Exact Reviewed Parent

The required parent is the independently reviewed Compose-repair candidate
`7e6eb9f0fcad35016f611096543fa4a81017259c`, tree
`fef080b85db9b44675150954d6af5afd5d6fec0d`. Its exact review record is
`docs/codex/local-v1-lv1-003-o4-compose-repair-exact-review.md`, with zero Critical, High, Medium,
or Low findings and exact-commit disposition `GO`.

No future child commit or tree is stated here. After every other check passes, the gate derives
current `HEAD` and tree and requires a clean, single-parent immediate child of the reviewed repair
commit. Its committed diff must equal the exact seven-path control allowlist. Every non-control
path, including the repaired base Compose, overlay, producer, and focused tests, must remain
byte-equivalent to the reviewed parent.

The exact repaired source digests are
`sha256:895107a268169790024c07fe00556fb5d6df0ce4479f49cbe091ccfc517ceb04`,
`sha256:f6a78f705165354e9908c4512ab551f87dd16cada6e415d59979d78d6f66107c`, and
`sha256:b4d44f09183fca2df5cab33496571c3ac316420074e8eeba71e506fd92999c4b`.

## Exact Invocation

The operator command is exactly:

```text
make local-v1-lv1-003-o4-producer-run
```

Its exact underlying command remains:

```text
uv run python -m scripts.local_v1_lv1_003_o4_producer
```

## Consumed History And Retained Evidence

Attempt 001 remains `ATTEMPT_CONSUMED_PRE_GATE_IMPORT_FAILURE`. Attempt 002 remains
`ATTEMPT_002_CONSUMED_FIXED_COMPOSE_INVALID`. Neither attempt is reinterpreted, retried, or
reopened.

Before granting Attempt 003, the gate directly validates the retained Attempt 002 receipt,
quarantine disposition, candidate manifest, and all 663 snapshot files through descriptor-anchored
no-follow reads. The exact Attempt 002 receipt is allowed and required. The runtime base must remain
owner-only `0700` and empty; the Attempt 002 runtime run and published report must remain absent.
Any missing or changed retained evidence, unknown or additional receipt run, populated runtime,
published report, symlink, special entry, or additional attempt root refuses authority.

## One-Attempt Custody

The gate does not claim atomic, tamper-proof, persistent cross-process budget consumption.
Central-manager custody is mandatory. Any invocation—successful, refused, failed, timed out,
interrupted, or ambiguous—consumes Attempt 003 and requires an immediate new post-attempt
disposition. There is no concurrent invocation, automatic retry, or post-attempt rerun authority.

## Authority Ceiling

Exactly five authority fields are true only for the dynamically validated child and one supervised
invocation: producer code, bounded Docker lifecycle, the single fixed Hermes execution, fixed
host-local model-provider access, and O4 evidence execution. The remaining 14 authority fields are
false, including credential custody, runner lifecycle, arbitrary host control, generic process
control, shell execution, Docker socket access, non-bypass claims, new powers, new tools, release,
promotion, production, and UAT. The governed tool count remains exactly 24.

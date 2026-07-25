# Local v1 LV1-003 O4 Attempt 002 Disposition

Status: `AUTHORIZE_SUPERVISED_ONE_ATTEMPT_IMMEDIATE_CHILD`

This disposition authorizes at most one central-manager-supervised invocation for Attempt
`LV1-003-O4-ATTEMPT-002`. It does not authorize concurrent invocation, automatic retry, or a
post-attempt rerun.

## Exact Reviewed Parent

The required parent is the independently reviewed entrypoint-repair candidate
`88c707f1c90d5807a81412ea7790b3a0b94e2f85`, tree
`5316f8f270eb55af38dd032ec7723edef8a423c5`. Its parent is the Attempt 001 closure commit
`148effd50c69b40a005f86f6217fc3db8b665a06`. The entrypoint-repair exact-review record is
`docs/codex/local-v1-lv1-003-o4-entrypoint-repair-exact-review.md`, with zero Critical, High,
Medium, or Low findings and exact-commit disposition `GO`.

No future child commit or tree is stated here. The gate derives current `HEAD` and tree only after
proving that it is a clean, single-parent immediate child of the reviewed parent, that its committed
diff is exactly the seven-path control allowlist, that reviewed producer/runtime paths remain
byte-equivalent to `5dab3654391c14fe214a9dfe302c099d0fe5fbf8`, and that the repaired entrypoint
surfaces remain byte-equivalent to `88c707f1c90d5807a81412ea7790b3a0b94e2f85`.

## Exact Invocation

The operator command is exactly:

```text
make local-v1-lv1-003-o4-producer-run
```

That target's exact underlying command remains:

```text
uv run python -m scripts.local_v1_lv1_003_o4_producer
```

The failed Attempt 001 file-path command
`uv run python scripts/local_v1_lv1_003_o4_producer.py` remains unauthorized.

## Attempt 001 Preservation

Attempt 001 remains `ATTEMPT_CONSUMED_PRE_GATE_IMPORT_FAILURE`. Its disposition JSON and Markdown
digests remain exact, its budget is not restored, and its retry authority remains false. Attempt
002 is a distinct reviewed attempt, not a reinterpretation or retry of Attempt 001.

## One-Attempt Custody

Before granting Attempt 002, the gate checks the exact runtime, receipt, and published-report roots.
Absent roots are acceptable. Existing roots must be no-follow owner-owned `0700` directories and
empty. Any retained entry, unsafe root, unreadable root, or ambiguous posture refuses authority.

This gate does not implement or claim atomic, tamper-proof, persistent cross-process budget
consumption. Central-manager custody is mandatory. Any invocation—whether successful, refused after
entry, failed, timed out, interrupted, or ambiguous—consumes Attempt 002 and requires an immediate
new post-attempt disposition. There is no concurrent invocation, automatic retry, or post-attempt
rerun authority.

## Authority Ceiling

Exactly five authority fields are true only for the dynamically validated child and one supervised
invocation: producer code, bounded Docker lifecycle, the single fixed Hermes execution, fixed
host-local model-provider access, and O4 evidence execution. The remaining 14 authority fields are
false, including credential custody, runner lifecycle, arbitrary host control, generic process
control, shell execution, Docker socket access, non-bypass claims, new powers, new tools, release,
promotion, production, and UAT. The governed tool count remains exactly 24.

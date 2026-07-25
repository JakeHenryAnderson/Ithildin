# Local v1 LV1-003 O4 Post-Review Disposition

Status: `AUTHORIZE_SUPERVISED_ONE_ATTEMPT_IMMEDIATE_CHILD`

This is the separate post-review disposition for one bounded local `O4` journey. Its machine
record is `docs/codex/local-v1-lv1-003-o4-post-review-disposition.json`.

## Exact Lineage

The disposition is anchored to candidate-parent commit
`86e75f0cf7f92ceb33218f2a66a00668f4da9e12`, tree
`11d9a752b8e08b483e1d8b9a347a06b5d8bf9af7`. That commit contains the code-only authorization for
reviewed producer candidate `5dab3654391c14fe214a9dfe302c099d0fe5fbf8`, tree
`f9a0cb66ac12e6e0ecca7fc23a0071be0dbe3075`, and the independent producer exact-review record.

No future child commit or tree is stated here. The execution gate may derive an execution checkout
identity only when current `HEAD` is a clean, single-parent, immediate child of the candidate
parent; its committed diff is exactly the six-path control allowlist; and every reviewed
runtime, producer, bridge, and covered test path remains byte-equivalent to the reviewed producer
candidate. A sibling, merge, descendant, dirty checkout, extra path, or runtime delta fails before
runtime creation.

## One-Attempt Custody

This disposition authorizes at most one central-manager-supervised local producer invocation. It
does not implement or claim atomic, tamper-proof, persistent cross-process budget consumption. No
concurrent invocation, automatic retry, or post-attempt rerun is authorized.

Before granting the attempt, the gate checks the exact local runtime, receipt, and published-report
roots for retained prior-attempt or success evidence. Any entry, unsafe root, unreadable root, or
ambiguous posture refuses execution. This is useful retained-local-evidence detection, not a
non-bypass or durable-ledger claim: a same-UID operator can remove local evidence. Manager
custody therefore remains mandatory, and any attempted invocation—success, refusal after runtime
creation, timeout, interruption, ambiguous outcome, or failure—requires an immediate new
post-attempt disposition before any rerun.

## Authority Ceiling

Only these five authority bits are true for the dynamically validated child checkout and the one
supervised invocation:

- producer code;
- bounded Docker lifecycle;
- the single fixed Hermes execution;
- fixed host-local model-provider access; and
- `O4` evidence execution.

Credential custody, runner lifecycle authority, arbitrary host control, generic process control,
shell execution, Docker socket access, network or filesystem non-bypass claims, new governed
powers, new governed tools, release, promotion, production, and UAT remain false. The governed
tool count remains exactly 24.

The authorization is not a release or UAT disposition. Gateway truth, Node connectivity,
runner-reported state, and model-provider state remain separate. A completed attempt produces
candidate-bound evidence for review; it does not prove output correctness, provider truth,
production readiness, or human acceptance.

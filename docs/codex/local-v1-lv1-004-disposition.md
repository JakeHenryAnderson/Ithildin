# Local v1 LV1-004 Failure and Recovery Disposition

Status: `O5_LV1_004_COMPLETE_NO_LIVE_AUTHORITY`

Exact clean evidence candidate `b77d53562229026e932ec554fda5caca84c9642e`, tree
`e514658e31300989ae339639f89f1fcd4b63bd57`, passed the isolated Local-v1
failure-and-recovery journey and its candidate-bound checker.

## Bounded Result

The single coherent scenario passed restart continuity, replay rejection, temporary partition
failure, Node revocation, stale-configuration rejection, and manual rollback. Rollback created
fresh signed generation three from generation one after generation two drifted. The stale rollback
precondition and stale generation-one acknowledgment both failed closed.

Gateway truth remained authoritative. Configuration status is `stored_not_enforced`; runner state
is `runner_reported_only`; model-provider state is `unknown`. The governed tool count remains 24.
The journey started only the fixed isolated loopback Gateway harness—no Docker service, external
runner, model provider, or arbitrary host process.

The private run, Node, and mission identities are represented only by domain-separated digests in
the machine disposition. The 39-file private evidence set, safe JSON report, safe Markdown report,
and checker output are bound by sizes, modes, and SHA-256 digests. No raw private identity or
selected run path is recorded here.

## Review and Validation Lineage

Independent Sol-high review of candidate `e2120f858ab35d19dac2dfa8ca83f0b555f7e147`
returned `GO` with zero Critical, High, Medium, or Low findings after symlink confinement and
operator-Markdown repairs. Its first live journey completed, but the checker then exposed a
regular-file probe bug: it applied a file-type test to permission bits after the no-follow reader
had already established a regular file. That run is not claimed as passing evidence.

The final candidate corrected that one-line classification and added a direct positive regression
test in exactly two paths. Nineteen focused tests, Ruff, strict mypy, Local-v1 inner checks,
agent-workflow checks, and trust-surface invariants passed. A fresh final-candidate journey and
checker then both exited zero. The final two-path mechanical delta did not receive another
independent review; this is recorded explicitly rather than representing the earlier review as
exact-candidate review of the final commit.

## Closure and Limits

This evidence closes only outcome `O5` and milestone `LV1-004`. It does not prove whole-host restart
safety, network or filesystem non-bypass, host enforcement of configuration, runner behavior beyond
reported state, model-provider output, production readiness, release acceptance, or human UAT.

All ten authority fields remain false. No retry, runtime, runner, Docker, provider, release,
promotion, production, credential-custody, or UAT authority is derived from this disposition. The
ordered next milestone is `LV1-005`.

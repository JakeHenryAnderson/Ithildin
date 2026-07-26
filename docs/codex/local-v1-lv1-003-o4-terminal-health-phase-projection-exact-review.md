# Local v1 LV1-003 O4 Terminal-Health Phase Projection Exact Review

Status: `GO_CODE_ONLY`

Date: 2026-07-26

## Exact Candidate

- Commit: `338dc059fa251299502ff31f9274f2a1ffc9c9ea`
- Tree: `3428f0148520e629fd5fe50788469fcd55ad2dba`
- Direct parent and consumed Attempt 013 closure:
  `0e2ed89b744bcf9a98fd09a5b39a0705656aa001`

Relative to the direct parent, the candidate changes exactly two paths:

| Path | SHA-256 |
| --- | --- |
| `scripts/local_v1_lv1_003_o4_producer.py` | `036ff3fe0baf2c2d4f8f89f72b6edbcbcf01fff55371ef8752118ded74492292` |
| `tests/test_local_v1_lv1_003_o4_producer.py` | `2eaba1dfe1835f8ae507af93d74c2d78ae192cf93ae4330e7b296ba94727f50f` |

The pushed upstream tracking ref equaled the exact candidate and the worktree was clean during the
independent review.

## Independent Review Disposition

One independent GPT-5.6 Sol high read-only review found:

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The exact-candidate disposition is `GO_CODE_ONLY`. The review applies only to the commit, tree,
lineage, exact two-path inventory, and file digests above. Sol xhigh was deliberately not used:
the defect and repair were source-proven, narrowly bounded, and covered by a closed state matrix.

## Reviewed Diagnostic Contract

When the fixed Node container is `exited`, not running, reports no OOM, dead, or engine-error
signal, and has health `absent` or `unhealthy`, the producer may retain the closed bridge phase
mapped from a reserved exit code. Docker can retain the final unhealthy health observation after a
container exits. That observation remains noncanonical for lifecycle classification, but it does
not contradict the bridge's reserved exit-code phase.

An exited/unhealthy observation therefore still classifies as
`fixed_node_exited_observation_noncanonical`. Health `starting` or `healthy`, a nonterminal
lifecycle state, a running state, or any OOM, dead, or engine-error signal suppresses the phase to
`not_reported`. Nonreserved exits also remain `not_reported`.

The producer discards the raw exit integer and container identity before retaining or projecting
the diagnostic. A phase is a closed, noncausal last-entered marker only. It does not prove root
cause, successful execution, safe retry, or authority.

## Boundary Review

The candidate changes no command construction or allowlist, Docker action, API request, filesystem
path, credential behavior, provider access, retry, cleanup, lifecycle action, governed tool,
manifest, or public authority. The governed tool count remains exactly 24. Arbitrary host, process,
shell, Docker-socket, network, and filesystem control remain unauthorized.

## Validation

The manager checkpoint and independent review passed:

- all 279 producer tests;
- 25 constrained-mission journey tests;
- 46 independently selected terminal-health and phase tests;
- Ruff across both changed paths;
- strict mypy for the producer;
- the agent-workflow instruction check;
- the tool-surface invariant with 24 tools and 24 manifests;
- the no-new-powers guardrail with deferred boundaries unchanged; and
- exact lineage, two-path inventory, file digests, clean worktree, and `git diff --check`.

Pytest emitted only the known non-failing cleanup warnings for synthetic temporary directories
outside the repository.

## Consumed Authority And Next Gate

Attempt 013 remains consumed. Its budget is zero, retry and automatic retry are false, and all 19
authority fields remain false. This review does not authorize Docker, Hermes, provider access,
another O4 attempt, release, promotion, production, or UAT.

This `GO_CODE_ONLY` disposition permits preparation of one separate exact-candidate execution gate
for a successor diagnostic attempt. That gate must bind this reviewed candidate and review record,
preserve all prior consumed-attempt evidence, require its own clean exact candidate and fixed
annotated tag, grant at most one central-manager-supervised invocation, and require immediate
consumed disposition. No execution authority exists until those conditions pass. No concurrent,
automatic, or second invocation is authorized.

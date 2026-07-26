# Local v1 LV1-003 O4 Socket-Parent Mode Exact Review

Status: `GO_CODE_ONLY`

Date: 2026-07-26

## Exact Candidate

- Commit: `8f2191a4b3a6b5559f5a9083973c8b2797fe7f45`
- Tree: `c5634835d7c2f2280ee2555866cf6c32c346f540`
- Direct parent: `f889449420c865299f8d2a08fe62cc323a994fab`

Relative to the direct parent, the candidate changes exactly two paths:

| Path | SHA-256 |
| --- | --- |
| `apps/node/src/ithildin_node/fixed_runner_bridge.py` | `8d9ba5cffcee099e8901fd0124a96b856681073b2adf68e2f25b4f0aeccf6f7b` |
| `tests/test_node_fixed_runner_bridge.py` | `cfd1aa52d0bce3385b53341a63cad6af7fbfb3210e55ef033a69ab1b9221bb26` |

The exact candidate had a clean diff during review.

## Independent Review Disposition

One independent GPT-5.6 Sol high read-only review found:

- Critical: 0
- High: 0
- Medium: 0
- Low: 0

The exact-candidate disposition is `GO_CODE_ONLY`. Sol xhigh and Ultra were not used. This review
applies only to the exact commit, tree, parent, two-path inventory, and file digests above.

## Reviewed Predicate Semantics

When `_open_owned_directory` receives `allowed_modes`, the observed directory mode must be an exact
member of that set. This permits the fixed bridge's internal socket-parent call sites to request
only `{0o770}` while rejecting every other mode, including modes that are more restrictive but not
explicitly allowed.

When `allowed_modes` is `None`, the established default remains unchanged: group-write or
world-write permission bits are rejected. UID, GID, and directory-type validation are unchanged.
Descriptor-relative access, no-follow opening, `fstat` validation, directory descriptors, and
`dir_fd`-anchored safety are unchanged.

The only internal call sites that supply a non-`None` mode allowlist are the socket-parent checks,
and both use exactly `{0o770}`. Receipt, mission, runtime, and other parent-directory checks continue
to pass `None` and therefore retain the stricter group/world-write rejection.

## Boundary Review

The candidate adds no tool, command, external input, arbitrary mode selection, filesystem path,
Docker action, provider access, credential behavior, network behavior, retry, cleanup operation, or
public authority. It changes no governed-power boundary and the governed tool count remains exactly
24.

The phase marker and successful mode predicate do not prove a fixed-Node root cause, successful O4
execution, safe retry, release readiness, or UAT completion.

## Validation

The manager checkpoint and independent review passed:

- all 30 fixed-runner bridge tests;
- all 137 Local-v1 constrained-journey tests;
- Ruff across the exact two changed paths;
- strict mypy for `apps/node/src/ithildin_node/fixed_runner_bridge.py`;
- the tool-surface invariant with exactly 24 tools;
- the no-new-powers guardrail with its result true and deferred boundaries unchanged; and
- exact lineage, two-path inventory, file digests, clean candidate diff, and `git diff --check`.

Pytest emitted only the known non-failing ambient temporary-directory cleanup warnings.

## Authority And Next Gate

This review grants code-only disposition for the exact candidate. It does not authorize another O4
execution, retry, automatic retry, Docker lifecycle, Hermes execution, model-provider access,
credential custody, arbitrary host/process/shell/Docker-socket control, release, promotion,
production, or UAT.

Any successor diagnostic attempt requires a separate exact-candidate authorization gate with its
own bounded one-shot budget and authority matrix. No execution authority exists in this record.

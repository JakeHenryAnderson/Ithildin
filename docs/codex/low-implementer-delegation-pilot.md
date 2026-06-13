# Low Implementer Delegation Pilot

Status: implemented as a local packet/check workflow.

This pilot tests whether a Low Codex implementer can make useful Ithildin contributions when the
main Codex manager provides a narrow task packet and reviews every diff. It is a productivity experiment, not permission to delegate safety judgment.

Gemma/local-model output is optional advisory input only. Low Codex implementers are the preferred
mechanical delegation path because they share the workspace, tooling, and gate workflow. The default
cheap worker is `gpt-5.4-mini` with low reasoning, used one at a time and report-first unless a
later sprint explicitly approves a bounded patch trial.

## Boundary

Low Codex implementers may receive only mechanical tasks:

- docs link updates;
- stale wording scans;
- packet inventory checks;
- repetitive release-readiness assertions;
- boilerplate following an existing checker/test pattern.

They must not edit manifests, executors, policy semantics, approval logic, audit logic, MCP/API
behavior, storage/auth boundaries, UI runtime behavior, or public trust claims. They also must not
decide whether a capability is safe.

## Command

```sh
make low-implementer-delegation-packet
make low-implementer-delegation-check
make low-implementer-ticket-catalog-check
```

The packet command writes an ignored task packet under
`var/agent-delegation/low-implementer-packet/`. It does not call a local model, send prompts over
the network, mutate runtime state, create approvals, write audit events, or add tool powers.

The check verifies that `AGENTS.md`, this pilot doc, the ticket catalog, README, docs-site inputs,
review-doc metadata, and the generated task packet preserve the planner-implementer boundary.

## Default Pilot Task

The default generated task is `docs-link-scan`, which asks a low implementer to inspect committed
docs for stale command-list references and report candidate mechanical updates only. The packet can
also generate `stale-wording-scan`, `make-target-wiring`, and `packet-inventory` tasks from the
[Low-Implementer Ticket Catalog](low-implementer-ticket-catalog.md). It forbids edits to runtime
source, manifests, policy, approval/audit code, MCP/API behavior, and trust claims.

Every packet includes a manager scorecard so the main manager can record useful suggestions,
rejected suggestions, boundary drift, cleanup effort, and whether the ticket should be delegated
again.

Direct file edits by Low Codex implementers remain disabled until several read-only trials show
useful suggestions, low manager cleanup, and no boundary drift.

The main manager may then choose to apply, patch, or discard any suggestion. No low implementer
output is committed without main-manager review and the usual gates.

## Success Criteria

- The packet is specific enough that a low implementer can produce useful suggestions.
- The task has explicit allowed and forbidden files.
- The focused check is small and cheap.
- The workflow can be repeated without spending High/XHigh review on mechanical chores.
- Any output that drifts into design or safety decisions is rejected.
- Gemma/local-model suggestions remain optional and are not part of the required release path.

## Calibration Note

The first `gpt-5.4-mini` low-effort trial used the default `docs-link-scan` ticket as a read-only
suggestion task. The manager accepted one duplicate-link cleanup, rejected one already-documented
README command suggestion, and observed no boundary drift. That outcome supports using Low Codex
workers for narrow, non-blocking mechanical scans when the manager keeps review and commit control.

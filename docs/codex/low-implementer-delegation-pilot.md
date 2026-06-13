# Low/Gemma Implementer Delegation Pilot

Status: implemented as a local packet/check workflow.

This pilot tests whether a low/Gemma-class implementer can make useful Ithildin contributions when
the main Codex manager provides a narrow task packet and reviews every diff. It is a productivity experiment, not permission to delegate safety judgment.

## Boundary

Low/Gemma-class implementers may receive only mechanical tasks:

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
```

The packet command writes an ignored task packet under
`var/agent-delegation/low-implementer-packet/`. It does not call a local model, send prompts over
the network, mutate runtime state, create approvals, write audit events, or add tool powers.

The check verifies that `AGENTS.md`, this pilot doc, README, docs-site inputs, review-doc metadata,
and the generated task packet preserve the planner-implementer boundary.

## Default Pilot Task

The default generated task asks a low implementer to inspect committed docs for stale command-list
references and report candidate mechanical updates only. It forbids edits to runtime source,
manifests, policy, approval/audit code, MCP/API behavior, and trust claims.

The main manager may then choose to apply, patch, or discard any suggestion. No low/Gemma-class
output is committed without main-manager review and the usual gates.

## Success Criteria

- The packet is specific enough that a low implementer can produce useful suggestions.
- The task has explicit allowed and forbidden files.
- The focused check is small and cheap.
- The workflow can be repeated without spending High/XHigh review on mechanical chores.
- Any output that drifts into design or safety decisions is rejected.

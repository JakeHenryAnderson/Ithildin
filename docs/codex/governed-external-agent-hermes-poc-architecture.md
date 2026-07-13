# Governed External Agent POC: Hermes Architecture

Status: Track A compatibility topology implemented and observed. Track B runtime expansion is blocked.

Current governed tool count: `24`.

Current capability-expansion decision: `blocked` because the source-review closure matrix still has
`external_pending` rows.

Validation:

```sh
make hermes-governance-poc-plan-check
make capability-expansion-gate
```

## Objective

Prove that a pinned external agent can perform a repetitive synthetic mission through Ithildin's
existing governed tools while Ithildin records allowed, denied, approval-bound, replay, restart,
and reconstruction evidence. The POC must distinguish mediation evidence from isolation or
orchestration claims.

Hermes owns the agent loop, a configured model provider performs inference, Ithildin Gateway
mediates governed tool calls, and Command Center presents authoritative Ithildin state.

## Current Baseline

The current implementation provides a local stdio MCP adapter with fixed principal
`agent:mcp-local` and session `mcp-stdio`, 24 manifest-locked tools, policy, approval, redaction,
audit, Agent Run correlation, read-only run APIs, and Command Center display. It does not provide
external-agent enrollment, dynamic identity, mission dispatch, process supervision, remote MCP,
container lifecycle control, non-bypass proof, or production identity.

## Proposed POC Topology

```text
operator -> Command Center (display and existing operator APIs)
                    |
                    v
             Ithildin Gateway
                    ^
                    |
          local stdio MCP adapter
                    ^
                    |
              Hermes runner --------> configured model provider
                    |
                    +-- shared local filesystem required by current stdio process
```

The first executable slice keeps Hermes operator-started and uses the current stdio adapter. Because
the adapter is a child process in the runner's environment, this compatibility topology cannot keep
the governed workspace inaccessible to Hermes built-in filesystem or terminal capabilities. It may
show that Hermes used Ithildin, but it must not claim filesystem non-bypass, Ithildin-managed
isolation, process control, or observation of actions outside governed MCP.

## Pinned Hermes Candidate

The official multi-platform image resolved on 2026-07-13 is:

```text
nousresearch/hermes-agent@sha256:6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc
```

Platform manifests:

- `linux/amd64`: `sha256:48420b0abcf18f9f33cfa1da4c4e8bbd4ad107a0ddc52e5fb3ebb34a9fd20149`
- `linux/arm64`: `sha256:bca5bafd0292bdf0d4b4b975780e96c0ec9e428e08941a87aacddb116663ce13`

The digest changes only through intentional review. Evidence runs must not use an unpinned
`latest`, install arbitrary skills, mount the Docker socket, or fetch mutable dependencies.

## Synthetic Mission

Hermes repeatedly reviews synthetic case files, summarizes the assigned record, and proposes a
bounded artifact or patch. Fixtures include adversarial instructions requesting cross-workspace
out-of-root reads, deletion, unapproved mutation, credential disclosure, or an unapproved network
destination. Per-agent cross-workspace assignment is not implemented in Track A.

The model's choice is not the security assertion. The governed surface must permit the approved
read/proposal path, provide no delete tool, deny out-of-scope resources and destinations, keep
approval-bound execution pending, reject stale or replayed approval, and retain secret-free
reconstruction evidence.

## Trust Zones

- **Hermes runner:** untrusted for authorization. Track A gives it no Ithildin admin token, Docker
  socket, or host root, but the stdio topology shares the configured demo workspace with the adapter.
- **Stdio adapter:** trusted local ingress using the current fixed identity/session and shared
  `GovernedToolCallService`; it does not prove per-instance Hermes identity.
- **Gateway:** authoritative for registry, policy, approval, execution, redaction, and audit outcomes
  on mediated calls; not authoritative for Hermes process state or outside actions.
- **Command Center:** displays observed/derived state; it does not start Hermes, execute tools, or
  infer container truth.

## Non-Bypass Claim Ladder

1. `observed_through_ithildin`: a Hermes call traversed governed MCP.
2. `governed_surface_enforced`: Ithildin allowed or denied the requested governed operation.
3. `fixture_access_path_constrained`: blocked in Track A; a separately reviewed enforcement-node
   transport must keep synthetic governed data and credentials outside the runner.
4. `agent_fully_non_bypassable`: prohibited for this POC; host compromise and unobserved Hermes
   capabilities remain outside Ithildin's proof.

Evidence from one level cannot be promoted to the next without the required topology proof.

## Required Future Gates

Dynamic principal/session and workspace binding, mission lifecycle control, remote MCP or a network enforcement
node, Ithildin-managed Docker/sandbox lifecycle, model invocation, production enrollment, SIEM
runtime behavior, and any tool-count change are separate future powers. Each requires its own
proposal, implementation decision, negative tests, source-review handoff, and readiness updates.

## Stop Conditions

Stop before runtime implementation if the first slice requires a new tool, public API/schema,
remote MCP, shell execution, Docker socket access, container lifecycle control, sandbox
orchestration, broad filesystem or network authority, production identity, or a stronger claim than
the evidence supports.

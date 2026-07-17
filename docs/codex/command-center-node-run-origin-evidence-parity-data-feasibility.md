# Command Center Node Run-Origin Evidence Parity Feasibility

Status: approved preimplementation map for bounded same-record consistency handling.

Current governed tool count: `24`.

## Operator Problem

Command Center now displays server-derived Node origin from the selected Agent Run, while the
existing redacted run-evidence endpoint independently serializes a bounded `run.origin` object from
the same persisted record. The UI must not silently present both if they disagree because of a
stale response, malformed record, or future implementation drift.

## Bounded Contract

For a selected `node_governed_access` run, compare the displayed run metadata and evidence-export
origin across the exact bounded fields:

- ingress kind and identity source;
- Node ID and display name;
- read-only authorization profile;
- configuration generation and digest;
- offline-fallback allowance; and
- runner-enforcement proof state.

The operator state is one of:

- `Preparing comparison` while the matching evidence response is loading;
- `Matches selected run` only when every bounded field is equal;
- `Unavailable` when the evidence request failed; or
- `Mismatch - do not rely on export origin` when the response is present but missing or different.

A match proves serialization consistency from the same Gateway record only. It is not an
independent signature, attestation, custody claim, runner-enforcement proof, or evidence that all
endpoint activity passed through Ithildin.

## Implementation Boundary

Use the existing selected-run detail and existing run-evidence response already loaded by Command
Center. Add no endpoint, schema, query, storage field, policy behavior, executor, role, permission,
or governed tool. Generic MCP and guided-demo runs remain unchanged.

## Stop Conditions

Stop if implementation requires treating the redacted snapshot as independent authority, mutating
run state, automatically retrying or repairing evidence, contacting the Node, or broadening Node,
runner, model, filesystem, network, or host-control powers.

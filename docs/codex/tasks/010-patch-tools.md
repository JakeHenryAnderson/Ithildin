# Task 010 - Patch Proposal and Apply

## Goal

Allow agents to propose file changes and apply them only after approval.

## Tools

- `fs.propose_patch`
- `fs.apply_patch`

## Acceptance Criteria

- Patch proposal produces a diff preview without mutation.
- Patch apply requires approval.
- Approval is bound to exact patch hash.
- Patch applies only under allowed workspace paths.
- Failed patch application is audited.
- Tests cover approval replay, modified patch hash, path escape, and successful apply.


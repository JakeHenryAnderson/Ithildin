# Task 005 - Policy Evaluator

## Goal

Implement deny-default policy decisions from a typed input model.

## Scope

- YAML rules.
- `allow`, `deny`, and `require_approval`.
- Policy version hash.
- Matched rule tracking.
- Obligations for audit, approval, and max execution time.

## Acceptance Criteria

- Default decision is deny.
- Invalid policy fails startup or fails closed.
- Writes require approval under the default policy.
- Deletes, shell, Docker, and secrets are denied in default policy.
- Tests cover allow, deny, require approval, and no matching rule.


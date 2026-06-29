# Development Efficiency Status

Status: checked development-efficiency view.

This page defines the compact local command for deciding which Ithildin gate to run next while the
project is deep in readiness, review, and enterprise-prep work.

Run:

```sh
make development-efficiency-status
```

The command consolidates:

- `make validation-decision` for the current dirty-file validation mode.
- `make release-check-profile` for the static shape of the full release gate.
- `make technical-mvp-operator-trial-readiness` for the local-preview operator-trial state.
- `make enterprise-current-checkpoint` for the current enterprise handoff action.

## What It Answers

The report is intentionally small and operator-facing. It records:

- the current commit and dirty state;
- tool count, latest implemented tool, and selected next capability;
- the recommended development gate, usually `make dev-check` on a clean tree;
- deferred handoff commands such as `make release-check`, `make review-candidate`, and
  `make enterprise-review-send-refresh`;
- release-check target counts and heaviest target categories;
- technical MVP operator-trial readiness;
- enterprise response/closure counts and the current ERG-003/ERG-002 send action;
- key handoff artifact paths.

## Boundaries

This command does not start services, does not call governed tools, does not approve runtime changes,
and does not replace release-check. It is a decision aid for choosing the smallest honest next
validation step.

It also does not approve:

- capability expansion;
- new power classes;
- sandbox orchestration;
- Mission Control execution authority;
- public/security-product positioning;
- production identity, runtime Postgres, hosted telemetry, or remote MCP hosting.

## Normal Use

For routine development:

```sh
make development-efficiency-status
make dev-check
```

For a meaningful checkpoint or review handoff:

```sh
make development-efficiency-status
make release-check
make review-candidate
```

For the current enterprise handoff lane:

```sh
make development-efficiency-status
make release-check
make review-candidate
make enterprise-review-send-refresh
```

The status command is included in `make release-check` so stale gate-selection guidance cannot drift
out of release evidence.

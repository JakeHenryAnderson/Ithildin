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
- `make validation-recommendation` when a command recommendation is enough and no command should
  run.
- `make release-check-profile` for the static shape of the full release gate.
- `make technical-mvp-operator-trial-readiness` for the local-preview operator-trial state.
- `make enterprise-current-checkpoint` for the current enterprise handoff action.
- `make enterprise-review-send-preflight` for current ERG-003/ERG-002 handoff artifact freshness.
- `make artifact-freshness-check` when packet/handoff freshness needs to be checked before a long
  gate.
- `make status-now` for the shortest current-state and next-command answer.
- `make handoff-dry-run` for cheap current-artifact handoff readiness after a full candidate
  refresh; it includes `make enterprise-send-quick-check` plus artifact freshness and no-refresh
  enterprise status.

## What It Answers

The report is intentionally small and operator-facing. It records:

- the current commit and dirty state;
- tool count, latest implemented tool, and selected next capability;
- the recommended development gate, usually `make dev-check` on a clean tree;
- deferred handoff commands such as `make release-check`, `make review-candidate`, and
  `make enterprise-review-send-refresh`;
- release-check target counts and heaviest target categories;
- technical MVP operator-trial readiness;
- whether the latest local operator trial has been observed from `DEMO_FLOW_RESULT.md`;
- whether the current enterprise send package is fresh for the current commit, generated from a
  clean tree, and hash-consistent;
- review-candidate artifact freshness for the compact v1.0 RC packet and captured release-check
  transcript;
- enterprise response/closure counts and the current ERG-003/ERG-002 send action;
- readiness warnings when strict handoff artifacts are stale or a downstream checkpoint gate is not
  currently green;
- key handoff artifact paths.

## Boundaries

This command does not start services, does not call governed tools, does not approve runtime changes,
and does not replace release-check. It is a decision aid for choosing the smallest honest next
validation step.

Stale generated packets, stale send artifacts, or stale captured release transcripts are reported as
readiness warnings. They still require the normal refresh or release gates before handoff, but they
do not make this diagnostic command itself fail.

The human-readable output caps readiness warning detail and points to `--json` for the full list.

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
make status-now
make validation-recommendation
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
make handoff-dry-run
make release-check
make review-candidate
make enterprise-review-send-refresh
```

`make handoff-dry-run` is a current-artifact confirmation path, not release proof. It includes the
cheap current-send confirmation path, artifact freshness, and no-refresh enterprise status without
starting services, recording review, normalizing responses, or closing enterprise lanes.

Use `make artifact-freshness-check` before a long gate when you suspect stale packet state. It
reports whether enterprise send artifacts, the compact v1.0 RC packet, and the captured
release-check transcript match the current commit, then recommends refresh commands. It is a
diagnostic shortcut, not release proof.

Use `make status-now` as the quick "what should I do next?" view. It combines validation mode,
artifact freshness, current enterprise action, and boundary flags without running services or
governed tools.

The status command is included in `make release-check` so stale gate-selection guidance cannot drift
out of release evidence.

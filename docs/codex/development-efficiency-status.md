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
- `make enterprise-review-send-preflight` for the current ERG-006/ERG-007 production identity/storage review artifact
  freshness.
- `make artifact-freshness-check` when packet/handoff freshness needs to be checked before a long
  gate.
- `make status-now` for the shortest current-state and next-command answer.
- `make progress-check` for the automatic efficient progress gate: dirty trees run `make
  dev-check`; clean trees run `make handoff-dry-run`.
- `make progress-check ARGS=--refresh-stale` for the clean-tree case where generated handoff
  artifacts should be refreshed before the same sanity path.
- `make handoff-dry-run` for cheap current-artifact handoff readiness after a full candidate
  refresh; it includes `make enterprise-send-quick-check` plus artifact freshness and no-refresh
  enterprise status.

## What It Answers

The report is intentionally small and operator-facing. It records:

- the current commit and dirty state;
- tool count, latest implemented tool, and selected next capability;
- the recommended development gate, usually `make dev-check` while files are dirty and `make
  handoff-dry-run` once the tree is clean and artifacts should be checked;
- deferred handoff commands such as `make release-check`, `make review-candidate`, and
  `make enterprise-review-send-refresh`;
- release-check target counts and heaviest target categories;
- technical MVP operator-trial readiness;
- whether the latest local operator trial has been observed from `DEMO_FLOW_RESULT.md`;
- whether the current enterprise send package is fresh for the current commit, generated from a
  clean tree, and hash-consistent;
- review-candidate artifact freshness for the compact v1.0 RC packet and captured release-check
  transcript;
- enterprise response/closure counts and the current ERG-006/ERG-007 production identity/storage review action;
- historical ERG-003/ERG-002 handoff artifacts only as lineage, not the current send action;
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
make progress-check
make validation-recommendation
make development-efficiency-status
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
make progress-check
make handoff-dry-run
make release-check
make review-candidate
make enterprise-review-send-refresh
make review-candidate-release-transcript
make v1-rc-packet
```

`make progress-check` is the default "keep moving" command. It saves the manager from deciding
between a dirty-file development gate and a clean-tree handoff sanity check, but it remains focused
development evidence only. It does not replace release-check or review-candidate.

Use `make progress-check ARGS=--refresh-stale` when the tree is already clean but the last commit
made generated handoff artifacts stale. This intentionally refreshes review-run manifests and
enterprise send artifacts, then runs the refresh commands reported by artifact freshness before
rechecking the clean-tree path. For stale review-candidate release transcripts or the compact v1.0
RC packet, the freshness repair path uses the narrower `make review-candidate-release-transcript`
and `make v1-rc-packet` targets instead of rebuilding every review-candidate artifact. It still does
not replace release-check or review-candidate before checkpoint claims.

`make handoff-dry-run` is a current-artifact confirmation path, not release proof. It includes the
cheap current-send confirmation path, artifact freshness, and no-refresh enterprise status without
starting services, recording review, normalizing responses, or closing enterprise lanes.

Use `make artifact-freshness-check` before a long gate when you suspect stale packet state. It
reports whether enterprise send artifacts, the compact v1.0 RC packet, and the captured
release-check transcript match the current commit, then recommends focused refresh commands. It is a
diagnostic shortcut, not release proof.

Use `make status-now` as the quick "what should I do next?" view. It combines validation mode,
artifact freshness, current enterprise action, and boundary flags without running services or
governed tools.

The status command is included in `make release-check` so stale gate-selection guidance cannot drift
out of release evidence.

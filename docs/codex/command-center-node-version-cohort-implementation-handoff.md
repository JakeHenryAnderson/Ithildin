# Command Center Node Software Version Cohort Implementation Handoff

Status: implemented and focused checks passed; exact-candidate closeout remains required.

Current governed tool count: `24`.

## Implemented Behavior

- The Nodes surface groups loaded enrolled Nodes by exact workspace, signed desired minimum
  version, and last version from an accepted signed heartbeat.
- Cohort cards keep desired and observed sources explicit and separately count meets-minimum,
  below-minimum, never-observed, and recently observed records.
- Below-minimum cohorts sort ahead of missing evidence, stale accepted-heartbeat evidence, and
  cohorts whose loaded records meet the desired minimum, with deterministic tie-breakers.
- Each card can scope the loaded inventory to its exact same-response member key. Selection clears
  stale query and posture filters, applies its workspace, restores attention-first ordering, and
  exposes a removable version-scope banner.
- Software-version scope and configuration-cohort scope are mutually exclusive. Selecting either
  replaces the other, workspace changes and `Clear filters` remove both, and dashboard refresh
  clears both before a new response is loaded.
- Revoked Nodes remain in inventory but do not appear in active software-version cohorts.
- Scope copy states that heartbeat version evidence does not verify installed packages, process
  health, upgrade execution, or rollback execution. Maintenance remains operator managed.

## Focused Validation

```sh
(cd apps/ui && npm test -- --run)
(cd apps/ui && npm run build)
uv run python scripts/review_docs.py
make agent-workflow-check
make lint
git diff --check
```

The UI suite includes a four-Node, three-version-cohort fixture covering two Nodes with an exact
current observation, one below-minimum and stale Node, a separate workspace and desired minimum,
deterministic cohort summaries, exact inventory drill-down, scope replacement in both directions,
and clearing across dashboard refresh.

Observed focused result: 44 UI tests passed, the production UI build completed, documentation
review passed, the agent-workflow contract reported 24 governed tools, Ruff passed, and
`git diff --check` reported no errors.

## Required Closeout

Commit this bounded slice and run `make enterprise-status-export` followed by
`make review-candidate` on the exact clean commit. Passing checks do not authorize package
distribution, update or rollback execution, self-update, release, external-review closure, or UAT
acceptance.

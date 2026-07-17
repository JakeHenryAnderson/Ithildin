# Command Center Node Configuration Cohort Implementation Handoff

Status: implemented and focused checks passed; exact-candidate closeout remains required.

Current governed tool count: `24`.

## Implemented Behavior

- The Nodes surface groups loaded enrolled Nodes by exact workspace, desired generation, desired
  digest, and current Gateway configuration signing-key field, while avoiding historical signer
  provenance claims.
- Cohort cards separate stored-current acknowledgment, awaiting storage, drift, incomplete
  evidence, version exceptions, and recently accepted heartbeat coverage.
- Configuration attention sorts before storage-pending, version/connectivity exceptions, and
  stored-current cohorts, with deterministic workspace and generation tie-breakers.
- Each cohort can scope the loaded inventory to its exact member key. Selection clears stale query
  and posture filters, applies the cohort workspace, restores attention-first ordering, and exposes
  a removable cohort-scope banner before the per-Node list.
- Search and posture filters can refine an active cohort. Selecting another cohort replaces the
  scope, changing the workspace filter clears it, and `Clear filters` removes all presentation
  scope without changing fleet state. Dashboard refresh also clears the scope before a new response
  is loaded.
- Revoked Nodes remain in the fleet inventory but do not appear in active rollout cohorts.
- Scope copy says the values come from loaded Gateway records and that Node storage acknowledgment
  does not prove enforcement, runner health, or host state.

## Focused Validation

```sh
(cd apps/ui && npm test -- --run App.test.tsx)
(cd apps/ui && npm run build)
uv run python scripts/review_docs.py
git diff --check
```

The UI suite includes a four-Node, three-cohort fixture covering a mixed stored-current/drift
cohort, a storage-pending generation, a separate workspace, a below-minimum version, stale
accepted-heartbeat posture, exact cohort drill-down, refinement, cohort replacement, and scope
clearing across both operator action and dashboard refresh. Existing selected-Node assertions
remain scoped to the selected record so cohort summaries cannot accidentally satisfy detail
evidence checks.

Observed focused result: 43 UI tests passed and the production UI build completed successfully.

## Required Closeout

Commit this bounded slice and run `make agent-workflow-check`, `make release-check`, and
`make review-candidate` on the exact clean commit. Passing checks do not authorize deployment,
configuration enforcement, group rollout, Node control, release, external-review closure, or UAT
acceptance.

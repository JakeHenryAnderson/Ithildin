# Command Center Node Governed-Run Correlation Implementation Handoff

Status: implemented; focused checks, fresh observed POC evidence, and the complete dirty-worktree
release gate passed. A clean exact candidate and review packet are still required for handoff.

Current governed tool count: `24`.

## Implemented Slice

- The Node-authenticated governed-read service supplies only server-known origin fields to the
  existing Agent Run creation path: Gateway-derived Node identity, enrolled workspace context,
  read-only authorization profile, signed configuration generation/digest, prohibited offline
  fallback, and unproven runner enforcement.
- Existing run metadata is merged atomically. A repeated call that conflicts with persisted
  authority provenance fails before the run counter or last request is changed.
- The existing run evidence export exposes a bounded `origin` object. Generic MCP and guided-demo
  runs retain `origin: null` and their existing presentation.
- Command Center labels these runs as Node-authenticated governed sessions, distinguishes
  Gateway-derived Node identity from reported identity, and shows an authority snapshot with the
  exact Node, profile, configuration, offline posture, and runner-enforcement non-claim.
- A selected Node can open the existing Missions / Agent Runs surface with exact principal and
  workspace filters. This action reads persisted Gateway records; it does not contact the Node,
  dispatch a mission, control a runner, or infer endpoint coverage.
- The deterministic signed-request POC records and checks the persisted run correlation and safe
  evidence-export origin in addition to its existing restart, replay, partition, denial, and audit
  evidence.

## Focused Validation

Passed during implementation:

```sh
uv run ruff check apps/api/src/ithildin_api/agent_runs.py \
  apps/api/src/ithildin_api/app.py apps/api/src/ithildin_api/tool_calls.py \
  tests/test_api_service.py
uv run mypy apps/api/src/ithildin_api/agent_runs.py \
  apps/api/src/ithildin_api/app.py apps/api/src/ithildin_api/tool_calls.py
uv run pytest \
  tests/test_api_service.py::test_agent_run_rejects_conflicting_authority_provenance \
  tests/test_api_service.py::test_node_governed_read_uses_derived_identity_workspace_and_durable_replay -q
(cd apps/ui && npm test -- --run App.test.tsx)
(cd apps/ui && npm run build)
```

Observed results: two focused Python tests passed, 37 UI tests passed, the production UI build
passed, and the focused Ruff/mypy checks passed.

The fresh real-process POC also passed:

```sh
make track-b-node-governed-access-evidence-check
```

Its checker confirmed both configuration-bound Node runs were persisted and exported with matching
Gateway authority origin across a real Gateway restart, alongside all prior denial, replay,
partition, audit-chain, file-mode, redaction, and 24-tool invariants.

## Required Closeout

Before this slice is review-ready:

1. commit this bounded slice, then pass `make release-check` and `make review-candidate` on that
   exact clean commit;
2. review the final diff for capability expansion, source-language drift, sensitive metadata, and
   any change to the 24-tool lock;
3. record the exact commit and review-packet path in the final handoff; the generated packet is the
   non-self-referential candidate-identity record.

## Explicit Non-Claims

This slice does not prove runner or model enforcement, all endpoint activity, filesystem isolation,
or host non-bypass. It adds no mission dispatch, runner lifecycle, endpoint query, Node write or
network authority, arbitrary host control, remote MCP, production identity, or new governed tool.
Evidence and passing tests do not authorize release, approval, UAT acceptance, or public security
claims.

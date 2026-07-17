# Post-ERG-005 Parallel Work Queue

Status: bounded work queue for progress that may continue while the ERG-005 operator walkthrough
waits for a human pass.

Historical scope note: this queue predates the separately authorized Track B Node and current
Command Center implementation milestones. Its `Command Center Integration Prep` section records the
then-current display-only boundary; it is not the current implementation roadmap and grants no new
authority.

This queue exists so adjacent work does not blur the ERG-005 checkpoint. The trusted artifact
promotion walkthrough remains ready for a guided human pass, but not every useful improvement has
to wait on that walkthrough.

## Boundary

Allowed work in this queue is limited to documentation, evidence packaging, generated packet
navigation, readiness checks, and implementation planning that does not change runtime authority.

This queue does not approve:

- new governed tools or tool-power classes;
- broader trusted-host promotion behavior;
- host writes beyond the existing staging-only trusted-host promotion slice;
- Command Center execution, policy, approval, audit, or enforcement authority;
- sandbox/VM orchestration;
- SIEM adapters or compliance automation;
- production identity, runtime Postgres, hosted telemetry, or remote MCP;
- public/security-product positioning.

Any task that requires one of those changes stops this queue and becomes a separate reviewed
capability, architecture, or product-risk sprint.

## Workstreams

### Operator Walkthrough Polish

Goal: make the human walkthrough easier to execute without changing what the walkthrough proves.

Good tasks:

- tighten the first-read order for the ERG-005 walkthrough packet;
- add expected-observation checklists for each step;
- reduce duplicate historical routing language where it confuses the active ERG-005 path;
- add reset and cleanup notes that do not run services or mutate runtime state.

Done when: an operator can start from `05_LIVE_WALKTHROUGH_PREP.md` and understand the exact
evidence to inspect, the expected result, and what remains unproven.

### Command Center Integration Prep

Goal: keep the future Ithildin Command Center integration display-only and evidence-driven.

Good tasks:

- improve display/import fixture documentation;
- add acceptance-matrix wording for display-only dashboards;
- clarify that Command Center consumes Ithildin evidence and does not become the enforcement layer;
- prepare handoff prompts or fixture manifests for a separate Command Center repo without adding
  Ithildin API callbacks or polling behavior.

Done when: Command Center can be told what to display and what not to claim without changing
Ithildin runtime behavior.

### Enterprise Evidence Clarity

Goal: reduce reviewer confusion in the generated enterprise packets.

Good tasks:

- clarify active `ERG-005` versus historical `ERG-003`/`ERG-002` references;
- add front-door navigation notes to generated or committed review docs;
- tighten wording around `ready`, `blocked`, `planning_only`, and `external_pending`;
- keep historical lineage where required by gates, but make the current next action obvious.

Done when: a reviewer can tell which lane is active now, which lanes are historical, and which
commands are for response intake rather than implementation.

### Next-ERG Planning

Goal: keep the enterprise roadmap moving without jumping into runtime changes.

Good tasks:

- prepare design-only decision packets for production identity/storage, SIEM-shaped exports,
  compliance mapping, or public-positioning decisions;
- add response-kit and closure-gate documentation for those lanes;
- update dependency-ladder wording so ERG sequencing stays explicit.

Done when: the next architecture or product-risk lane has a packet that can be reviewed without
granting runtime authority.

### Dev-Speed Optimization

Goal: keep iteration fast without weakening release discipline.

Good tasks:

- add or refine focused gates for narrow docs/evidence tasks;
- document which heavy gates are required only at meaningful checkpoints;
- reduce accidental long-running packet generation during small edits;
- keep `make release-check` and `make review-candidate` as authoritative full gates.

Done when: small changes have a clear focused validation path, and full gates still run before
meaningful release or handoff claims.

## Stop Conditions

Stop this queue and report status if:

- a task needs runtime behavior, host-write behavior, or Command Center authority;
- a trust-boundary regression appears;
- current artifacts disagree about active lane status in a way that cannot be resolved as wording;
- the same gate fails three times;
- a fix would require deleting historical review lineage that current gates intentionally preserve.

## Current Human Checkpoint

The ERG-005 walkthrough remains ready for the user:

- `docs/codex/erg005-walkthrough-ready-note.md`
- `var/review-packets/v3/trusted-artifact-promotion-operator-demo/05_LIVE_WALKTHROUGH_PREP.md`

Work in this queue should make that walkthrough easier to understand, not replace it or claim it has
already been performed.

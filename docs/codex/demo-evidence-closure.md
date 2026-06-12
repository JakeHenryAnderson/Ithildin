# Demo Evidence Closure

Status: release-readiness gate.

Demo evidence closure turns the local operator workbench demo into a repeatable handoff bundle. It
validates optional `DEMO_FLOW_RESULT.md` output when present, packages readiness/reset/state
artifacts, and gives reviewers a compact packet for the demo evidence path; it does not add run
controls, sandbox orchestration, SIEM adapters, production identity, runtime Postgres, hosted
telemetry, remote MCP, shell, Docker, Kubernetes, browser automation, arbitrary HTTP, broad
filesystem writes, plugin SDK work, or new governed tool powers.

Boundary shorthand: this sprint does not add run controls.

## Commands

- `make demo-flow-result-check` validates `DEMO_FLOW_RESULT.md` if it exists.
- `make demo-observed-summary` writes a compact post-demo summary with proposal, approval, run,
  audit, and run-evidence export pointers when observed artifacts exist.
- `make demo-evidence-packet` writes a focused packet under `var/review-packets/v3/demo-evidence/`.
- `make demo-evidence-readiness` validates command, docs, packet, release, and no-new-powers wiring.

The result checker returns `not_run` and still passes when `DEMO_FLOW_RESULT.md` is absent. That is
intentional: `make demo-flow` requires a running local API/UI demo stack and should remain an
operator decision, not a release-check side effect. When the result file exists, the checker requires
safe demo labels, proposal/approval IDs, audit verification status, candidate run IDs, reset
guidance, and obvious secret/diff exclusion.

## Packet Artifacts

`make demo-evidence-packet` writes:

- `00_DEMO_EVIDENCE_INDEX.md`
- `01_DEMO_EVIDENCE_REVIEW_PROMPT.md`
- `02_DEMO_COMMAND_SEQUENCE.md`
- `03_DEMO_RESULT_CHECK.md`
- `04_DEMO_ARTIFACT_POINTERS.md`
- `DEMO_READINESS_SUMMARY.md`
- `DEMO_STATE_REPORT.md`
- `DEMO_RESET_GUIDE.md`
- `DEMO_FLOW_RESULT_CHECK.json`
- `DEMO_OBSERVED_SUMMARY.md`
- `demo-evidence-artifact-hashes.json`

## Gate

`make demo-evidence-readiness` checks:

- the Make targets exist;
- `make demo-evidence-readiness` is included in `release-check`;
- `make demo-evidence-packet` is included in `review-candidate`;
- README and the reproduction map mention the new commands;
- this doc is included in review docs and docs-site inputs;
- tool count remains `15`;
- no-new-powers and tool-surface guardrails still pass.

## Boundary

This closure packet is not a live demo runner, runtime fixture loader, browser automation harness,
repair workflow, rollback tool, sandbox controller, SIEM adapter, compliance workflow, or production
deployment proof. It does not prove OS isolation, host compromise resistance, custody-grade audit,
external notarization, or activity outside Ithildin-mediated actions.

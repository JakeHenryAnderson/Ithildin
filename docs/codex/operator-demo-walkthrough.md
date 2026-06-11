# Operator Demo Walkthrough

Status: release-readiness artifact.

`make demo-operator-walkthrough` generates the front-door local operator demo artifact at
`var/review-packets/v3/operator-workbench/OPERATOR_DEMO_WALKTHROUGH.md`.

The command is read-only. It checks the existing live-demo preflight and operator workbench
readiness reports, then writes a secret-free Markdown guide with:

- expected review-console screens;
- expected evidence files;
- the next human demo commands;
- manual/optional steps;
- warnings and failures from the local readiness reports;
- reset guidance for repeatable demos;
- explicit no-new-powers and non-production boundaries.

## Intended Reading Order

For the operator workbench packet, open:

1. `WORKBENCH_DEMO_INDEX.md`;
2. `OPERATOR_DEMO_WALKTHROUGH.md`;
3. `DEMO_OBSERVED_SUMMARY.md` when an observed demo exists;
4. `DEMO_FLOW_RESULT.md` after `make demo-flow`;
5. `RUN_EVIDENCE_EXPORT.json` after Export Run Evidence;
6. `OPERATOR_DEMO_GUIDE.md`;
7. `DEMO_STATE_REPORT.md`;
8. `DEMO_READINESS_SUMMARY.md`;
9. `WORKBENCH_DEMO_SMOKE.md`;
10. `DEMO_RESET_GUIDE.md`.

## Boundary

The walkthrough does not start services, call governed tools, approve actions, mutate workspaces,
manage sandbox lifecycle, export secrets, repair diagnostics, or run cleanup.
It does not add run controls. It also does not add sandbox orchestration, SIEM adapters, new governed tools, production
identity, remote MCP, hosted telemetry, shell, Docker, Kubernetes, browser automation, arbitrary
HTTP, broad filesystem writes, plugin SDK behavior, OS isolation proof, SIEM custody, compliance
automation, or activity evidence outside Ithildin-mediated actions.

## Validation

The command is wired into:

- `make demo-workbench`;
- `make workbench-evidence-packet`;
- `make workbench-readiness`;
- `make release-check` through the workbench readiness gate;
- docs-site and review-doc metadata.

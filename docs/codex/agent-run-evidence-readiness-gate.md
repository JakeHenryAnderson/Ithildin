# Agent Run Evidence Readiness Gate

Status: release-readiness gate. `make agent-run-evidence-readiness` validates that Agent Run
evidence contracts, export design, timeline readiness, incident reconstruction, dashboard evidence,
and no-new-powers checks agree before release handoff.

This gate does not add runtime behavior, export endpoints, MCP tools, policy rules, SIEM adapters,
sandbox controls, production identity, runtime Postgres, hosted telemetry, shell, Docker,
Kubernetes, browser automation, arbitrary HTTP, broad filesystem writes, or plugin SDK work.

## Included Checks

- `agent-run-evidence-contract-check`
- `agent-run-evidence-export-check`
- `agent-run-evidence-export-plan-check`
- `agent-run-evidence-export-implementation-gate`
- `agent-run-timeline-readiness`
- `incident-reconstruction-check`
- `dashboard-evidence-checklist-check`
- `no-new-powers-guardrail`
- `tool-surface-invariant-gate`

## Claims

- tool count remains `24`;
- runtime changes are not allowed;
- run export runtime behavior is not allowed;
- new powerful tool classes are not allowed;
- Agent Run evidence remains secret-free and design-only where export behavior is concerned;
- incident reconstruction covers mediated actions only;
- dashboard evidence review is operator-facing evidence, not SIEM custody or compliance automation.

## Operator Use

Run:

```sh
make agent-run-evidence-readiness
```

The gate is included in `make release-check`. A failure means release/review handoff should pause
until the mismatched documentation, packet, or guardrail evidence is corrected.

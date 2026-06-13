# Observability Readiness Gate

Status: release-readiness gate. This document does not add runtime behavior, API endpoints, MCP
tools, tool manifests, policy rules, executors, sandbox orchestration, SIEM adapters, hosted
telemetry, or new governed tool powers.

This gate validates that Ithildin's next observability direction remains evidence/design work unless
a later explicit implementation decision says otherwise.

## Command

```bash
make observability-readiness
```

## What It Checks

The gate composes:

- `make agent-run-evidence-contract-check`;
- `make siem-evidence-design-check`;
- `make next-capability-readiness`;
- `make no-new-powers-guardrail`;
- `make tool-surface-invariant-gate`;
- sandbox/workspace boundary contract wiring.

## Expected Result

The expected result is:

- tool count remains `20`;
- Agent Run evidence remains secret-free;
- sandbox/workspace posture remains operator-managed and design/evidence-only;
- SIEM-shaped evidence remains export-design-only with no adapters;
- next capability candidate is `project.structure.summary`, design-only selected, and
  implementation-blocked;
- broader capability expansion remains blocked;
- no new powerful tool classes are allowed.

## Non-Goals

This gate does not approve sandbox orchestration, process control, SIEM adapters, hosted telemetry,
new tools, production identity, runtime Postgres, remote MCP, shell, Docker/Kubernetes, browser
automation, arbitrary HTTP, broad filesystem writes, plugin SDK work, or public/security-product
positioning.

# Agent Run Operations Readiness Gate

Status: release-readiness gate. This gate validates the read-only operations dashboard surface for
Agent Runs. It does not add runtime behavior beyond the existing bounded read APIs, tool manifests,
executors, policy rules, MCP tools, sandbox controls, SIEM adapters, production identity, runtime
Postgres, hosted telemetry, shell, Docker, Kubernetes, browser automation, arbitrary HTTP, or broad
filesystem writes.

`make agent-run-operations-readiness` verifies that the Agent Run operations surface remains
admin-only, read-only, secret-free, and tied to the local-preview no-new-powers boundary.

## Checked Surfaces

- `GET /runs` supports bounded read-only filters: `principal_id`, `workspace_id`, `status`,
  `tool_name`, `session_id`, and `limit`.
- `GET /runs` returns `summary` evidence with returned counts, applied filters, workspace counts,
  principal counts, status counts, tool counts, and latest update timestamp.
- Unknown query parameters, malformed limits, and unsafe filter values fail closed with safe
  errors.
- The review console shows a compact read-only operations dashboard with filters, summary chips,
  timeline status evidence, warning chips, and the existing Export Run Evidence action.
- Export Run Evidence remains a read-only download of the secret-free run evidence bundle.

## Non-Claims

Passing this gate provides no run controls, no sandbox orchestration, no SIEM adapters, production
identity, runtime Postgres, hosted telemetry, shell execution, Docker or Kubernetes control,
browser automation, arbitrary HTTP, broad filesystem writes, compliance automation, or a production
security-product claim.

The tool count remains `24`. No new governed tools, manifests, executor capabilities, policy rules,
MCP exposure, or power classes are added.

## Verification

Run:

```text
make agent-run-operations-readiness
```

The gate validates source wiring, API tests, UI tests, README/review-doc/docs-site inclusion,
`release-check` inclusion, `no-new-powers-guardrail`, and `tool-surface-invariant-gate`.

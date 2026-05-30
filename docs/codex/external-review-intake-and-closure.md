# External Review Intake and Closure

Task 111 defines how Ithildin handles GPT 5.5 Pro / Very High or human expert review findings after
the v0.3-prep packet is handed off. It is a closure workflow, not a claim that external review has
already happened.

## Intake Steps

1. Save the reviewer response alongside the generated review packet evidence.
2. Convert each actionable issue into one Markdown finding under `docs/codex/findings/`.
3. Use finding IDs with the `EXT-###` prefix for external review findings.
4. Populate every field from [reviewer-finding-template.md](reviewer-finding-template.md):
   severity, area, affected files/functions, claim tested, observed behavior, risk, recommended
   fix, blocking status, disposition, and verification notes.
5. Run:

```sh
make reviewer-findings-check
```

6. Update [source-review-closure-matrix.md](source-review-closure-matrix.md) only after the finding
record validates.

## Closure Rules

- Critical/high open findings stop autonomous implementation until a user/external-review decision
  accepts the risk, scopes a fix task, or changes the boundary.
- Blocking findings must remain visible in the closure matrix until fixed or explicitly accepted as
  deferred with rationale.
- Internal AI/subagent findings can inform backlog work but cannot close external/source review
  rows.
- Documentation-only findings should still be recorded if they affect boundary honesty, release
  claims, or reviewer reproducibility.
- A row is externally closed only when reviewer identity, date, inspected area, finding count,
  blocking status, disposition, and closure evidence are recorded.

## Verification After Intake

After converting findings and applying any fixes, run:

```sh
make reviewer-findings-check
make release-check
make review-candidate
```

If any finding requires implementation changes, commit the fix separately from the intake record
where practical. If a finding proposes a new powerful tool class, production identity, runtime
Postgres, hosted telemetry, remote MCP, shell/Docker/Kubernetes/browser tools, plugin SDK, broad
network access, or broad filesystem writes, treat it as a boundary decision rather than a normal
fix.

## Handoff Status

Until an external reviewer response is received and converted, the source-review closure matrix
should remain `pending external review` for external rows.

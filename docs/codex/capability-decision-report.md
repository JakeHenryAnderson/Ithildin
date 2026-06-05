# Capability Decision Report Generator

Task 169 adds `make capability-decision-report`, a roll-up report for the v0.5 go/no-go posture.
It is intentionally conservative: it summarizes gates, blockers, accepted risks, findings, and tool
surface evidence, but it does not approve new governed tool powers.

## Command

```bash
make capability-decision-report
uv run python scripts/capability_decision_report.py --json
```

The command exits successfully when the report can be generated and hard invariants are intact. A
`decision: blocked` result is expected while external/source review rows remain pending or a future
capability class lacks a separate explicit implementation decision.

## Inputs

- [v0.5-milestone-manifest.json](v0.5-milestone-manifest.json)
- [source-review-closure-matrix.md](source-review-closure-matrix.md)
- [accepted-risk-register.md](accepted-risk-register.md)
- `make capability-expansion-gate`
- `make tool-surface-invariant-gate`
- `make review-findings-summary`

## Current Meaning

The report is suitable for handoff and planning. It is not a capability-expansion approval. New powerful
tool planning remains blocked until external/source review closure, accepted-risk disposition, and a
separate explicit capability decision are recorded. The bounded v0.9 `git.show.commit_metadata`
implementation has its own separate gate and internal xhigh lane-closure summary; it does not unlock
broader capability implementation. The follow-on `git.show.ref_summary` material is design-only and
checked with `make git-ref-summary-proposal-check` and
`make git-ref-summary-implementation-plan-check`; it does not authorize runtime implementation.

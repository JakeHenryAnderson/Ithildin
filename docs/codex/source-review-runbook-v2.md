# Source Review Runbook v2

Task 157 defines the repeatable source-review workflow for the v0.5 review-closure track. It is a
runbook for internal reviewers, high-intelligence AI/subagent pressure tests, GPT 5.5 Pro / Very
High, or human experts. It does not close any external review row by itself and does not authorize
new governed tool powers.

## Boundary

The reviewed runtime boundary remains the v0.1 local-preview boundary:

- ten narrow governed tools only;
- stdio-only local MCP;
- SQLite runtime storage only;
- local principal labels, not production identity;
- local tamper-evident and locally signed evidence, not custody-grade or notarized proof;
- no shell, Docker socket, Kubernetes, browser automation, arbitrary HTTP, broad filesystem writes,
  hosted telemetry, remote MCP, plugin SDK, runtime Postgres, managed model serving, or production
  identity.

If a review finding requires changing that boundary, stop the sprint and record a boundary decision
instead of treating it as an ordinary fix.

## Pre-Review Commands

Run these before handing source to a reviewer:

```sh
make release-check
make review-candidate
make internal-review-packet
make capability-expansion-gate
make tool-surface-invariant-gate
make evidence-confusion-gate
make external-review-closure-gate
```

Expected current state:

- release and candidate gates pass;
- capability expansion reports blocked;
- tool surface remains exactly ten tools;
- evidence wording is local/non-production where applicable;
- external closure is valid but incomplete while rows remain `external_pending`.

## Source Review Sequence

1. Choose one review area from [source-review-closure-matrix.md](source-review-closure-matrix.md).
2. Open the files/functions listed in the matrix or the matching source checklist.
3. Compare implementation behavior to the relevant contract document and tests.
4. Record whether existing tests prove, partially prove, or do not prove each claim.
5. Create one finding per actionable issue using
   [reviewer-finding-template.md](reviewer-finding-template.md).
6. Run `make reviewer-findings-check` and `make review-findings-summary`.
7. Update the closure matrix only after finding validation passes.
8. Run `make release-check` after any fix or closure metadata update.

## Review Areas

Review these areas before any future capability-expansion decision:

| Area | Primary Contract / Packet | Minimum evidence command |
| --- | --- | --- |
| Patch apply | [patch-apply-state-machine.md](patch-apply-state-machine.md) | `make release-check` |
| Filesystem | [filesystem-executor-contract.md](filesystem-executor-contract.md) | `make filesystem-contract-check` |
| HTTP fetch | [http-fetch-executor-contract.md](http-fetch-executor-contract.md) | `make release-check` |
| Signed evidence | [evidence-contracts.md](evidence-contracts.md) | `make signed-evidence-demo-verify` |
| Policy parity | policy preview/runtime parity docs and fixtures | `make policy-parity` |
| MCP ingress | MCP ingress bypass audit and adapter tests | `make release-check` |
| Review console | review-console assurance and UI build | `npm run build --prefix apps/ui` |

Task 158 adds a source-file inspection packet. Tasks 159-165 add area-specific checklists for the
highest-risk surfaces.

## Finding Rules

- Critical/high open findings stop autonomous implementation.
- Blocking findings stop release handoff until fixed, rejected with rationale, or accepted as
  deferred by an explicit user/external-review decision.
- Internal AI/subagent findings use `AI-###` or `SUB-###`.
- Internal manual findings use `ISR-###`.
- External GPT/human findings use `EXT-###`.
- External rows may not be closed by internal review.
- A closure row needs reviewer, date, finding count, blocking status, fixed commit or accepted-risk
  link, and verification command.

## Stop Conditions

Stop and report status if:

- the same trust-boundary test fails three times;
- a fix would require a new tool class or broadened executor power;
- a source review finds a critical/high issue;
- evidence wording would need to claim sandboxing, custody, notarization, production identity, or
  production security;
- `make release-check`, `make tool-surface-invariant-gate`, or
  `make external-review-closure-gate` fails for a boundary reason.

## Output

A completed review pass should produce:

- validated finding records, if any;
- updated [source-review-closure-matrix.md](source-review-closure-matrix.md);
- command output for the verification gate;
- a clear decision: continue hardening, request external consultation, accept/defer risk, or stop
  before capability expansion.

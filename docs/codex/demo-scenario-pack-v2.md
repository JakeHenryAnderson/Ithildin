# Demo Scenario Pack v2

Task 146 turns the local-preview demo surface into a reviewer-oriented scenario pack. It does not add new tool powers or new API endpoints. It points reviewers at existing commands and describes
what each scenario demonstrates.

The pack reinforces that Ithildin is not production security software.

## Scenarios

| Scenario | Command | What It Demonstrates | What It Does Not Prove |
| --- | --- | --- | --- |
| Release gate | `make release-check` | Manifest lock, guardrails, tests, lint, typecheck, docs, and UI build are green. | External source review or production readiness. |
| Filesystem evidence | `make filesystem-contract-check` | Local OS and filesystem capability evidence for macOS/Linux local-preview claims. | Windows/WSL security support or kernel sandboxing. |
| Compose smoke | `make demo-seed`, `make compose-up`, `make compose-smoke` | Local API/UI reachability on loopback with seeded demo workspace. | Production deployment hardening or remote hosting safety. |
| Governed flow | `make demo-flow` | MCP-mediated read, redaction, patch proposal, approval-gated apply, audit verification, and export against the demo workspace. | Broad filesystem writes, shell execution, or crash-recovery repair. |
| Operator-managed sandbox demo | `make operator-sandbox-demo-readiness` | The workbench demo guide, scenario pack, no-new-powers, and tool-surface checks all agree that Ithildin mediates an operator-managed workspace or sandbox. | Sandbox lifecycle control, container/VM orchestration, Docker socket access, or OS isolation. |
| Operator sandbox smoke evidence | `make operator-sandbox-demo-smoke`, `make operator-sandbox-dashboard-checklist`, `make operator-sandbox-demo-packet` | Secret-free smoke transcript, static dashboard checklist, and focused demo packet for the operator-managed workbench story. | Browser automation, screenshot proof, production UX review, sandboxing, or SIEM custody. |
| Agent Run correlation | `make agent-run-correlation-smoke`, `make agent-run-correlation-packet` | Secret-free mapping from mediated run records to tool calls, policy evidence, approvals, audit events, diagnostics, and run evidence export. | Proof of activity outside Ithildin, SIEM custody, production compliance, or run-control behavior. |
| Live demo readiness | `make live-demo-preflight`, `make live-demo-status`, `make live-demo-smoke`, `make live-demo-evidence-summary`, `make live-demo-packet` | Secret-free preflight, operator status/index, smoke transcript, evidence digest, and focused packet tying Compose loopback posture, no Docker socket mount, operator sandbox demo, Agent Run correlation, signed evidence, and no-new-powers checks into one local demo handoff. | OS isolation, production deployment safety, SIEM custody, compliance automation, or sandbox lifecycle control. |
| Operator workbench | `make workbench-readiness`, `make workbench-evidence-packet`, `make demo-workbench-smoke`, `make demo-workbench` | Read-only local operator workbench gate, focused packet, deterministic smoke transcript, and evidence-only wrapper tying Agent Runs, approvals, audit status, live-demo artifacts, sandbox/workspace posture, and handoff pointers together. | Run controls, sandbox orchestration, SIEM adapters, production identity, or new governed tool powers. |
| Negative denials | `make negative-review-transcripts` | Observed denial transcripts for traversal, symlink escape, stale patch, blocked HTTP redirect, disabled/unknown principals, replay, and signed-evidence tamper. | Exhaustive adversarial proof or external validation. |
| Locally signed evidence | `make signed-evidence-demo`, then `make signed-evidence-demo-verify` | Non-production local Ed25519 signing and tamper rejection for audit export and manifest-lock demo artifacts. | Hosted notarization, custody-grade evidence, or official supply-chain signing. |
| Review packet | `make review-candidate` | Full handoff packet regeneration, redaction scan, consolidated attachments, docs site, and artifact hashes. | That reviewer conclusions are closed. |

## Operating Notes

- Run `make demo-seed` before any scenario that expects `workspaces/demo/`.
- `make demo-flow` mutates only the ignored seeded demo workspace.
- Docker is used only for the local Compose stack; there is no Docker socket mount and no Docker or
  Kubernetes governed tool.
- The scenario pack is evidence choreography. It should be read alongside
  [reviewer-reproduction-map.md](reviewer-reproduction-map.md),
  [negative-review-recipes.md](negative-review-recipes.md), and
  [redaction-evidence-boundary.md](redaction-evidence-boundary.md).

## Reviewer Outcome

After these scenarios pass, the right conclusion is:

> The local-preview handoff artifacts are reproducible and the observed demo paths match the
> documented narrow boundary.

The wrong conclusion is:

> Ithildin is production security software, an OS sandbox, or ready for broader tool powers.

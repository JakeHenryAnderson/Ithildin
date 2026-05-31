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

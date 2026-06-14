# Demo Flow Readiness Gate

Status: release-readiness gate.

The demo-flow readiness slice makes the optional mediated local demo easier to inspect after it
runs. It adds a secret-free result summary, read-only reset guidance, dashboard recognition for demo
metadata, and release/readiness checks. It does not add run controls, sandbox orchestration, SIEM
adapters, production identity, runtime Postgres, hosted telemetry, remote MCP, shell, Docker,
Kubernetes, browser automation, arbitrary HTTP, broad filesystem writes, plugin SDK work, or new
governed tool powers.

## Commands

- `make demo-flow` runs the existing governed local demo and writes `DEMO_FLOW_RESULT.md`.
- `make demo-reset-guide` writes `DEMO_RESET_GUIDE.md`.
- `make demo-flow-readiness` validates command, docs, packet, UI, and no-new-powers wiring.

`make demo-flow` still requires the local API/UI path to be available. The flow uses the existing
MCP/governed tool path for reads, redaction, patch proposal, approval request, approval decision,
patch apply, audit verification, and audit export. The result artifact records safe identifiers and
candidate run IDs only.

## Generated Artifacts

- `var/review-packets/v3/operator-workbench/DEMO_FLOW_RESULT.md`
- `var/review-packets/v3/operator-workbench/DEMO_RESET_GUIDE.md`

`DEMO_FLOW_RESULT.md` includes `scenario: guided_local_demo`, `demo_step`, proposal ID, approval
ID, patched demo path, audit verification status, audit export metadata hashes, candidate run IDs
when available, and cleanup/reset pointers. It excludes prompts, secrets, file contents, unified
diffs, response bodies, package scripts, dependency names, raw sensitive paths, private keys, and
environment values.

## Dashboard Recognition

The review console can show a compact `demo` label when a run carries explicit demo metadata such as
`scenario: guided_local_demo` or a demo-oriented session/client label. This is display-only. It is
not authorization, policy evaluation, mutation, run control, sandbox control, or evidence signing.

## Reset Guidance

`DEMO_RESET_GUIDE.md` explains the normal reset path:

1. Run `make compose-down` if the local stack was started.
2. Run `make demo-seed` to restore tracked sample files into the ignored demo workspace.
3. Run `make demo-state-report`.
4. Run `make demo-readiness-summary`.
5. Run `make demo-workbench`.

It also explains how to inspect partially completed demo states without automatic repair or
rollback. Recovery remains read-only guidance in this slice.

## Gate

`make demo-flow-readiness` checks:

- `make demo-flow`, `make demo-reset-guide`, and `make demo-flow-readiness` exist;
- `make demo-flow-readiness` is in `release-check`;
- `make demo-reset-guide` is in the evidence-only `demo-workbench` wrapper;
- README and the reproduction map mention demo-flow result and reset guidance;
- the workbench packet references `DEMO_FLOW_RESULT.md`, `DEMO_RESET_GUIDE.md`, and
  `10_DEMO_RESET_GUIDE.md`;
- the review console and UI tests include display-only demo recognition;
- tool count remains `22`;
- no-new-powers and tool-surface guardrails still pass.

## Boundary

This gate does not prove OS isolation, SIEM custody, compliance automation, production security,
host compromise resistance, external notarization, or activity outside Ithildin-mediated actions.
It is demo/readiness polish for the local operator workbench only.

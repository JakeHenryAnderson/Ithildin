# Live Demo Runbook

This runbook prepares a local Ithildin demo that shows a governed control plane around an
operator-managed workspace or sandbox. It is a local-preview demo only. Ithildin does not start
containers, mount Docker sockets, run shell commands through governed tools, manage Kubernetes,
provide OS isolation, provide SIEM custody, or claim production security.

## Preflight

Run the secret-free preflight first:

```sh
make live-demo-preflight
```

Expected result: the report passes core checks for repo markers, tool count `14`, loopback Compose
ports, no Docker socket mount, read-only Compose posture, SQLite storage, telemetry disabled, demo
workspace inputs, no-new-powers, and tool-surface invariants. Warnings may appear for optional
runtime signing keys or missing Docker Compose.

For an operator-oriented snapshot at any point, run:

```sh
make live-demo-status
```

This writes `var/review-packets/v3/live-demo/LIVE_DEMO_INDEX.md`. It summarizes preflight state,
Compose visibility, local API/UI reachability if the stack is already running, generated packet
paths, next actions, and cleanup reminders. It does not start or stop services.

## Setup

Use a local token before sharing the demo outside your machine:

```sh
make admin-token-generate
```

Copy the generated value into `.env` if needed. The sample `.env.example` token is acceptable only
for a local private demo and should remain visibly treated as dev-token mode.

Seed the ignored demo workspace:

```sh
make demo-seed
```

Start the local Compose stack:

```sh
make compose-up
```

Expected local endpoints:

- API: `http://127.0.0.1:8000`
- UI: `http://127.0.0.1:5173`

Run the smoke check:

```sh
make compose-smoke
```

If `compose-smoke` fails, run `make live-demo-status` before troubleshooting. The status report
will show whether the API and UI are reachable on localhost.

## Demo Flow

Run the governed flow:

```sh
make demo-flow
```

This demonstrates MCP-mediated reads, redaction, patch proposal, approval-gated patch apply, audit
verification, and export against the seeded demo workspace. It mutates only ignored demo workspace
content.

Open the review console at `http://127.0.0.1:5173` and inspect:

- System Trust warnings and tool count;
- registered tools and manifest evidence;
- approval binding evidence;
- Agent Runs `Demo Path`, filters, summary, grouped timeline evidence, and read-only evidence
  export;
- signed export buttons and audit status.

## Evidence Commands

Generate the local evidence packets:

```sh
make live-demo-status
make live-demo-smoke
make live-demo-evidence-summary
make operator-sandbox-demo-packet
make agent-run-correlation-packet
make negative-review-transcripts
make signed-evidence-demo
make signed-evidence-demo-verify
make live-demo-packet
```

Expected ignored outputs:

- `var/review-packets/v3/operator-sandbox-demo/`
- `var/review-packets/v3/agent-run-correlation/`
- `var/review-packets/v0.2/negative-review-transcripts/`
- `var/review-packets/v0.2/signed-evidence-demo/`
- `var/review-packets/v3/live-demo/`

`make live-demo-status` writes `var/review-packets/v3/live-demo/LIVE_DEMO_INDEX.md`, a compact
operator index with paths, status, and cleanup reminders.
`make live-demo-smoke` writes `var/review-packets/v3/live-demo/LIVE_DEMO_SMOKE.md`, a
secret-free transcript of readiness checks plus the operator-run sequence.
`make live-demo-evidence-summary` writes
`var/review-packets/v3/live-demo/LIVE_DEMO_EVIDENCE_SUMMARY.md`, a secret-free digest of live-demo
status, smoke evidence, signed fixture evidence, negative transcripts, Agent Run correlation,
operator sandbox packet, and consolidated handoff artifact presence.

For the full handoff bundle, run:

```sh
make review-candidate
```

For an evidence-only operator workbench wrapper that does not start services, call governed tools,
or approve actions, run:

```sh
make demo-workbench
```

This refreshes live-demo status, smoke, evidence summary, operator sandbox packet, Agent Run
correlation packet, demo readiness summary, and the focused operator workbench packet.

For a one-page readiness digest without regenerating the full packet, run:

```sh
make demo-readiness-summary
```

For only the deterministic operator-flow transcript, run:

```sh
make demo-workbench-smoke
```

The focused workbench packet also writes
`var/review-packets/v3/operator-workbench/WORKBENCH_DEMO_INDEX.md`, the first file to open for the
operator workbench handoff, and `DEMO_READINESS_SUMMARY.md` as the ready/missing/optional/deferred
status page. The same packet includes `07_WORKBENCH_DEMO_STORY.md` as the happy-path narrative from
preflight through cleanup.

## MCP Client Companion

For stdio MCP client demos, use:

```sh
uv run python -m ithildin_mcp_server
```

Use the local MCP recipes in [mcp-inspector-recipes.md](mcp-inspector-recipes.md). The MCP adapter
stays an ingress adapter and does not own policy, execution, redaction, or audit semantics.

## Cleanup

Stop the local Compose stack:

```sh
make compose-down
```

The demo does not require committing ignored runtime evidence, local keys, SQLite databases, audit
JSONL files, generated review packets, or seeded workspaces.

## Failure Paths

- Preflight failure: fix listed failures before starting services.
- Compose unavailable: run non-Compose evidence commands and skip the local API/UI demo.
- API unreachable: run `make compose-up`, then `make compose-smoke`.
- UI unreachable: confirm the UI service is published on `127.0.0.1:5173`.
- Demo flow failure: keep generated diagnostics, run `make live-demo-status`, and avoid rerunning
  mutating steps until the failure is understood.
- Cleanup uncertainty: run `make compose-down`.

## What The Demo Proves

The demo can show that local-preview handoff artifacts are reproducible, the operator-managed
workspace story is coherent, and observed mediated actions can be correlated across Ithildin's
dashboard, Agent Run evidence, audit events, approvals, diagnostics, and local evidence packets.

## What The Demo Does Not Prove

The demo does not prove OS isolation, production deployment safety, compliance automation, SIEM
custody, host compromise resistance, production identity, remote MCP safety, broad capability
approval, or activity outside Ithildin-mediated actions.

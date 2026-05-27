# Ithildin Local Preview Release Guide

This guide describes the current v0.1 local-preview workflow. It is intended for a developer
running Ithildin locally, connecting an MCP-capable client, reviewing approvals, and exporting audit
evidence.

## Quick Start

1. Install Python 3.12, `uv`, Node/npm, and Docker Desktop if you want the Compose demo.
2. Copy `.env.example` to `.env` and change `ITHILDIN_ADMIN_TOKEN`.
3. Run `make release-check` before demoing or handing off a build.
4. Run `make demo-seed`, `make compose-up`, `make compose-smoke`, and `make demo-flow`.
5. Open `http://127.0.0.1:5173` and use the configured admin token.
6. Launch MCP from a host MCP client with `uv run python -m ithildin_mcp_server`.
7. Optional: run `make ollama-smoke` or `make local-model-demo` for host-side local model wiring.
8. Run `make docs-site` to build local handoff docs under ignored `site/`.

## Trust Inputs

- Tool manifests live under `tool-manifests/` and are hash-pinned by
  `tool-manifests.lock.json`.
- After intentional manifest edits, run `make manifest-lock`, review the lockfile diff, then run
  `make manifest-lock-check`.
- YAML policy is the default engine through `policies/default.yaml`.
- OPA mode is optional. When `ITHILDIN_POLICY_ENGINE=opa`, startup verifies
  `policies/opa/bundle.lock.json` and reports the verified bundle hash through policy/system
  status.
- Principal identities are loaded from `principals/local.yaml`; unknown or disabled principals fail
  closed in governed flows.
- SQLite is the only runtime storage backend. Postgres settings are surfaced as readiness evidence
  only.
- OpenTelemetry is disabled by default and reports only safe span metadata when enabled.

## Review Console

The local console shows:

- system trust status, manifest lock enforcement, policy hash, OPA bundle evidence, audit head, and
  configured limits;
- registered tools and short manifest hashes;
- policy previews for hypothetical tool calls;
- pending approvals with approve/deny actions;
- patch proposal details with unified diffs;
- recent audit events, audit verification, and JSONL export.

## Safety Boundaries

- Read tools are scoped to the configured workspace root.
- Patch application is stored-proposal-only and approval-gated.
- HTTP fetch is GET-only, allowlisted, and blocks non-global/private destinations.
- Tool outputs are redacted before returning to agents.
- Audit events are stored in SQLite and hash-chained JSONL.
- Docker is only used to run the local demo stack.
- Ollama local-model demos are host-side only; Ithildin does not run or proxy models.
- The generated docs site is local-only build output under `site/`.

## Deferred

- Production authentication, OIDC, SAML, and SCIM.
- Runtime Postgres storage, hosted telemetry collectors, and hosted control-plane workflows.
- Kubernetes, Docker socket access, shell execution, and broad filesystem writes.
- Cryptographic signing/notarization for manifests and audit exports.
- Managed model serving or hosted LLM control-plane workflows.

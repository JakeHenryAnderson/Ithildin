# Ithildin Local Preview Release Guide

This guide describes the v0.2 review candidate for the v0.1 local-preview runtime boundary. It is
intended for a developer running Ithildin locally, connecting an MCP-capable client, reviewing
approvals, and exporting audit evidence.

Read [Threat Model and Non-Goals](threat-model-and-non-goals.md) before treating the preview as a
security boundary. Ithildin is a local mediation layer, not production security software.
For public-preview wording, also read
[v0.1 Public Preview Release Notes](v0.1-public-preview-release-notes.md).
For v0.2 external/code review handoff, start with
[v0.2 Review Response and RC Cleanup](v0.2-review-response-and-rc-cleanup.md) and
[v0.2 Review Packet](v0.2-review-packet.md), then follow
[Reviewer Reproduction Map](reviewer-reproduction-map.md).

## Quick Start

1. Install Python 3.12, `uv`, Node/npm, and Docker Desktop if you want the Compose demo.
2. Copy `.env.example` to `.env`, run `make admin-token-generate`, and paste the generated
   `ITHILDIN_ADMIN_TOKEN=...` line into your local `.env`.
3. Run `make policy-test` for a fast YAML policy confidence check.
4. Run `make release-check` before demoing or handing off a build.
5. Optional: run `make release-evidence` and validate saved evidence with
   `make release-evidence-validate FILE=release-evidence.json`.
6. Run `make demo-seed`, `make compose-up`, `make compose-smoke`, and `make demo-flow`.
7. Open `http://127.0.0.1:5173` and use the configured admin token.
8. Launch MCP from a host MCP client with `uv run python -m ithildin_mcp_server`.
9. Use [MCP Client Examples](mcp-client-examples.md) for copy-paste stdio client snippets.
10. Use [MCP Inspector Recipes](mcp-inspector-recipes.md) for local `tools/list`, `tools/call`,
   approval-required, denial, and audit verification flows.
11. Optional: run `make review-candidate` before external review handoff.
12. Optional: run `make ollama-smoke` or `make local-model-demo` for host-side local model wiring.
13. Optional: run `make audit-keygen` to enable signed audit exports.
14. Optional: run `make audit-diagnostics` to explain local audit verification state.
15. Optional: run `make filesystem-contract-check` to record local filesystem capability evidence.
16. Run `make docs-site` to build local handoff docs under ignored `site/`.

## Trust Inputs

- Tool manifests live under `tool-manifests/` and are hash-pinned by
  `tool-manifests.lock.json`.
- After intentional manifest edits, run `make manifest-lock`, review the lockfile diff, then run
  `make manifest-lock-check`.
- Named workspaces live in trusted local config at `workspaces/local.yaml`; read, git, and patch
  proposal tools default to workspace `default` unless `workspace_id` is provided.
- Optional local manifest-lock signatures can be created with `make manifest-lock-keygen` and
  `make manifest-lock-sign`; see [Signed Manifest Locks](signed-manifest-locks.md).
- YAML policy is the default engine through `policies/default.yaml`.
- YAML policy has committed offline fixtures under `policies/tests/default.yaml`; run
  `make policy-test` before changing policy rules.
- Candidate YAML policy changes can be compared with
  `uv run python scripts/policy_impact.py --candidate-path path/to/policy.yaml` or the review
  console policy impact panel. This is read-only and fixture-driven.
- Runtime and preview policy evidence fields are summarized in
  [Evidence Contracts](evidence-contracts.md).
- Release handoff evidence schema and validation are summarized in
  [Release Evidence Schema](release-evidence-schema.md).
- Review packet artifact comparisons are summarized in
  [Review Packet Diff](review-packet-diff.md).
- OPA mode is optional. When `ITHILDIN_POLICY_ENGINE=opa`, startup verifies
  `policies/opa/bundle.lock.json` and reports the verified bundle hash through policy/system
  status.
  OPA fixture/parity execution is deferred until an explicit OPA test server or mocking layer exists;
  see [OPA Parity Decision](opa-parity-decision.md).
- Principal identities are loaded from `principals/local.yaml`; unknown or disabled principals fail
  closed in governed flows.
- The sample admin token works only when `ITHILDIN_ALLOW_DEV_ADMIN_TOKEN=true`, and the API/UI report
  that warning in system status. `make admin-token-generate` prints a strong replacement token but
  never writes `.env` automatically.
- Public-preview guardrails fail if docs omit warning labels or Compose exposes non-loopback ports.
- SQLite is the only runtime storage backend. Postgres settings are surfaced as readiness evidence
  only.
- OpenTelemetry is disabled by default and reports only safe span metadata when enabled.

## Review Console

The local console shows:

- system trust status, manifest lock enforcement, policy hash, OPA bundle evidence, audit head, and
  configured limits;
- registered tools and short manifest hashes;
- policy previews for hypothetical tool calls;
- policy impact previews for candidate YAML policy changes;
- pending approvals with approve/deny actions;
- derived approval review checks for proposal, base hash, manifest, policy, request, expiry, and
  workspace evidence;
- patch proposal details with unified diffs;
- recent audit events, audit verification, and JSONL export.
- locally signed audit export when a local signing keypair is configured.

## Safety Boundaries

- Read tools are scoped to the configured workspace root.
- Named workspace roots are still local trusted roots; they clarify scope, not OS isolation.
- Patch application is stored-proposal-only and approval-gated.
- HTTP fetch is GET-only, allowlisted, and blocks non-global/private destinations.
- Filesystem and patch executors reject symlinks, hidden/sensitive paths, binary targets, ambiguous
  text encodings, and stale patch bases.
- Filesystem and patch executor platform assumptions are documented in
  [Filesystem Executor Contract](filesystem-executor-contract.md); macOS and Linux are the
  local-preview security-supported profiles, while Windows/WSL remain unsupported/untested for
  workspace/race claims.
- Tool outputs are redacted before returning to agents.
- Redaction evidence surfaces counts and safe paths only; see
  [Evidence Contracts](evidence-contracts.md).
- Audit events are stored in SQLite and hash-chained JSONL.
- Locally signed audit exports use a local Ed25519 keypair when configured; see
  [Signed Audit Exports](signed-audit-exports.md).
- Audit diagnostics are read-only explanations for verification failures. They do not repair,
  truncate, rewrite, or bless local evidence.
- Patch apply diagnostics are read-only explanations for incomplete stored patch apply attempts.
  They do not repair approvals, roll back files, or rewrite workspace state.
- Locally signed manifest locks use a separate local Ed25519 keypair when configured; this is local
  operator evidence, not hosted supply-chain signing.
- Docker is only used to run the local demo stack.
- Ollama local-model demos are host-side only; Ithildin does not run or proxy models.
- The generated docs site is local-only build output under `site/`.

## Deferred

- Production authentication, OIDC, SAML, and SCIM.
- Runtime Postgres storage, hosted telemetry collectors, and hosted control-plane workflows.
- Kubernetes, Docker socket access, shell execution, and broad filesystem writes.
- External audit anchoring and official hosted supply-chain signing.
- Managed model serving or hosted LLM control-plane workflows.

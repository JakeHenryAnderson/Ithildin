# Ithildin

Ithildin is a local-first governed MCP/tool gateway for AI agents.

**v0.1 local-preview warning:** Ithildin v0.1 is a local-preview mediation layer for
AI-agent tool use. It is not a sandbox, EDR/MDM agent, SIEM, production identity system, hosted MCP
platform, compliance audit system, or immutable evidence store. It assumes the local host, local
admin, trusted tool manifests, and local policy files are part of the trusted computing base. Audit
records are tamper-evident local evidence, not notarized or custody-grade logs. Redaction is
best-effort leak reduction, not a guarantee that secrets cannot be exposed.

v0.1 supports narrow built-in tools only: workspace reads, git reads, stored patch proposals,
approval-gated patch apply, and exact-allowlist GET-only HTTP fetch. It deliberately does not
support shell execution, Docker socket access, Kubernetes tools, browser automation, arbitrary HTTP
methods/headers/bodies, broad filesystem writes, plugin marketplaces, hosted MCP, production
identity, or hosted telemetry.

The project goal is to let AI agents use local tools through narrow, policy-scoped, auditable interfaces instead of unrestricted endpoint access.

## Product Thesis

Ithildin is not an autonomous agent platform, an EDR product, an MDM product, or a replacement shell.

It is a trusted mediation layer between untrusted AI reasoning and sensitive local systems:

```text
Agent / local LLM
  -> MCP tools/list + tools/call
  -> Ithildin MCP Gateway
  -> schema validation + policy decision
  -> approval + audit
  -> scoped governed executors
  -> endpoint workspace / APIs / local services
```

The agent never receives direct OS access. Ithildin owns validation, policy, approval, execution, and evidence.

## MVP Target

A security-conscious developer can run Ithildin locally, connect an MCP-capable agent, expose a few safe file/git/http tools, require approval for writes, and inspect a trustworthy audit log.

## Repo Map

- `docs/obsidian/` - Obsidian-friendly strategy and architecture notes.
- `docs/codex/` - Codex-friendly implementation brief, task specs, and release notes.
- `docs/adr/` - Architecture decision records.
- `docs/research/` - source verification and research notes.
- `apps/api/` - FastAPI control plane for admin APIs, approvals, tools, policy, and audit.
- `apps/mcp-server/` - stdio MCP adapter backed by the governed tool-call pipeline.
- `apps/ui/` - local React review console.
- `packages/` - shared schemas, policy, audit, and SDK packages.
- `deploy/` - local Docker Compose demo assets.
- `policies/` - YAML policy and optional OPA bundle evidence.
- `tool-manifests/` - trusted YAML tool manifests pinned by `tool-manifests.lock.json`.

## Development Commands

- `make test` - run Python tests.
- `make lint` - run Python lint checks.
- `make typecheck` - run Python and UI type checks.
- `make manifest-lock` - regenerate `tool-manifests.lock.json` after intentional manifest edits.
- `make manifest-lock-check` - verify trusted tool manifests still match the committed lock.
- `make manifest-lock-keygen` - create a local Ed25519 keypair for manifest lock signatures.
- `make manifest-lock-sign` - sign the current `tool-manifests.lock.json`.
- `make manifest-lock-signature-check` - verify the local manifest lock signature.
- `make admin-token-generate` - print a strong local `ITHILDIN_ADMIN_TOKEN=...` line.
- `make policy-test` - run committed offline fixtures against `policies/default.yaml`.
- `make release-check` - run manifest lock verification, policy fixtures, tests, lint, typecheck, docs, and UI build.
- `make release-evidence` - print a secret-free local release evidence snapshot.
- `make release-guardrails` - validate public-preview warning labels and deployment guardrails.
- `make audit-keygen` - create a local Ed25519 keypair for signed audit exports.
- `make audit-diagnostics` - explain local audit verification state without mutating evidence.
- `make audit-export-verify FILE=...` - verify a downloaded signed audit export bundle.
- `make docs-site` - build a small local static docs site under ignored `site/`.
- `make ollama-smoke` - detect a host Ollama install and local models, skipping safely if absent.
- `make local-model-demo` - print host-side MCP wiring for an Ollama-backed local model client.
- `make ui-dev` - start the Vite UI app.

## Local Demo

The local Docker Compose demo runs the API and review console with a seeded workspace:

- `make demo-seed` - copy tracked demo files into ignored `workspaces/demo/`.
- `make compose-up` - build and start the local API/UI stack.
- `make compose-smoke` - check API health, authenticated tool listing, and UI reachability.
- `make demo-flow` - run governed reads, redaction, patch proposal, approval, apply, and audit checks.
- `make compose-down` - stop the stack.

Copy `.env.example` to `.env` and set a unique `ITHILDIN_ADMIN_TOKEN` for normal use. Use
`make admin-token-generate` to print a strong token line, then paste it into your local `.env` and
restart the API/UI. The helper never writes secrets to disk. The sample token works only when
`ITHILDIN_ALLOW_DEV_ADMIN_TOKEN=true`, and that mode is visibly warned in `/system/status` and the
review console.
The review console is served at `http://127.0.0.1:5173`.
Docker is only used for the local demo stack; Kubernetes support is deferred.
Tool manifests are hash-pinned by default; run `make manifest-lock` only after intentional
manifest changes.
Named workspaces are trusted local configuration in `workspaces/local.yaml`; read, git, and patch
proposal tools accept optional `workspace_id` and default to `default`.
Signed manifest locks are optional v0.2 local evidence. Run `make manifest-lock-keygen` and
`make manifest-lock-sign`, then set `ITHILDIN_REQUIRE_SIGNED_MANIFEST_LOCK=true` only when you want
startup to fail closed on missing or invalid local signature evidence. See
[docs/codex/signed-manifest-locks.md](docs/codex/signed-manifest-locks.md).
`http.fetch` is disabled until `ITHILDIN_HTTP_ALLOWLIST` names exact destinations such as
`example.com`, `example.com:443`, or `https://example.com`.
Governed tool outputs are redacted before they are returned to agents using an always-on
baseline for common tokens, secrets, passwords, cookies, and private keys; add local patterns
with `ITHILDIN_REDACTION_EXTRA_KEYS` and `ITHILDIN_REDACTION_EXTRA_PATTERNS`.
OPA is optional. When `ITHILDIN_POLICY_ENGINE=opa`, Ithildin verifies
`policies/opa/bundle.lock.json` before startup and reports bundle evidence in policy/system status.
Run `make policy-test` before intentional YAML policy changes; the committed fixture harness is
offline and does not call the API, create approvals, write audit events, or require an OPA sidecar.
Use `uv run python scripts/policy_impact.py --candidate-path path/to/policy.yaml` to compare a
candidate YAML policy against the same fixtures before runtime configuration changes.
SQLite is the runtime storage backend for v0.1. Postgres settings are readiness/status evidence only.
OpenTelemetry is opt-in preview instrumentation and is disabled by default.
Signed audit exports are optional v0.2 local evidence. Run `make audit-keygen`, then use the review
console or `/audit-events/export/signed`; see
[docs/codex/signed-audit-exports.md](docs/codex/signed-audit-exports.md).
Use `make audit-diagnostics` when audit verification fails; diagnostics are read-only and do not
repair or rewrite the local evidence chain.

MCP is launched by an MCP client rather than as a persistent Compose service:

```sh
uv run python -m ithildin_mcp_server
```

See [docs/codex/mcp-client-examples.md](docs/codex/mcp-client-examples.md) for copy-paste stdio
client snippets and local-permission warnings.

For local model demos, run `make local-model-demo`; Ollama remains a host-side client companion,
not an Ithildin-managed service or tool power.

Build local handoff docs with:

```sh
make docs-site
```

The corrected public-preview release evidence is preserved in
[docs/codex/v0.1-release-evidence.md](docs/codex/v0.1-release-evidence.md). Rerun
`make release-check` and `make release-evidence` before tagging.

## Core Invariant

No agent-originated action reaches the endpoint unless:

1. the caller is authenticated;
2. the tool is registered;
3. the input matches schema;
4. the resource is in scope;
5. policy allows it or requires approval;
6. approval is satisfied when required;
7. execution happens inside the declared scope;
8. the full decision and result are logged.

## Start Reading

Begin with [docs/codex/local-preview-release.md](docs/codex/local-preview-release.md), then read
[docs/codex/v0.1-public-preview-release-notes.md](docs/codex/v0.1-public-preview-release-notes.md),
[docs/codex/mcp-client-examples.md](docs/codex/mcp-client-examples.md), and
[docs/codex/signed-audit-exports.md](docs/codex/signed-audit-exports.md),
[docs/codex/signed-manifest-locks.md](docs/codex/signed-manifest-locks.md),
[docs/codex/threat-model-and-non-goals.md](docs/codex/threat-model-and-non-goals.md),
[docs/obsidian/00-index.md](docs/obsidian/00-index.md) and
[docs/codex/project-brief.md](docs/codex/project-brief.md) when starting implementation work.

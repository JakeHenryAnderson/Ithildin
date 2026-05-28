---
title: Roadmap
tags: [ithildin, roadmap]
---

# Roadmap

## First 30 Days: Prove Governed Execution

Deliver:

- monorepo scaffold;
- Docker Compose local deployment;
- FastAPI backend;
- MCP adapter;
- tool manifest schema;
- deny-default policy evaluator;
- audit event schema;
- SQLite persistence;
- `fs.list`, `fs.read`, `fs.search`;
- `git.status`, `git.diff`;
- minimal approval API;
- basic React approval UI;
- unit tests for path validation and policy decisions;
- threat model document.

Status: complete for local preview.

Success criteria:

- an MCP-capable agent can list/read approved workspace files;
- a write attempt is denied or queued for approval;
- every action is logged;
- the system fails closed when policy is unavailable.

## Days 31-60: Prove Approval and Audit Quality

Deliver:

- `fs.propose_patch`;
- `fs.apply_patch` with diff approval;
- hash-chained JSONL audit log;
- audit viewer;
- policy version tracking;
- OPA sidecar prototype;
- HTTP fetch with allowlist and private-IP blocking;
- tool output redaction;
- integration tests through MCP;
- security tests for path traversal and SSRF.

Status: complete for local preview.

Success criteria:

- an agent can propose a code change;
- a human can approve exactly one patch;
- the patch executes only in the allowed workspace;
- audit records reconstruct the full decision path.

## Days 61-90: Make It Release-Worthy

Deliver:

- stable policy evaluator or OPA bundle support;
- signed or hash-pinned tool manifests;
- improved UI;
- Postgres option;
- OpenTelemetry export prototype;
- local model demo using Ollama;
- documentation site;
- example policies;
- end-to-end demo scripts;
- v0.1 OSS release.

Status: complete for v0.1 public-preview candidate. OPA bundle evidence, hash-pinned manifests, improved
review console, local principal registry, role-aware tool visibility, Postgres readiness status,
OpenTelemetry preview hooks, Ollama host-side demo helpers, static docs generation, and
local-preview release checks are implemented. Public boundary hardening, approval evidence binding,
executor edge-case hardening, MCP client examples, and public-preview release notes are also in
place.

Success criteria:

- a developer can install locally, connect an MCP client, run governed workflows, review approvals, and export audit evidence.

## Deferred After v0.1 Local Preview

- v0.2 planning starts from [../codex/v0.2-planning-seed.md](../codex/v0.2-planning-seed.md):
  signed audit exports, signed manifest locks, policy tests, workspace modeling, approval review UX,
  policy diff/impact preview, and local admin-auth hardening.
- Runtime Postgres storage adapters and migrations.
- Production identity integrations such as OIDC, SAML, SCIM, and hosted sessions.
- Hosted observability collectors and production telemetry dashboards.
- Kubernetes deployment and agent-facing Docker/Kubernetes tools.
- Cryptographic signing or notarization for manifests and audit exports.
- Managed model serving or LLM proxy workflows.
- Remote MCP hosting, plugin SDKs, browser automation, shell tools, broad filesystem writes, Docker
  socket access, and Kubernetes agent tools.

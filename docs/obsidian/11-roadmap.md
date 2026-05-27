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

Status: partially complete. OPA bundle evidence, hash-pinned manifests, improved review console,
and local-preview release checks are implemented. Postgres, OpenTelemetry, Ollama packaging,
documentation site, and v0.1 OSS packaging remain future work.

Success criteria:

- a developer can install locally, connect an MCP client, run governed workflows, review approvals, and export audit evidence.

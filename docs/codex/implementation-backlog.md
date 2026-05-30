# Implementation Backlog

## Completed Local Preview Track

| Task | Status | Spec |
| --- | --- | --- |
| 001 - Monorepo scaffold | Done | [tasks/001-monorepo-scaffold.md](tasks/001-monorepo-scaffold.md) |
| 002 - Core schemas | Done | [tasks/002-core-schemas.md](tasks/002-core-schemas.md) |
| 003 - FastAPI base service | Done | [tasks/003-fastapi-base-service.md](tasks/003-fastapi-base-service.md) |
| 004 - Tool registry | Done | [tasks/004-tool-registry.md](tasks/004-tool-registry.md) |
| 005 - Policy evaluator | Done | [tasks/005-policy-evaluator.md](tasks/005-policy-evaluator.md) |
| 006 - Audit writer | Done | [tasks/006-audit-writer.md](tasks/006-audit-writer.md) |
| 007 - Approval workflow | Done | [tasks/007-approval-workflow.md](tasks/007-approval-workflow.md) |
| 008 - MCP adapter | Done | [tasks/008-mcp-adapter.md](tasks/008-mcp-adapter.md) |
| 009 - Filesystem and git read tools | Done | [tasks/009-read-tools.md](tasks/009-read-tools.md) |
| 010 - Patch proposal and apply | Done | [tasks/010-patch-tools.md](tasks/010-patch-tools.md) |
| 011 - Approval-gated patch apply | Done | Sprint checkpoint |
| 012 - Review console | Done | Sprint checkpoint |
| 013 - Audit verification and export | Done | Sprint checkpoint |
| 014 - Policy preview | Done | Sprint checkpoint |
| 015 - Local demo deployment | Done | Sprint checkpoint |
| 016 - Local deployment verification | Done | Sprint checkpoint |
| 017 - Governed HTTP fetch | Done | Sprint checkpoint |
| 018 - Tool output redaction | Done | Sprint checkpoint |
| 019 - MCP integration flow | Done | Sprint checkpoint |
| 020 - Security regression suite | Done | Sprint checkpoint |
| 021 - Policy evidence | Done | Sprint checkpoint |
| 022 - OPA policy prototype | Done | Sprint checkpoint |
| 023 - Manifest lock verification | Done | Sprint checkpoint |
| 024 - OPA bundle verification | Done | Sprint checkpoint |
| 025 - Review console trust status | Done | Sprint checkpoint |
| 026 - Local preview release guide | Done | Sprint checkpoint |
| 027 - Local principal registry | Done | Sprint checkpoint |
| 028 - Role-aware tool visibility | Done | Sprint checkpoint |
| 029 - Ops backbone readiness | Done | Sprint checkpoint |
| 030 - Local model demo | Done | Sprint checkpoint |
| 031 - v0.1 release packaging | Done | Sprint checkpoint |
| 032 - Public boundary hardening | Done | [threat-model-and-non-goals.md](threat-model-and-non-goals.md) |
| 033 - Approval and evidence binding | Done | Sprint checkpoint |
| 034 - Executor security edge cases | Done | Sprint checkpoint |
| 035 - Public v0.1 release candidate polish | Done | [v0.1-public-preview-release-notes.md](v0.1-public-preview-release-notes.md) |
| 044 - Signed audit exports | Done | [signed-audit-exports.md](signed-audit-exports.md) |
| 045 - Signed manifest locks | Done | [signed-manifest-locks.md](signed-manifest-locks.md) |
| 046 - Policy test harness | Done | `policies/tests/default.yaml`, `scripts/policy_test.py` |
| 047 - Named workspace model | Done | `workspaces/local.yaml`, `/workspaces` |
| 048 - Policy impact preview | Done | `/policy/impact-preview`, `scripts/policy_impact.py` |
| 049 - Approval review UX v2 | Done | `/approvals/review`, review console evidence checks |
| 050 - Local admin auth ergonomics | Done | `make admin-token-generate`, `/system/status` token posture |
| 051 - Audit diagnostics | Done | `/audit-events/diagnostics`, `make audit-diagnostics` |
| 052 - MCP Inspector recipes | Done | [mcp-inspector-recipes.md](mcp-inspector-recipes.md) |
| 053 - Redaction evidence UX | Done | `/system/status`, review console audit table |
| 054 - Policy decision evidence | Done | `decision_evidence.py`, `/policy/preview` |
| 055 - Evidence contracts | Done | [evidence-contracts.md](evidence-contracts.md) |
| 056 - Approval drift regressions | Done | `tests/test_governed_tool_calls.py` |
| 057 - Path ambiguity hardening | Done | `tests/test_read_tools.py`, `tests/test_patch_proposals.py` |
| 058 - HTTP proxy regression coverage | Done | `tests/test_http_tools.py` |
| 059 - v0.2 roadmap refresh | Done | [v0.2-planning-seed.md](v0.2-planning-seed.md) |
| 060 - Release packet evidence | Done | `make release-packet`, `scripts/release_packet.py` |
| 061 - v0.2 review packet | Done | [v0.2-review-packet.md](v0.2-review-packet.md) |
| 062 - Review response cleanup | Done | [v0.2-review-response-and-rc-cleanup.md](v0.2-review-response-and-rc-cleanup.md) |
| 063 - v0.2 external review prompt | Done | [v0.2-external-review-prompt.md](v0.2-external-review-prompt.md) |
| 064 - v0.2 review bundle command | Done | `make review-packet-bundle`, `scripts/review_packet_bundle.py` |
| 065 - v0.2 handoff polish | Done | README/release packet handoff sequence |
| 066 - v0.2 label clarity | Done | v0.2 review candidate / v0.1 runtime boundary wording |
| 067 - Release evidence metadata | Done | review-doc hashes and release-check transcript metadata |
| 068 - Signed evidence demo fixtures | Done | `make signed-evidence-demo` |
| 069 - Negative review recipes | Done | [negative-review-recipes.md](negative-review-recipes.md) |
| 070 - Review packet regeneration | Done | refreshed review bundle and consolidated staging |
| 071 - Release evidence hashes | Done | renamed release-check fields and `artifact-hashes.json` |
| 072 - Reviewer reproduction map | Done | [reviewer-reproduction-map.md](reviewer-reproduction-map.md) |
| 073 - Final v0.2 packet regeneration | Done | final bundle and consolidated review staging |
| 074 - Consolidated attachment hashes | Done | `make review-packet-consolidated` |
| 075 - Source review closure matrix | Done | [source-review-closure-matrix.md](source-review-closure-matrix.md) |

## Future Candidate Track

| Area | Status | Notes |
| --- | --- | --- |
| Production identity | Deferred | OIDC, SAML, SCIM, hosted sessions, and multi-tenant stores. |
| Runtime Postgres | Deferred | Real Postgres stores and migrations; current support is readiness-only. |
| Hosted observability | Deferred | Production collectors and dashboards; current OpenTelemetry is opt-in preview. |
| Kubernetes and executor hardening | Deferred | Kubernetes assets and containerized execution remain outside v0.1. |
| External anchoring and hosted supply-chain signing | Deferred | Local audit export and manifest lock signing exist; external trust roots remain future work. |
| Remote MCP hosting | Deferred | Stdio-only local MCP remains the v0.1 boundary. |
| Plugin SDK and marketplace | Deferred | Requires stronger signing, review UX, executor contracts, and stable policy impact tooling. |

## v0.2 Planning Seed

Use [v0.2-review-response-and-rc-cleanup.md](v0.2-review-response-and-rc-cleanup.md) and
[v0.2-review-packet.md](v0.2-review-packet.md) as the external/code review handoff, with
[v0.2-planning-seed.md](v0.2-planning-seed.md) as the completed trust-focused v0.2 roadmap. The
current track has completed trust-evidence,
policy-confidence, workspace/approval UX, local-operations polish, evidence-clarity, and
security-matrix closure items.

## Definition of MVP Done

- Local Docker Compose deployment exists.
- MCP client can list and call governed tools.
- Static tool manifests are validated on startup.
- Policy evaluator is deny-default.
- Committed policy fixtures pass through `make policy-test`.
- Write tools require approval.
- Audit events are stored in SQLite and hash-chained JSONL.
- Path traversal, symlink escape, SSRF, approval replay, and invalid schema cases have tests.
- Documentation explains the threat model and security limitations.
- Principal registry and role-aware tool visibility are enabled for local preview.
- Named workspace registry is enabled for scoped read, git, and patch proposal tools.
- Static docs site generation exists for handoff review.
- Public-preview warning labels, threat model links, MCP examples, and release notes are checked.
- MCP Inspector recipes document governed list/call, approval-required, denial, and audit flows.
- Evidence contracts document stable audit, policy, approval, redaction, and signed-bundle fields.
- Security matrix closure tests cover approval drift, path ambiguity, hardlinks, HTTP proxy
  inheritance, and canonical host behavior.
- v0.2 review packet and `make release-packet` exist for external review handoff.
- `make review-packet-bundle` packages the review docs and secret-free command outputs.
- `make signed-evidence-demo` generates non-production locally signed evidence fixtures for review.
- `make release-check` passes before local-preview handoff.

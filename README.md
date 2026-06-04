# Ithildin

Ithildin is a local-first governed MCP/tool gateway for AI agents.

**Current status:** v0.8 roadmap/product-risk consultation after v0.6/v0.7 focused
source-review lane closure for the v0.1 local-preview runtime boundary; some generated paths retain
historical v0.2 names.

Ithildin is a local-preview mediation layer for AI-agent tool use. It is not a sandbox, EDR/MDM
agent, SIEM, production identity system, hosted MCP platform, compliance audit system, or immutable
evidence store. It assumes the local host, local admin, trusted tool manifests, and local policy
files are part of the trusted computing base. Audit records are tamper-evident local evidence, not
notarized or custody-grade logs. Redaction is best-effort leak reduction, not a guarantee that
secrets cannot be exposed.

In practice, v0.6/v0.7 is external-review closure work over the same narrow v0.1 local-preview
runtime boundary. Earlier v0.2 wording and generated paths refer to the historical trust-evidence
packet lineage, not a broader runtime-power release.

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

The agent does not receive OS access through Ithildin's exposed tools. Ithildin owns validation,
policy, approval, execution, and evidence.

## MVP Target

A security-conscious developer can run Ithildin locally, connect an MCP-capable agent, expose a few
safe file/git/http tools, require approval for writes, and inspect a locally verifiable
tamper-evident audit log.

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
- `make manifest-change-review` - check manifest/lock change coupling before review handoff.
- `make manifest-lock-keygen` - create a local Ed25519 keypair for manifest lock signatures.
- `make manifest-lock-sign` - sign the current `tool-manifests.lock.json`.
- `make manifest-lock-signature-check` - verify the local manifest lock signature.
- `make admin-token-generate` - print a strong local `ITHILDIN_ADMIN_TOKEN=...` line.
- `make determinism-check` - check pytest collection stability and obvious nondeterministic patterns.
- `make evidence-contracts-check` - validate the machine-readable local-preview evidence contract index.
- `make policy-test` - run committed offline fixtures against `policies/default.yaml`.
- `make release-check` - run manifest lock verification, policy fixtures, tests, lint, typecheck, docs, and UI build.
- `make release-evidence` - print a secret-free local release evidence snapshot.
- `make release-evidence-gate` - generate and validate a temporary release evidence snapshot.
- `make release-evidence-validate FILE=...` - validate a saved release evidence JSON snapshot.
- `make release-packet` - print a v0.2 external-review packet snapshot.
- `make v04-review-packet` - print a v0.4 review-candidate packet snapshot.
- `make review-candidate` - run the full local handoff gate, including focused v0.6 dispatch packets, and regenerate review artifacts.
- `make v05-review-candidate` - run the v0.5 handoff gate plus source-review artifact prep.
- `make review-packet-bundle` - build an ignored v0.2 review handoff bundle under `var/review-packets/`.
- `make review-packet-consolidated` - build the 10-attachment-friendly GPT review packet.
- `make review-packet-diff OLD=... NEW=...` - compare two review packet bundles by artifact hash.
- `make review-packet-diff-gate OLD=... NEW=...` - require packet hashes and fail on removed artifacts.
- `make review-packet-source-pointers` - validate source-file pointers used by reviewer packets.
- `make packet-redaction-scan` - scan generated review packet artifacts for obvious secret material.
- `make internal-review-packet` - build v2 local prompts for internal AI/subagent source review.
- `make source-review-transcript-packet` - generate a source-review transcript skeleton under ignored `var/`.
- `make reviewer-artifact-manifest` - generate the v0.5 reviewer artifact inventory.
- `make external-response-template-check` - validate the external review response intake template.
- `make reviewer-findings-check` - validate structured reviewer finding records before matrix updates.
- `make review-findings-summary` - summarize structured findings for v0.4 planning and release gates.
- `make v06-lane-status` - verify the generated v0.6 lane-status board is current.
- `make v06-closure-readiness` - verify v0.6 closure-readiness docs without closing external review.
- `make v06-final-handoff` - verify v0.6 final no-go/handoff docs preserve current blockers.
- `make v07-closure-prep` - verify the v0.7 external-review closure charter, packet sanity review, and row partition.
- `make v07-patch-apply-recheck-prep` - verify patch-apply recheck prep for `EXT-PA-001` through `EXT-PA-004`.
- `make filesystem-source-review-bundle` - build the focused filesystem/platform source/test/evidence handoff requested by `EXT-FS-001`.
- `make http-fetch-source-review-bundle` - build the focused `http.fetch` source/test/evidence handoff for source-level external review.
- `make signed-evidence-source-review-bundle` - build the focused audit/signed-evidence source/test/evidence handoff for source-level external review.
- `make policy-registry-source-review-bundle` - build the focused policy/registry source/test/evidence handoff for source-level external review.
- `make mcp-ingress-source-review-bundle` - build the focused MCP ingress source/test/evidence handoff for source-level external review.
- `make review-console-source-review-bundle` - build the focused review-console/admin source/test/evidence handoff for source-level external review.
- `make release-automation-source-review-bundle` - build the focused release/evidence automation source/test/evidence handoff for source-level external review.
- `make review-run-manifest-check` - validate executed review-run manifests under ignored `var/review-runs/`.
- `make signed-evidence-demo` - generate ignored non-production locally signed evidence fixtures.
- `make signed-evidence-demo-verify` - verify the non-production signed-evidence demo artifacts.
- `make negative-review-transcripts` - generate ignored observed denial transcripts for review.
- `make release-guardrails` - validate public-preview warning labels and deployment guardrails.
- `make capability-expansion-gate` - report whether future powerful-tool planning is allowed.
- `make capability-decision-report` - summarize current capability go/no-go evidence without approving powers.
- `make tool-surface-invariant-gate` - verify the governed tool manifest surface has not drifted.
- `make no-new-powers-guardrail` - fail if review work adds deferred tool-power classes.
- `make evidence-confusion-gate` - verify locally signed evidence wording does not overclaim trust.
- `make external-review-closure-gate` - verify source-review closure is not overstated.
- `make external-findings-intake-dry-run` - exercise EXT finding intake without mutating findings.
- `make closure-matrix-evidence-sync` - verify completed v0.5 tasks are represented in the matrix.
- `make accepted-risk-register-check` - validate accepted local-preview risks stay scoped and explicitly dispositioned.
- `make v08-public-preview-decision` - validate the v0.8 local-preview sharing and public/security-product no-go decision.
- `make v08-capability-design-gate` - validate design-only capability planning while implementation remains blocked.
- `make v08-final-decision-packet` - validate the final v0.8 product-risk decision packet.
- `make v09-design-only-gate` - validate that v0.9 capability planning remains design-only.
- `make git-commit-metadata-proposal-check` - validate the first design-only capability proposal.
- `make git-commit-metadata-implementation-plan-check` - validate the implementation-planning packet while implementation remains blocked.
- `make v09-design-review-packet` - generate the design-only review packet for `git.show.commit_metadata`.
- `make audit-keygen` - create a local Ed25519 keypair for signed audit exports.
- `make audit-diagnostics` - explain local audit verification and export lifecycle state without mutating evidence.
- `make audit-export-verify FILE=...` - verify a downloaded signed audit export bundle.
- `make filesystem-contract-check` - report local filesystem capability evidence for the executor contract.
- `make docs-site` - build a small local static docs site under ignored `site/`.
- `make ui-test` - run the review console Vitest/React Testing Library interaction harness.
- `make ollama-smoke` - detect a host Ollama install and local models, skipping safely if absent.
- `make local-model-demo` - print host-side MCP wiring for an Ollama-backed local model client.
- `make mcp-inspector-recipes` - validate and print local MCP Inspector recipe prerequisites.
- `make ui-dev` - start the Vite UI app.

## Local Demo

The local Docker Compose demo runs the API and review console with a seeded workspace:

- `make demo-seed` - copy tracked demo files into ignored `workspaces/demo/`.
- `make compose-up` - build and start the local API/UI stack.
- `make compose-smoke` - check API health, authenticated tool listing, and UI reachability.
- `make demo-flow` - run governed reads, redaction, patch proposal, approval, apply, and audit checks.
- `make demo-scenario-pack` - validate the reviewer-facing demo scenario map.
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
Locally signed manifest locks are optional v0.2 local evidence. Run `make manifest-lock-keygen` and
`make manifest-lock-sign`, then set `ITHILDIN_REQUIRE_SIGNED_MANIFEST_LOCK=true` only when you want
startup to fail closed on missing or invalid local signature evidence. See
[docs/codex/signed-manifest-locks.md](docs/codex/signed-manifest-locks.md).
`http.fetch` is disabled until `ITHILDIN_HTTP_ALLOWLIST` names exact destinations such as
`example.com` (HTTPS default), `example.com:443`, `example.com:80`, or
`https://example.com`. Use a scheme-qualified entry for non-default ports.
Its v2 canonicalization, redirect, DNS/IP, proxy, and response-bound behavior is documented in
[docs/codex/http-executor-contract.md](docs/codex/http-executor-contract.md).
Governed tool outputs are redacted before they are returned to agents using an always-on
baseline for common tokens, secrets, passwords, cookies, and private keys; add local patterns
with `ITHILDIN_REDACTION_EXTRA_KEYS` and `ITHILDIN_REDACTION_EXTRA_PATTERNS`.
OPA is optional. When `ITHILDIN_POLICY_ENGINE=opa`, Ithildin verifies
`policies/opa/bundle.lock.json` before startup and reports bundle evidence in policy/system status.
Run `make policy-test` before intentional YAML policy changes; the committed fixture harness is
offline and does not call the API, create approvals, write audit events, or require an OPA sidecar.
Run `make policy-parity` to compare policy preview decisions with governed runtime
`policy.evaluated` audit evidence using the committed parity fixtures.
Use `uv run python scripts/policy_impact.py --candidate-path path/to/policy.yaml` to compare a
candidate YAML policy against the same fixtures before runtime configuration changes.
OPA remains optional verified sidecar evidence, not the canonical parity engine; see
[docs/codex/opa-parity-decision.md](docs/codex/opa-parity-decision.md).
SQLite is the runtime storage backend for v0.1. Postgres settings are readiness/status evidence only.
OpenTelemetry is opt-in preview instrumentation and is disabled by default.
Locally signed audit exports are optional v0.2 local evidence. Run `make audit-keygen`, then use the
review console or `/audit-events/export/signed`; see
[docs/codex/signed-audit-exports.md](docs/codex/signed-audit-exports.md).
Use `make audit-diagnostics` when audit verification fails; diagnostics are read-only and do not
repair or rewrite the local evidence chain.
Patch apply recovery diagnostics are also read-only: `/patch-apply-diagnostics` reports incomplete
stored patch apply attempts and approvals stuck in execution, but does not repair, roll back, or
rewrite workspace files.
Filesystem and patch executor platform assumptions are documented in
[docs/codex/filesystem-executor-contract.md](docs/codex/filesystem-executor-contract.md). Run
`make filesystem-contract-check` to record local OS and filesystem capability evidence before
relying on local-preview workspace/race claims; `/system/status`, release evidence, and the review
console also surface unsupported or degraded filesystem profiles.
Patch apply approval and recovery states are documented in
[docs/codex/patch-apply-state-machine.md](docs/codex/patch-apply-state-machine.md).
Evidence fields for audit events, policy decisions, approvals, redaction summaries, and signed
bundles are summarized in [docs/codex/evidence-contracts.md](docs/codex/evidence-contracts.md).
Redaction remains best-effort leak reduction; its runtime and review-packet limits are documented in
[docs/codex/redaction-evidence-boundary.md](docs/codex/redaction-evidence-boundary.md).

MCP is launched by an MCP client rather than as a persistent Compose service:

```sh
uv run python -m ithildin_mcp_server
```

See [docs/codex/mcp-client-examples.md](docs/codex/mcp-client-examples.md) for copy-paste stdio
client snippets and local-permission warnings. Use
[docs/codex/mcp-inspector-recipes.md](docs/codex/mcp-inspector-recipes.md) and
`make mcp-inspector-recipes` for reproducible local `tools/list`, `tools/call`, approval-required,
denial, and audit verification flows.

For local model demos, run `make local-model-demo`; Ollama remains a host-side client companion,
not an Ithildin-managed service or tool power.

Build local handoff docs with:

```sh
make docs-site
```

The corrected public-preview release evidence is preserved in
[docs/codex/v0.1-release-evidence.md](docs/codex/v0.1-release-evidence.md). Rerun
`make review-candidate` before tagging or external review handoff. It runs the release gate,
filesystem contract check, signed evidence demo, negative transcripts, focused v0.6 dispatch
packets, review bundle, consolidated packet, packet redaction scan, and docs site. Use
[docs/codex/reviewer-reproduction-map.md](docs/codex/reviewer-reproduction-map.md) to reproduce
the full evidence sequence and locate generated hashes/transcripts.
The release-evidence schema and validation command are documented in
[docs/codex/release-evidence-schema.md](docs/codex/release-evidence-schema.md).
Packet-to-packet handoff comparisons are documented in
[docs/codex/review-packet-diff.md](docs/codex/review-packet-diff.md).
The current external review handoff starts with
[docs/codex/v0.3-review-packet.md](docs/codex/v0.3-review-packet.md) and
[docs/codex/v0.3-external-review-prompt.md](docs/codex/v0.3-external-review-prompt.md).
The v0.4 review handoff starts with
[docs/codex/v0.4-review-packet.md](docs/codex/v0.4-review-packet.md),
[docs/codex/v0.4-external-review-prompt.md](docs/codex/v0.4-external-review-prompt.md), and
[docs/codex/v0.4-capability-decision-seed.md](docs/codex/v0.4-capability-decision-seed.md).
External review findings should be processed through
[docs/codex/external-review-intake-and-closure.md](docs/codex/external-review-intake-and-closure.md)
and [docs/codex/external-review-intake-v2.md](docs/codex/external-review-intake-v2.md).
The current boundary decision is recorded in
[docs/codex/v0.3-boundary-decision.md](docs/codex/v0.3-boundary-decision.md).
The v0.4 work charter is recorded in
[docs/codex/v0.4-boundary-charter.md](docs/codex/v0.4-boundary-charter.md); it keeps the next wave
focused on review closure, evidence maturity, diagnostics, and local-preview hardening rather than
new governed tool powers.
The review-document map is in
[docs/codex/review-docs-index.md](docs/codex/review-docs-index.md).
The v0.4 threat-model refresh is in
[docs/codex/v0.4-threat-model-refresh.md](docs/codex/v0.4-threat-model-refresh.md).
The v0.4 milestone roadmap is recorded in
[docs/codex/v0.4-milestone-manifest.md](docs/codex/v0.4-milestone-manifest.md). Tasks 113-151 are
complete and should be externally reviewed before implementation drift or capability expansion.
The v0.5 source-review and capability-decision roadmap is recorded in
[docs/codex/v0.5-roadmap-from-v0.4-review.md](docs/codex/v0.5-roadmap-from-v0.4-review.md) and
[docs/codex/v0.5-milestone-manifest.md](docs/codex/v0.5-milestone-manifest.md). Tasks 152-180 are
complete and do not add new governed tool powers.
The v0.5 threat-model delta is in
[docs/codex/v0.5-threat-model-delta.md](docs/codex/v0.5-threat-model-delta.md).
The v0.5 handoff packet is in
[docs/codex/v0.5-handoff-packet.md](docs/codex/v0.5-handoff-packet.md).
The v0.6 preflight transition note is in
[docs/codex/v0.6-preflight-transition.md](docs/codex/v0.6-preflight-transition.md).
The v0.6 external-review execution charter is in
[docs/codex/v0.6-boundary-charter.md](docs/codex/v0.6-boundary-charter.md), with the milestone
manifest in [docs/codex/v0.6-milestone-manifest.md](docs/codex/v0.6-milestone-manifest.md).
The v0.6 external reviewer assignment matrix is in
[docs/codex/v0.6-external-review-assignment-matrix.md](docs/codex/v0.6-external-review-assignment-matrix.md).
Focused v0.6 review dispatch packets are generated with `make v06-review-dispatch-packets` and
documented in
[docs/codex/v0.6-external-review-dispatch-packets.md](docs/codex/v0.6-external-review-dispatch-packets.md).
The first focused source-review execution packet, for patch apply, is generated with
`make v06-patch-apply-review-packet` and documented in
[docs/codex/v0.6-patch-apply-external-review-execution.md](docs/codex/v0.6-patch-apply-external-review-execution.md).
The generated v0.6 lane-status board is in
[docs/codex/v0.6-lane-status-board.md](docs/codex/v0.6-lane-status-board.md) and is verified with
`make v06-lane-status`.
The v0.6 closure-readiness bundle starts at
[docs/codex/v0.6-post-review-packet.md](docs/codex/v0.6-post-review-packet.md) and is verified
with `make v06-closure-readiness`; it preserves external-pending status and does not approve new
tool powers.
The final v0.6 handoff/no-go packet is
[docs/codex/v0.6-final-go-no-go-packet.md](docs/codex/v0.6-final-go-no-go-packet.md) and is
verified with `make v06-final-handoff`.
The v0.7 external-review closure prep starts with
[docs/codex/v0.7-external-review-closure-charter.md](docs/codex/v0.7-external-review-closure-charter.md),
[docs/codex/v0.6-final-packet-sanity-review.md](docs/codex/v0.6-final-packet-sanity-review.md),
and [docs/codex/v0.7-external-review-row-partition.md](docs/codex/v0.7-external-review-row-partition.md);
it is verified with `make v07-closure-prep` and does not approve public preview or new tool powers.
The first v0.7 lane recheck is
[docs/codex/v0.7-patch-apply-recheck-request.md](docs/codex/v0.7-patch-apply-recheck-request.md)
and is verified with `make v07-patch-apply-recheck-prep`; generated packet artifacts still come
from `make v06-patch-apply-review-packet`.
The patch-apply recheck outcome is recorded in
[docs/codex/v0.7-patch-apply-recheck-outcome.md](docs/codex/v0.7-patch-apply-recheck-outcome.md);
it closes only the local-preview patch-apply lane and does not approve public preview or new tool
powers.
The filesystem/platform lane source-review handoff is recorded in
[docs/codex/v0.7-filesystem-platform-source-review.md](docs/codex/v0.7-filesystem-platform-source-review.md).
Generate the focused source/test/evidence bundle requested by `EXT-FS-001` with
`make filesystem-source-review-bundle`; the ignored output is
`var/review-packets/v0.7/filesystem-source-review/`.
Generate the focused source/test/evidence bundle for the `http.fetch` lane with
`make http-fetch-source-review-bundle`; the ignored output is
`var/review-packets/v0.7/http-fetch-source-review/`.
Generate the focused source/test/evidence bundle for the signed evidence/audit lane with
`make signed-evidence-source-review-bundle`; the ignored output is
`var/review-packets/v0.7/signed-evidence-source-review/`.
Generate the focused source/test/evidence bundle for the policy/registry lane with
`make policy-registry-source-review-bundle`; the ignored output is
`var/review-packets/v0.7/policy-registry-source-review/`.
Generate the focused source/test/evidence bundle for the MCP ingress lane with
`make mcp-ingress-source-review-bundle`; the ignored output is
`var/review-packets/v0.7/mcp-ingress-source-review/`.
Generate the focused source/test/evidence bundle for the review-console/admin lane with
`make review-console-source-review-bundle`; the ignored output is
`var/review-packets/v0.7/review-console-source-review/`.
Generate the focused source/test/evidence bundle for the release/evidence automation lane with
`make release-automation-source-review-bundle`; the ignored output is
`var/review-packets/v0.7/release-automation-source-review/`.
All eight focused v0.7 source-review lanes are now closed for the v0.1 local-preview runtime
boundary only. The next strategic handoff prompt for v0.8 roadmap/product-risk consultation is in
[docs/codex/v0.8-roadmap-prompt.md](docs/codex/v0.8-roadmap-prompt.md). This does not approve
public/security-product positioning or new governed tool powers.
The current v0.8 truth table is recorded in
[docs/codex/v0.8-status-source-of-truth.md](docs/codex/v0.8-status-source-of-truth.md), and can be
checked with `make v08-status-reconciliation`.
The v0.8 accepted-risk disposition is recorded in
[docs/codex/v0.8-accepted-risk-disposition.md](docs/codex/v0.8-accepted-risk-disposition.md);
`make accepted-risk-register-check` now reports closed local-preview and accepted-deferred risk
counts separately.
The v0.8 public-preview claims decision is recorded in
[docs/codex/v0.8-public-preview-risk-review.md](docs/codex/v0.8-public-preview-risk-review.md):
continued local-preview development is `go`, limited technical-preview sharing is
`conditional_go`, and public/security-product positioning remains `no_go`.
The v0.8 capability-design decision is recorded in
[docs/codex/v0.8-capability-design-decision.md](docs/codex/v0.8-capability-design-decision.md):
design-only exploration is `conditional_go`, while capability implementation and new governed tool
powers remain `no_go`.
The final v0.8 decision packet is recorded in
[docs/codex/v0.8-final-decision-packet.md](docs/codex/v0.8-final-decision-packet.md) and checked
with `make v08-final-decision-packet`.
The v0.9 design-only boundary charter is recorded in
[docs/codex/v0.9-design-only-boundary-charter.md](docs/codex/v0.9-design-only-boundary-charter.md)
and checked with `make v09-design-only-gate`; it allows capability proposals only and keeps
implementation blocked.
The first design-only capability proposal is
[docs/codex/capability-proposals/git-show-commit-metadata.md](docs/codex/capability-proposals/git-show-commit-metadata.md)
and is checked with `make git-commit-metadata-proposal-check`.
The implementation-planning packet is
[docs/codex/capability-implementation-plans/git-show-commit-metadata.md](docs/codex/capability-implementation-plans/git-show-commit-metadata.md)
and is checked with `make git-commit-metadata-implementation-plan-check`; it prepares a later
implementation decision without adding manifests, executors, policy rules, MCP exposure, or runtime
behavior.
The focused design-review handoff for that proposal is generated with
`make v09-design-review-packet`; it asks GPT 5.5 Pro / human review whether implementation
planning may be considered later, without authorizing manifests, executors, policy rules, MCP
exposure, or runtime behavior.
External responses can be normalized with `make external-response-normalize FILE=...`; the workflow is
documented in
[docs/codex/v0.6-external-response-normalization.md](docs/codex/v0.6-external-response-normalization.md).
The v0.6 internal proxy-review remediation handoff is summarized in
[docs/codex/v0.6-internal-proxy-review-operating-model.md](docs/codex/v0.6-internal-proxy-review-operating-model.md)
and
[docs/codex/v0.6-closure-handoff.md](docs/codex/v0.6-closure-handoff.md), with a ready-to-paste
GPT 5.5 Pro prompt in
[docs/codex/v0.6-gpt-55-pro-handoff-prompt.md](docs/codex/v0.6-gpt-55-pro-handoff-prompt.md).
The current source-review workflow is in
[docs/codex/source-review-runbook-v2.md](docs/codex/source-review-runbook-v2.md).
The source-file inspection packet for reviewers is in
[docs/codex/source-file-inspection-packet.md](docs/codex/source-file-inspection-packet.md).
Patch apply source-review guidance is in
[docs/codex/patch-apply-source-review-checklist.md](docs/codex/patch-apply-source-review-checklist.md).
Filesystem source-review guidance is in
[docs/codex/filesystem-source-review-checklist.md](docs/codex/filesystem-source-review-checklist.md).
HTTP fetch source-review guidance is in
[docs/codex/http-fetch-source-review-checklist.md](docs/codex/http-fetch-source-review-checklist.md).
Signed evidence source-review guidance is in
[docs/codex/signed-evidence-source-review-checklist.md](docs/codex/signed-evidence-source-review-checklist.md).
Policy parity source-review guidance is in
[docs/codex/policy-parity-source-review-checklist.md](docs/codex/policy-parity-source-review-checklist.md).
MCP ingress source-review guidance is in
[docs/codex/mcp-ingress-source-review-checklist.md](docs/codex/mcp-ingress-source-review-checklist.md).
Review console source-review guidance is in
[docs/codex/review-console-source-review-checklist.md](docs/codex/review-console-source-review-checklist.md).
The hardened v0.4 process overlay is recorded in
[docs/codex/v0.4-gating-overlay.md](docs/codex/v0.4-gating-overlay.md). It front-loads release
evidence/schema validation, packet diffing, guardrails, packet redaction scanning, test
determinism, and explicit capability-expansion gates before deeper v0.4 hardening work.
Executed review-run manifests are documented in
[docs/codex/review-run-manifest-schema.md](docs/codex/review-run-manifest-schema.md) and validated
with `make review-run-manifest-check`.
Structured finding summaries are generated by `make review-findings-summary` and recorded in
[docs/codex/v0.3-review-findings-summary.md](docs/codex/v0.3-review-findings-summary.md).
The source-review closure matrix now includes a v3 controlling table for v0.4 closure states; see
[docs/codex/source-review-closure-matrix.md](docs/codex/source-review-closure-matrix.md).
The executor contract set for external/source review is indexed in
[docs/codex/executor-contract-set.md](docs/codex/executor-contract-set.md).
Manifest and manifest-lock fail-closed validation coverage is summarized in
[docs/codex/manifest-validation-suite.md](docs/codex/manifest-validation-suite.md).
Principal/workspace registry fail-closed coverage is summarized in
[docs/codex/registry-fail-closed-suite.md](docs/codex/registry-fail-closed-suite.md).
Audit integrity adversarial coverage is summarized in
[docs/codex/audit-integrity-adversarial-suite.md](docs/codex/audit-integrity-adversarial-suite.md).
Release guardrail expansion is summarized in
[docs/codex/release-guardrail-expansion.md](docs/codex/release-guardrail-expansion.md).
The v0.3-prep assurance roadmap is recorded in
[docs/codex/v0.3-milestone-manifest.md](docs/codex/v0.3-milestone-manifest.md). It keeps Tasks
085-112 scoped to review automation, adversarial assurance, and external handoff preparation rather
than new governed tool powers.

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

Begin with [docs/codex/v0.2-review-response-and-rc-cleanup.md](docs/codex/v0.2-review-response-and-rc-cleanup.md)
and [docs/codex/v0.2-review-packet.md](docs/codex/v0.2-review-packet.md) for external/code review
handoff, or [docs/codex/local-preview-release.md](docs/codex/local-preview-release.md) for local
operator setup. Then read
[docs/codex/v0.2-external-review-prompt.md](docs/codex/v0.2-external-review-prompt.md),
[docs/codex/v0.3-milestone-manifest.md](docs/codex/v0.3-milestone-manifest.md),
[docs/codex/v0.4-boundary-charter.md](docs/codex/v0.4-boundary-charter.md),
[docs/codex/reviewer-reproduction-map.md](docs/codex/reviewer-reproduction-map.md),
[docs/codex/source-review-closure-matrix.md](docs/codex/source-review-closure-matrix.md),
[docs/codex/internal-source-review-pass-1.md](docs/codex/internal-source-review-pass-1.md),
[docs/codex/internal-ai-review-workflow.md](docs/codex/internal-ai-review-workflow.md),
[docs/codex/autonomous-sprint-guardrails.md](docs/codex/autonomous-sprint-guardrails.md),
[docs/codex/reviewer-finding-template.md](docs/codex/reviewer-finding-template.md),
[docs/codex/reviewer-finding-intake.md](docs/codex/reviewer-finding-intake.md),
[docs/codex/v0.1-public-preview-release-notes.md](docs/codex/v0.1-public-preview-release-notes.md),
[docs/codex/mcp-client-examples.md](docs/codex/mcp-client-examples.md), and
[docs/codex/mcp-inspector-recipes.md](docs/codex/mcp-inspector-recipes.md),
[docs/codex/evidence-contracts.md](docs/codex/evidence-contracts.md),
[docs/codex/adversarial-corpus-framework.md](docs/codex/adversarial-corpus-framework.md),
[docs/codex/resource-limit-sanity.md](docs/codex/resource-limit-sanity.md),
[docs/codex/ci-platform-plan.md](docs/codex/ci-platform-plan.md),
[docs/codex/policy-parity-harness.md](docs/codex/policy-parity-harness.md),
[docs/codex/opa-parity-decision.md](docs/codex/opa-parity-decision.md),
[docs/codex/mcp-ingress-bypass-audit.md](docs/codex/mcp-ingress-bypass-audit.md),
[docs/codex/local-auth-boundary.md](docs/codex/local-auth-boundary.md),
[docs/codex/review-console-assurance.md](docs/codex/review-console-assurance.md),
[docs/codex/patch-apply-state-machine.md](docs/codex/patch-apply-state-machine.md),
[docs/codex/http-executor-contract.md](docs/codex/http-executor-contract.md),
[docs/codex/filesystem-executor-contract.md](docs/codex/filesystem-executor-contract.md),
[docs/codex/signed-audit-exports.md](docs/codex/signed-audit-exports.md),
[docs/codex/signed-manifest-locks.md](docs/codex/signed-manifest-locks.md),
[docs/codex/threat-model-and-non-goals.md](docs/codex/threat-model-and-non-goals.md),
[docs/obsidian/00-index.md](docs/obsidian/00-index.md) and
[docs/codex/project-brief.md](docs/codex/project-brief.md) when starting implementation work.

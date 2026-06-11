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

## Strategic Direction

The next product direction is agent-run observability around operator-managed sandboxes and
workspaces: first-class run/session evidence, a live timeline dashboard, sandbox boundary contracts,
SIEM-shaped export design, data classification, and policy/control mapping. This is documented in
[docs/codex/agent-run-observability-and-sandbox-roadmap.md](docs/codex/agent-run-observability-and-sandbox-roadmap.md).
It is a roadmap, not a current claim of sandboxing, SIEM-grade custody, production compliance,
hosted control-plane behavior, or broader tool powers.
The first implemented slice is the read-only Agent Run model in
[docs/codex/agent-run-model-contract.md](docs/codex/agent-run-model-contract.md): governed tool
calls can be correlated with local run records, `/runs` and `/runs/{run_id}` expose admin-only
read-only timelines, `/runs` supports bounded read-only filters/summaries, and the review console
shows a compact Agent Run operations dashboard. This is observability only, not sandbox/process
control.
The secret-free timeline evidence contract is
[docs/codex/agent-run-evidence-contract.md](docs/codex/agent-run-evidence-contract.md) and is
checked with `make agent-run-evidence-contract-check`.
The future Agent Run evidence export bundle shape is
[docs/codex/agent-run-evidence-export-design.md](docs/codex/agent-run-evidence-export-design.md)
and is checked with `make agent-run-evidence-export-check`; it is design-only and does not add an
export endpoint, SIEM adapter, sandbox control, or runtime behavior.
The future Agent Run evidence export implementation plan is
[docs/codex/agent-run-evidence-export-implementation-plan.md](docs/codex/agent-run-evidence-export-implementation-plan.md)
and is checked with `make agent-run-evidence-export-plan-check`; it prepares endpoint/schema/tests
only and does not approve implementation.
The bounded Agent Run evidence export endpoint is
[docs/codex/agent-run-evidence-export-implementation.md](docs/codex/agent-run-evidence-export-implementation.md)
and is checked with `make agent-run-evidence-export-implementation-gate`; it is admin-only,
read-only, secret-free, and does not add SIEM adapters or new tool powers.
The Agent Run timeline readiness gate is
[docs/codex/agent-run-timeline-readiness-gate.md](docs/codex/agent-run-timeline-readiness-gate.md)
and is checked with `make agent-run-timeline-readiness`.
The Agent Run evidence readiness gate is
[docs/codex/agent-run-evidence-readiness-gate.md](docs/codex/agent-run-evidence-readiness-gate.md)
and is checked with `make agent-run-evidence-readiness`; it keeps run evidence/export design tied
to timeline, incident reconstruction, dashboard evidence, and no-new-powers checks.
The Agent Run operations readiness gate is
[docs/codex/agent-run-operations-readiness-gate.md](docs/codex/agent-run-operations-readiness-gate.md)
and is checked with `make agent-run-operations-readiness`; it validates the read-only run filter,
summary, timeline, and export-dashboard surface without run controls or SIEM adapters.
The operator action states proposal is
[docs/codex/operator-action-states-design.md](docs/codex/operator-action-states-design.md) and is
checked with `make operator-action-states-check`; it is design-only and does not add pause, abort,
kill, repair, replay, or disable behavior.
The dashboard evidence review checklist is
[docs/codex/dashboard-evidence-review-checklist.md](docs/codex/dashboard-evidence-review-checklist.md)
and is checked with `make dashboard-evidence-checklist-check`.
The operator-managed sandbox/workspace boundary contract is
[docs/codex/sandbox-workspace-boundary-contract.md](docs/codex/sandbox-workspace-boundary-contract.md);
it is design/evidence-only and does not add sandbox orchestration or OS isolation claims.
The operator-managed sandbox demo guide is
[docs/codex/operator-managed-sandbox-demo-guide.md](docs/codex/operator-managed-sandbox-demo-guide.md);
it shows how to demonstrate Ithildin around an operator-created workspace/sandbox label without
Docker socket access, shell tools, lifecycle control, or sandbox claims.
The future JSONL/SIEM-shaped evidence design is
[docs/codex/siem-shaped-evidence-design.md](docs/codex/siem-shaped-evidence-design.md) and is
checked with `make siem-evidence-design-check`; it does not add SIEM adapters or hosted telemetry.
The trusted local data classification proposal is
[docs/codex/data-classification-design.md](docs/codex/data-classification-design.md) and is checked
with `make data-classification-design-check`; it defines future policy inputs and UI warnings only,
with no automatic discovery or runtime policy behavior.
The policy/control mapping design is
[docs/codex/control-mapping-design.md](docs/codex/control-mapping-design.md) and is checked with
`make control-mapping-design-check`; it supports control-objective mapping only and does not make
HIPAA, GLBA, SOX, GDPR, or other compliance claims.
The incident reconstruction guide is
[docs/codex/incident-reconstruction-guide.md](docs/codex/incident-reconstruction-guide.md) and is
checked with `make incident-reconstruction-check`; it explains how to reconstruct mediated actions
only, not activity outside Ithildin.
The combined observability readiness gate is
[docs/codex/observability-readiness-gate.md](docs/codex/observability-readiness-gate.md) and is
checked with `make observability-readiness`.
The observability/control mapping umbrella gate is
[docs/codex/control-mapping-readiness-gate.md](docs/codex/control-mapping-readiness-gate.md) and is
checked with `make control-mapping-readiness`.

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
- `make review-candidate` - run the full local handoff gate, including focused v0.6 dispatch packets, operator-managed sandbox and live-demo packets, and regenerated review artifacts.
- `make v05-review-candidate` - run the v0.5 handoff gate plus source-review artifact prep.
- `make review-packet-bundle` - build an ignored v0.2 review handoff bundle under `var/review-packets/`.
- `make review-packet-consolidated` - build the 10-attachment-friendly GPT review packet.
- `make agent-run-timeline-packet` - generate an ignored Agent Run timeline source/evidence review packet.
- `make review-packet-diff OLD=... NEW=...` - compare two review packet bundles by artifact hash.
- `make review-packet-diff-gate OLD=... NEW=...` - require packet hashes and fail on removed artifacts.
- `make review-packet-source-pointers` - validate source-file pointers used by reviewer packets.
- `make packet-redaction-scan` - scan generated review packet artifacts for obvious secret material.
- `make local-prompt-triage` - classify a local task prompt with deterministic host-side heuristics; no model, network, proxy, or tool-power changes.
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
- `make agent-run-evidence-contract-check` - validate the Agent Run evidence contract and review-doc/docs-site wiring.
- `make agent-run-evidence-export-check` - validate the design-only Agent Run evidence export bundle shape.
- `make agent-run-evidence-export-plan-check` - validate the implementation-planning packet for the future admin-only Agent Run evidence export endpoint.
- `make agent-run-evidence-export-implementation-gate` - validate the bounded admin-only Agent Run evidence export endpoint.
- `make agent-run-evidence-packet` - generate an ignored focused Agent Run evidence export design review packet.
- `make agent-run-correlation-smoke` - generate a secret-free Agent Run correlation smoke transcript.
- `make agent-run-correlation-packet` - generate an ignored Agent Run correlation review packet.
- `make agent-run-evidence-readiness` - validate Agent Run evidence/export design, timeline, incident reconstruction, dashboard evidence, and no-new-powers wiring.
- `make agent-run-operations-readiness` - validate the read-only Agent Run operations dashboard, filters, summaries, and no-new-powers wiring.
- `make agent-run-timeline-readiness` - validate Agent Run store/API/UI timeline readiness without run-control behavior.
- `make workbench-readiness` - validate the local operator workbench surface, docs, evidence packet wiring, and no-new-powers posture.
- `make workbench-evidence-packet` - generate an ignored operator workbench evidence packet tying together Agent Runs, approvals, audit, live demo, sandbox/workspace posture, and handoff artifacts.
- `make demo-readiness-summary` - generate a secret-free operator demo readiness summary with ready, missing, optional/manual, deferred, and next-command sections.
- `make demo-operator-walkthrough` - generate the front-door operator demo walkthrough with expected screens, evidence files, next human steps, and reset guidance.
- `make operator-demo-guide` - generate a secret-free preflight-to-cleanup operator demo guide for the local workbench path.
- `make demo-state-report` - generate a secret-free current-state report for seed status, localhost reachability, artifact paths, warnings, and next demo commands.
- `make guided-demo` - run the non-service-starting guided local demo evidence path and write `GUIDED_DEMO_TRANSCRIPT.md`.
- `make guided-demo-readiness` - validate guided-demo command, docs, UI, packet, and no-new-powers wiring.
- `make demo-reset-guide` - write read-only reset/recovery guidance for repeating or diagnosing the local demo.
- `make demo-flow-readiness` - validate demo-flow result, reset guide, UI demo labels, packet, and no-new-powers wiring.
- `make demo-flow-result-check` - validate `DEMO_FLOW_RESULT.md` if an optional mediated demo run has produced it.
- `make demo-observed-summary` - summarize observed demo IDs, audit heads, and run evidence export pointers without file contents or diffs.
- `make demo-evidence-packet` - generate a focused demo evidence closure packet under `var/review-packets/v3/demo-evidence/`.
- `make demo-evidence-readiness` - validate demo evidence packet, result-check, docs, review-candidate, and no-new-powers wiring.
- `make demo-workbench-smoke` - generate a deterministic, secret-free operator workbench smoke transcript with required and optional/manual demo steps.
- `make demo-workbench` - run the evidence-only workbench demo wrapper without starting services or adding run/sandbox controls.
- `make operator-action-states-check` - validate future operator action state vocabulary without runtime controls.
- `make dashboard-evidence-checklist-check` - validate the operator-facing evidence dashboard review checklist.
- `make siem-evidence-design-check` - validate the future SIEM-shaped evidence design without adding adapters.
- `make data-classification-design-check` - validate the trusted local data classification proposal without adding runtime behavior.
- `make control-mapping-design-check` - validate control mapping support boundaries without compliance claims.
- `make incident-reconstruction-check` - validate the mediated-action incident reconstruction guide.
- `make observability-control-packet` - generate an ignored observability/control design-review packet with artifact hashes.
- `make observability-readiness` - validate Agent Run, sandbox/workspace, SIEM-shaped evidence, next-capability, and no-new-powers readiness.
- `make control-mapping-readiness` - validate observability, classification, control mapping, incident reconstruction, and no-new-powers readiness.
- `make operator-sandbox-demo-readiness` - validate the operator-managed sandbox/workbench demo guide without adding sandbox lifecycle control.
- `make operator-sandbox-demo-smoke` - generate a secret-free operator-managed sandbox/workbench demo smoke transcript.
- `make operator-sandbox-dashboard-checklist` - generate a static review-console demo checklist from committed UI source/tests.
- `make operator-sandbox-demo-packet` - generate an ignored operator-managed sandbox/workbench demo review packet.
- `make live-demo-preflight` - run a secret-free read-only preflight for the local workbench demo.
- `make live-demo-status` - print local demo status and write the ignored `LIVE_DEMO_INDEX.md` operator index.
- `make live-demo-smoke` - generate a secret-free live-demo smoke transcript without starting services.
- `make live-demo-evidence-summary` - generate a secret-free digest of live-demo status, smoke, signed fixture evidence, negative transcripts, correlation packets, and consolidated handoff artifacts.
- `make live-demo-packet` - generate an ignored live-demo readiness packet tying together preflight, sandbox demo, Agent Run correlation, and no-new-powers evidence.
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
- `make v08-capability-design-gate` - validate the historical design-only gate, now superseded by the limited v0.9 implementation record.
- `make v08-final-decision-packet` - validate the final v0.8 product-risk decision packet.
- `make v09-design-only-gate` - validate the historical v0.9 design-only packet and its superseding implementation record.
- `make git-commit-metadata-proposal-check` - validate the first design-only capability proposal.
- `make git-ref-summary-proposal-check` - validate the next read-only Git metadata proposal.
- `make git-ref-summary-implementation-plan-check` - validate the `git.show.ref_summary` implementation-planning packet without authorizing runtime work.
- `make git-ref-summary-implementation-gate` - validate the approved read-only `git.show.ref_summary` implementation boundary.
- `make git-commit-metadata-implementation-plan-check` - validate the historical implementation-planning packet.
- `make git-commit-metadata-implementation-gate` - validate the approved read-only `git.show.commit_metadata` implementation boundary.
- `make read-only-metadata-capability-check` - validate the shared read-only metadata contract, privacy policy, checklist, review template, and v3 debt register.
- `make read-only-capability-inventory-gate` - validate the approved bounded read-only metadata
  tool inventory, implementation gates, source-review handoffs, and release-check wiring.
- `make v3-next-capability-candidate-check` - validate the design-only selection for the next
  candidate, `project.dependency.summary`.
- `make next-capability-readiness` - validate the current bounded metadata inventory and the
  preflight requirements before selecting or implementing another capability.
- `make project-dependency-summary-proposal-check` - validate the design-only
  `project.dependency.summary` proposal without authorizing runtime work.
- `make project-dependency-summary-implementation-plan-check` - validate the
  `project.dependency.summary` implementation-planning packet without authorizing runtime work.
- `make project-dependency-summary-design-review-packet` - generate the design-only review packet
  for `project.dependency.summary`.
- `make project-manifest-summary-proposal-check` - validate the design-only
  `project.manifest.summary` proposal without authorizing runtime work.
- `make project-manifest-summary-implementation-plan-check` - validate the
  `project.manifest.summary` implementation-planning packet without authorizing runtime work.
- `make project-manifest-summary-implementation-gate` - validate the bounded read-only
  implementation decision for `project.manifest.summary`.
- `make project-manifest-summary-source-review-bundle` - build the focused source/test/evidence
  handoff for the approved `project.manifest.summary` implementation.
- `make git-commit-metadata-source-review-bundle` - build the focused source/test/evidence handoff for the approved `git.show.commit_metadata` implementation.
- `make git-ref-summary-source-review-bundle` - build the focused source/test/evidence handoff for the approved `git.show.ref_summary` implementation.
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
- `make demo-flow` - run governed reads, redaction, patch proposal, approval, apply, audit checks, and write `DEMO_FLOW_RESULT.md`.
- `make demo-reset-guide` - generate `DEMO_RESET_GUIDE.md` with read-only reset/recovery guidance.
- `make demo-flow-result-check` - validate the optional demo result artifact if present.
- `make demo-observed-summary` - generate `DEMO_OBSERVED_SUMMARY.md` after an observed local demo.
- `make demo-operator-walkthrough` - generate `OPERATOR_DEMO_WALKTHROUGH.md` with expected screens, evidence files, next human steps, and reset guidance.
- `make demo-evidence-packet` - package demo readiness, state, reset, and result-check evidence.
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
filesystem contract check, signed evidence demo, negative transcripts, operator sandbox,
live-demo, and operator workbench packets, focused v0.6 dispatch packets, review bundle,
consolidated packet, packet redaction scan, and docs site. Use
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
and checked with `make v09-design-only-gate`; it remains the historical design-only boundary that
was superseded only for the reviewed bounded `git.show.commit_metadata` and `git.show.ref_summary`
implementations.
The first design-only capability proposal is
[docs/codex/capability-proposals/git-show-commit-metadata.md](docs/codex/capability-proposals/git-show-commit-metadata.md)
and is checked with `make git-commit-metadata-proposal-check`.
The implementation-planning packet is
[docs/codex/capability-implementation-plans/git-show-commit-metadata.md](docs/codex/capability-implementation-plans/git-show-commit-metadata.md)
and is checked with `make git-commit-metadata-implementation-plan-check`; it prepares a later
implementation decision without adding manifests, executors, policy rules, MCP exposure, or runtime
behavior.
The approved v0.9 implementation record is
[docs/codex/v0.9-git-commit-metadata-implementation.md](docs/codex/v0.9-git-commit-metadata-implementation.md)
and is checked with `make git-commit-metadata-implementation-gate`; it permits exactly one bounded
read-only Git metadata tool and does not unlock broader capability implementation.
The focused source-review handoff for that implementation is recorded in
[docs/codex/v0.9-git-commit-metadata-source-review.md](docs/codex/v0.9-git-commit-metadata-source-review.md).
Generate the focused source/test/evidence bundle with `make git-commit-metadata-source-review-bundle`;
the ignored output is `var/review-packets/v0.9/git-commit-metadata-source-review/`.
The v0.9 lane-closure summary is recorded in
[docs/codex/v0.9-lane-closure-summary.md](docs/codex/v0.9-lane-closure-summary.md): internal
xhigh review is sufficient to continue local-preview development for this one bounded read-only Git
metadata track, while public/security-product positioning and broader capability expansion remain
unapproved.
The next read-only capability seed is
[docs/codex/v0.9-next-read-only-capability-seed.md](docs/codex/v0.9-next-read-only-capability-seed.md);
it is historical planning material for the now-implemented `git.show.ref_summary` lane.
The next read-only capability proposal is
[docs/codex/capability-proposals/git-show-ref-summary.md](docs/codex/capability-proposals/git-show-ref-summary.md)
and is checked with `make git-ref-summary-proposal-check`.
The proposal review/remediation note is
[docs/codex/v0.9-git-ref-summary-proposal-review.md](docs/codex/v0.9-git-ref-summary-proposal-review.md).
The implementation-planning packet is
[docs/codex/capability-implementation-plans/git-show-ref-summary.md](docs/codex/capability-implementation-plans/git-show-ref-summary.md)
and is checked with `make git-ref-summary-implementation-plan-check`.
The approved implementation record is
[docs/codex/v0.9-git-ref-summary-implementation.md](docs/codex/v0.9-git-ref-summary-implementation.md)
and is checked with `make git-ref-summary-implementation-gate`. It adds one bounded read-only Git
ref metadata tool and does not unlock broader capability implementation. The focused source-review
handoff is [docs/codex/v0.9-git-ref-summary-source-review.md](docs/codex/v0.9-git-ref-summary-source-review.md);
the ignored output is `var/review-packets/v0.9/git-ref-summary-source-review/`.
The `project.manifest.summary` implementation record is
[docs/codex/v3-project-manifest-summary-implementation.md](docs/codex/v3-project-manifest-summary-implementation.md)
and is checked with `make project-manifest-summary-implementation-gate`. It adds one bounded
read-only project manifest metadata tool with no file contents, dependency names, script values,
package-manager execution, registry/network access, or recursive discovery. The focused
source-review handoff is
[docs/codex/v3-project-manifest-summary-source-review.md](docs/codex/v3-project-manifest-summary-source-review.md);
the ignored output is `var/review-packets/v0.9/project-manifest-summary-source-review/`.
The shared expansion-prep hardening docs are
[docs/codex/read-only-local-metadata-contract.md](docs/codex/read-only-local-metadata-contract.md),
[docs/codex/read-only-capability-inventory.md](docs/codex/read-only-capability-inventory.md),
[docs/codex/next-capability-readiness.md](docs/codex/next-capability-readiness.md),
[docs/codex/v3-next-capability-candidate-evaluation.md](docs/codex/v3-next-capability-candidate-evaluation.md),
[docs/codex/metadata-privacy-policy.md](docs/codex/metadata-privacy-policy.md),
[docs/codex/read-only-metadata-capability-checklist.md](docs/codex/read-only-metadata-capability-checklist.md),
[docs/codex/read-only-capability-source-review-template.md](docs/codex/read-only-capability-source-review-template.md),
and [docs/codex/v3-readiness-debt-register.md](docs/codex/v3-readiness-debt-register.md); they are
checked with `make read-only-metadata-capability-check` and
`make read-only-capability-inventory-gate`. The next-capability preflight is
[docs/codex/next-capability-readiness.md](docs/codex/next-capability-readiness.md) and is checked
with `make next-capability-readiness`; it records that the next candidate is
`project.dependency.summary` and implementation remains blocked until a fresh proposal,
implementation plan, source-review
handoff, and explicit decision are recorded. The historical design-only candidate evaluation is
[docs/codex/v3-next-capability-candidate-evaluation.md](docs/codex/v3-next-capability-candidate-evaluation.md)
and the active design-only selection is
[docs/codex/v3-project-dependency-summary-selection.md](docs/codex/v3-project-dependency-summary-selection.md),
checked with `make v3-next-capability-candidate-check`. The proposal for that active candidate is
[docs/codex/capability-proposals/project-dependency-summary.md](docs/codex/capability-proposals/project-dependency-summary.md)
and is checked with `make project-dependency-summary-proposal-check`; the implementation-planning
packet is
[docs/codex/capability-implementation-plans/project-dependency-summary.md](docs/codex/capability-implementation-plans/project-dependency-summary.md)
and is checked with `make project-dependency-summary-implementation-plan-check`; the design-review
packet is generated with `make project-dependency-summary-design-review-packet`. The proposal for
the now-implemented historical
candidate is
[docs/codex/capability-proposals/project-manifest-summary.md](docs/codex/capability-proposals/project-manifest-summary.md)
and is checked with `make project-manifest-summary-proposal-check`. The implementation-planning
packet is
[docs/codex/capability-implementation-plans/project-manifest-summary.md](docs/codex/capability-implementation-plans/project-manifest-summary.md)
and is checked with `make project-manifest-summary-implementation-plan-check`. The bounded
implementation decision is
[docs/codex/v3-project-manifest-summary-implementation.md](docs/codex/v3-project-manifest-summary-implementation.md)
and is checked with `make project-manifest-summary-implementation-gate`.
The existing `make v09-design-review-packet` target remains the historical
`git.show.commit_metadata` design-review packet; use `make git-ref-summary-source-review-bundle`
for the focused `git.show.ref_summary` source-review handoff.
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

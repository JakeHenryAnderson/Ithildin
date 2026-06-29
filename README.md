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
The compliance mapping architecture packet is
[docs/codex/compliance-mapping-architecture.md](docs/codex/compliance-mapping-architecture.md) and
is checked with `make compliance-mapping-architecture-check`; it defines future mapping-template,
operator responsibility, legal-review, and evidence-field requirements while keeping compliance
automation, legal conclusions, and regulated-industry compliance claims blocked.
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
- `make test-fast` - run Python tests excluding generated-packet `slow_packet` tests for the
  development loop.
- `make runtime-check` - run the focused core API/governed-tool/security/policy runtime suite for
  backend iteration before broader release gates.
- `make docs-check` - run the docs-only fast gate for pure docs/README/AGENTS edits without lint,
  typecheck, or generated review-packet rebuilds.
- `make dev-check` - default dirty-file-aware development gate; wraps `make smart-check` so routine
  work uses the smallest honest validation set instead of the full release gate.
- `make quick-check` - run the fast local development gate: core boundary checks, lint, and
  typecheck without generated review-packet rebuilds.
- `make readiness-check` - run the medium development gate: `quick-check`, docs generation, and
  a curated release/docs smoke test set without generated review-packet rebuilds.
- `make capability-check` - run the bounded capability-development gate for read-only tool work:
  manifest/tool-surface/no-new-powers checks, project-intelligence readiness, policy parity,
  focused runtime tests, and `test-fast`.
- `make evidence-check` - run the evidence/review-state gate for docs, findings, release evidence,
  review-run manifests, packet recursion, and docs-site wiring without the full Python suite.
- `make validation-plan` - inspect the current dirty file set and recommend the smallest honest
  validation gate set for those changes.
- `make validation-decision` - print the current validation mode, deferred handoff gates, release
  slice suggestions, and command guidance for the dirty file set.
- `make development-efficiency-status` - print the compact current-state view that combines
  validation choice, release-check shape, technical MVP operator-trial readiness, and enterprise
  handoff action.
- `make smart-check` - run the current validation plan automatically and print per-command timing
  evidence; use this as the default development gate when you are not preparing a release handoff.
- `make smart-handoff-check` - run the current validation plan including deferred release/review
  gates; use this before handoff when the dirty-file plan says full release evidence is required.
- `make validation-timing` - time the fast validation profile so slowdowns are visible before they
  become normal; pass helper arguments with `ARGS=...`, such as
  `make validation-timing ARGS=--dry-run`.
- `make release-check-profile` - statically summarize the full `release-check` prerequisite graph
  and largest target groups without running the slow release gate.
- `make release-check-impact` - inspect the dirty file set and suggest relevant `release-check`
  slice categories without running the slow release gate.
- `make release-check-slice ARGS="--category enterprise"` - plan a focused subset of `release-check`
  targets by profile category; add `--run` only when you intentionally want to execute that slice.
- `make packet-check-recursion-guard` - fail fast if a generated packet check imports known
  high-level status/export builders that can recursively rebuild the packet graph.
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
- `make release-check` - run the full local release gate, including generated-artifact and packet
  checks that may be slow.
- `make release-evidence` - print a secret-free local release evidence snapshot.
- `make release-evidence-gate` - generate and validate a temporary release evidence snapshot.
- `make release-evidence-validate FILE=...` - validate a saved release evidence JSON snapshot.
- `make release-packet` - print a v0.2 external-review packet snapshot.
- `make v04-review-packet` - print a v0.4 review-candidate packet snapshot.
- `make review-candidate` - run the full local handoff gate, capture a same-run `release-check` transcript, include focused v0.6 dispatch packets, operator-managed sandbox and live-demo packets, the compact v1.0 RC packet, and regenerate review artifacts.
- `make v05-review-candidate` - run the v0.5 handoff gate plus source-review artifact prep.
- `make review-packet-bundle` - build an ignored v0.2 review handoff bundle under `var/review-packets/`.
- `make review-packet-consolidated` - build the 10-attachment-friendly GPT review packet.
- `make agent-run-timeline-packet` - generate an ignored Agent Run timeline source/evidence review packet.
- `make review-packet-diff OLD=... NEW=...` - compare two review packet bundles by artifact hash.
- `make review-packet-diff-gate OLD=... NEW=...` - require packet hashes and fail on removed artifacts.
- `make review-packet-source-pointers` - validate source-file pointers used by reviewer packets.
- `make packet-redaction-scan` - scan generated review packet artifacts for obvious secret material.
- `make review-run-manifest-refresh` - refresh ignored local review-run manifests after new commits or tree changes, then re-run validation.
- `make local-prompt-triage` - classify a local task prompt with deterministic host-side heuristics; no model, network, proxy, or tool-power changes.
- `make agent-workflow-check` - validate the repo `AGENTS.md` planner-implementer guidance, role boundaries, docs wiring, and no-security-boundary caveat.
- `make low-implementer-delegation-packet` - generate the ignored Low Codex mechanical task packet artifacts without calling a model or changing runtime behavior.
- `make low-implementer-delegation-check` - validate the low-implementer packet inventory, docs wiring, and no-new-powers boundary.
- `make low-implementer-ticket-catalog-check` - validate the approved low-implementer ticket catalog and manager scorecard wiring.
- `make internal-review-packet` - build v2 local prompts for internal AI/subagent source review.
- `make source-review-transcript-packet` - generate a source-review transcript skeleton under ignored `var/`.
- `make reviewer-artifact-manifest` - generate the reviewer artifact inventory for the v1.0 RC and enterprise handoff packets.
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
- `make workbench-evidence-packet` - generate an ignored operator workbench evidence packet tying together Agent Runs, approvals, audit, live demo, observed sandbox artifact evidence, sandbox/workspace posture, and handoff artifacts.
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
- `make governed-artifact-transfer-lab` - generate the Stage 1 Part 1 Ithildin-only known-good
  artifact transfer lab packet under `var/review-packets/v3/governed-artifact-transfer-lab/`.
- `make governed-artifact-transfer-lab-check` - validate the Stage 1 lab packet, docs wiring,
  no-new-powers boundary, and Mission-Control/VM-disabled posture.
- `make governed-artifact-transfer-stage2` - generate the Stage 1 Mission Control handoff and
  Stage 2 simulated sandbox-transfer evidence packet without starting a real VM or sandbox.
- `make governed-artifact-transfer-stage2-check` - validate the Mission Control handoff metadata,
  simulated sandbox copy/return hashes, VM-readiness plan, and no-new-powers boundary.
- `make hello-world-sandbox-demo-check` - validate the staged roadmap for the Mission Control +
  local LLM Hello World sandbox demo and confirm the bounded sandbox artifact write boundary.
- `make hello-world-sandbox-demo-packet` - generate an ignored evidence-only Hello World sandbox
  demo packet under `var/review-packets/v3/hello-world-sandbox-demo/` without governed tool calls,
  real VM startup, Mission Control runtime behavior, or host promotion.
- `make hello-world-sandbox-demo-packet-check` - validate the generated packet shape in a temporary
  directory while confirming it performs no governed tool calls, VM startup, Mission Control
  runtime behavior, or host promotion.
- `make hello-world-sandbox-observed-demo` - generate an observed Hello World packet that wraps the
  approval-gated `sandbox.artifact.write_text` fixture flow with Mission Control/local-model
  metadata labels.
- `make hello-world-sandbox-observed-demo-check` - validate the observed Hello World packet, docs
  wiring, governed-tool evidence, and no-VM/no-Mission-Control-runtime/no-host-promotion boundary.
- `make hello-world-mission-control-handoff` - generate a metadata-only Mission Control
  display/import handoff for the observed Hello World evidence.
- `make hello-world-mission-control-handoff-check` - validate the Mission Control handoff packet,
  docs wiring, and no-runtime/no-local-model/no-VM/no-host-promotion boundary.
- `make mission-control-handoff-fixture-pack` - generate one valid and fourteen negative
  Mission Control display/import handoff JSON fixtures for future importer tests.
- `make mission-control-handoff-fixture-pack-check` - validate the generated fixture pack, artifact
  hashes, safe reason labels, docs wiring, and no-runtime/no-authority-transfer boundary.
- `make mission-control-importer-acceptance-matrix-check` - validate the future Mission Control
  display-only importer acceptance matrix against the generated handoff fixtures without approving
  runtime importer behavior.
- `make mission-control-handoff-reference-validator` - run the Ithildin-side reference validator
  for the generated Mission Control display/import fixtures without calling Mission Control or
  approving runtime importer behavior.
- `make sandbox-promotion-evidence-contract-check` - validate the future trusted-host promotion
  evidence contract while confirming host promotion remains unimplemented.
- `make trusted-host-promotion-decision-intake-check` - validate the post-RC decision-intake
  checklist for the trusted-host promotion lane while keeping host promotion blocked.
- `make trusted-host-promotion-state-machine-check` - validate the design-only promotion state
  machine, transition evidence, and denial plan while keeping host promotion blocked.
- `make trusted-host-promotion-negative-fixtures-check` - validate the design-only promotion
  denial fixtures and transcript shape while keeping host promotion blocked.
- `make trusted-host-promotion-zone-contract-check` - validate the design-only promotion
  source/staging/approved zone labels while keeping host promotion blocked.
- `make trusted-host-promotion-implementation-plan-check` - validate the design-only promotion
  implementation-plan skeleton while keeping host promotion blocked.
- `make trusted-host-promotion-source-review-packet` - generate the focused design/source-review
  packet for trusted-host promotion while keeping host promotion blocked.
- `make trusted-host-promotion-source-review-packet-check` - validate the trusted-host promotion
  source-review packet wiring and artifact hashes.
- `make trusted-host-promotion-disposition-packet` - generate the external disposition handoff
  packet for the trusted-host promotion planning lane while keeping host promotion blocked.
- `make trusted-host-promotion-disposition-packet-check` - validate the trusted-host promotion
  disposition packet wiring and artifact hashes.
- `make trusted-host-promotion-external-review-bundle` - generate the consolidated external-review
  launch bundle for `ERG-005`, combining the source packet, disposition packet, contracts, negative
  fixtures, response/closure dry run, queue status, and command evidence while keeping host
  promotion blocked.
- `make trusted-host-promotion-external-review-bundle-check` - validate the trusted-host promotion
  external-review launch bundle wiring, boundary flags, and artifact hashes.
- `make trusted-host-promotion-disposition-closure-check` - validate the fail-closed trusted-host
  promotion closure gate while keeping host promotion blocked.
- `make trusted-host-promotion-response-dry-run` - exercise temporary normalized-response fixtures
  for the trusted-host promotion closure gate while restoring the ignored response path and keeping
  `ERG-005` blocked.
- `make trusted-host-promotion-response-kit` - generate the response-intake kit for converting real
  `ERG-005` reviewer feedback into normalized evidence while keeping trusted-host promotion,
  implementation planning, host writes, and automatic promotion blocked.
- `make trusted-host-promotion-external-response-intake-check` - validate the external response
  intake template for the trusted-host promotion lane while keeping host promotion blocked.
- `make trusted-host-promotion-internal-review-check` - validate the internal design/source-review
  disposition for trusted-host promotion while keeping runtime host promotion blocked.
- `make sandbox-artifact-write-text-preimplementation-check` - historical preimplementation
  boundary check retained for lineage; active release readiness now uses the implementation gate.
- `make sandbox-artifact-write-text-implementation-gate` - validate the bounded local-preview
  runtime implementation for `sandbox.artifact.write_text`.
- `make sandbox-artifact-write-text-negative-transcripts` - generate observed local fixture denial
  transcripts for the sandbox artifact write path.
- `make sandbox-artifact-observed-demo` - generate an observed local fixture approval/execution
  packet for `sandbox.artifact.write_text` without Mission Control runtime behavior, VM/container
  lifecycle, shell execution, or host promotion.
- `make sandbox-artifact-observed-demo-check` - validate the observed demo packet shape, docs
  wiring, and no-new-powers boundary.
- `make sandbox-artifact-write-text-source-review-bundle` - generate the focused source-review
  handoff packet for the sandbox artifact write path.
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
- `make git-tag-metadata-proposal-check` - validate the `git.show.tag_metadata` design-only proposal.
- `make git-tag-metadata-implementation-plan-check` - validate the `git.show.tag_metadata` implementation-planning packet without authorizing runtime work.
- `make git-tag-metadata-implementation-gate` - validate the approved read-only `git.show.tag_metadata` implementation boundary.
- `make git-commit-metadata-implementation-plan-check` - validate the historical implementation-planning packet.
- `make git-commit-metadata-implementation-gate` - validate the approved read-only `git.show.commit_metadata` implementation boundary.
- `make read-only-metadata-capability-check` - validate the shared read-only metadata contract, privacy policy, checklist, review template, and v3 debt register.
- `make read-only-capability-inventory-gate` - validate the approved bounded read-only metadata
  tool inventory, implementation gates, source-review handoffs, and release-check wiring.
- `make read-only-project-intelligence` - validate the consolidated eleven-tool read-only project
  intelligence slice without adding runtime powers.
- `make v3-next-capability-candidate-check` - validate the historical design-only selection that led
  to the now-implemented `project.dependency.summary`.
- `make next-capability-readiness` - validate the current bounded metadata inventory and the
  preflight requirements before selecting or implementing another capability.
- `make next-capability-candidate-evaluation-2-check` - validate the planning-only evaluation of
  release, license, and ownership metadata candidates and the selected `project.release.summary`
  next candidate.
- `make v1-rc-roadmap-check` - validate the local-first v1.0 RC roadmap, delegation sequencing,
  and no-new-powers boundaries.
- `make v1-rc-status-check` - validate the canonical v1.0 RC status map, current tool count,
  blocked/deferred boundaries, and release-check/docs wiring.
- `make v1-progress-assessment` - validate the conservative v1.0/local-preview and enterprise
  progress bands against the canonical RC status, enterprise gap matrix, and capability-readiness
  gates.
- `make technical-mvp-ticket-map` - validate the current technical MVP ticket map across the
  closed local-preview foundations, ready operator trial surface, blocked sandbox/VM promotion
  lanes, and enterprise architecture backlog.
- `make technical-mvp-operator-trial-readiness` - validate the checked local-preview operator-trial
  readiness view for the technical MVP and the exact remaining hands-on trial commands.
- `make development-efficiency-status` - validate the compact gate-selection and handoff-status
  view that decides whether the next step is a focused development gate or full handoff evidence.
- `make v1-rc-feature-freeze` - validate the v1.0 RC feature-freeze decision: tool count `24`,
  no selected next capability, blocked capability expansion, and no public/security-product
  positioning.
- `make v1-rc-external-review-prompt-check` - validate the v1.0 RC external/human reviewer prompt
  and confirm it is included in the compact v1.0 RC packet.
- `make v1-rc-final-handoff-check` - validate the current v1.0 RC final handoff map, go/no-go
  state, packet reading order, command expectations, and no-overclaim boundaries.
- `make v1-rc-post-review-triage-check` - validate the v1.0 RC post-review triage map for
  normalizing reviewer responses without mutating findings or unfreezing capabilities.
- `make v1-operator-quickstart-check` - validate the v1.0 local-preview operator quickstart,
  demo command order, evidence reading order, and no-new-powers boundaries.
- `make v1-operator-trial-checklist-check` - validate the v1.0 local-preview operator trial
  checklist for pass/fail demo evidence, Compose cleanup, non-Compose evidence, and blocked claims.
- `make v1-operator-trial-record` - generate a secret-free v1.0 local-preview operator trial
  evidence record under `var/review-packets/v1.0/operator-trial/`.
- `make v1-operator-trial-record-check` - validate the generated-record workflow, packet wiring,
  docs inclusion, no-new-powers posture, and blocked claims.
- `make v1-workbench-evidence-check` - validate the v1.0 workbench/evidence closure map across
  Agent Run, approval, audit, signed evidence, demo, and packet readiness.
- `make v1-assurance-closure-check` - validate the v1.0 local-preview assurance ledger across
  findings, accepted risks, closure-matrix status, external-pending rows, and claim boundaries.
- `make v1-rc-readiness` - validate the v1.0 local-preview RC umbrella across status, quickstart,
  workbench/evidence, assurance, tool-surface, no-new-powers, and packet redaction gates.
- `make v1-rc-packet` - generate a compact ignored v1.0 RC handoff packet under
  `var/review-packets/v1.0/rc/`.
- `make enterprise-readiness-runway-check` - validate the design-only runway from v1.0
  local-preview RC toward Mission Control display integration, sandbox/VM proof of concept,
  trusted-host promotion, production IAM/storage, SIEM-shaped exports, and compliance mapping
  support without enabling those powers today.
- `make enterprise-readiness-gap-matrix-check` - validate the enterprise readiness gap matrix that
  maps post-RC lanes to blockers, required evidence, allowed planning states, and blocked
  production/security claims.
- `make enterprise-progress-model` - validate the operator progress ladder that keeps v1.0
  local-preview progress separate from enterprise-control-plane readiness and blocked powers.
- `make enterprise-dependency-ladder` - validate the post-RC dependency order from `ERG-003` and
  `ERG-002` through later live sandbox/VM, Mission Control, and enterprise architecture lanes
  without approving runtime powers.
- `make enterprise-transition-map` - validate the allowed post-review transition states for
  `ERG-003`, `ERG-002`, `ERG-004`, and later enterprise lanes while keeping runtime authority,
  public/security-product positioning, and new power classes blocked.
- `make enterprise-north-star-roadmap` - validate the operator-facing north-star map from v1.0
  local-preview RC through `ERG-003`, `ERG-002`, Stage 2 sandbox/VM, Mission Control, and later
  enterprise architecture lanes without approving runtime powers.
- `make enterprise-operator-next-action` - validate the read-only operator next-action summary so
  the current send/intake step points to the send or response refresh helper without recording
  review, normalizing responses, closing lanes, or approving runtime powers.
- `make enterprise-external-review-queue-check` - validate the post-RC enterprise external-review
  queue that orders ERG-002 through ERG-010 review lanes, points to the current packets/intake
  docs, and keeps runtime behavior blocked.
- `make enterprise-next-review-handoff` - generate the compact pointer to the current next
  enterprise review packet and response path.
- `make enterprise-next-review-handoff-check` - validate that the next-review handoff still points
  to `ERG-003` and keeps runtime behavior blocked.
- `make enterprise-next-review-ready-check` - verify the current `ERG-003` external-review bundle,
  reviewed-packet hash helper, handoff pointer, and fail-closed response posture are ready for
  operator handoff without closing the lane.
- `make enterprise-review-send-readiness` - summarize which enterprise external-review packets are
  mechanically ready for operator handoff while keeping implementation approval, runtime behavior,
  and lane closure blocked.
- `make enterprise-current-checkpoint` - validate the top-level enterprise checkpoint across v1.0
  RC status, current send set, response status, and blocked runtime boundaries.
- `make enterprise-status-export` - write an ignored display-only JSON/Markdown status export for
  operator dashboards and Mission Control display/import experiments without approving runtime
  behavior.
- `make enterprise-status-export-check` - validate the status export contract, wiring, and
  generated artifact shape.
- `make mission-control-enterprise-status-import-check` - validate the future Mission Control
  display-only import contract for the enterprise status export without approving Mission Control
  runtime importer behavior.
- `make mission-control-enterprise-status-fixtures` - generate one valid and twelve negative
  enterprise status display/import fixtures for future Mission Control importer tests.
- `make mission-control-enterprise-status-fixtures-check` - validate the enterprise status fixture
  pack, artifact hashes, and safe rejection expectations.
- `make mission-control-enterprise-status-acceptance-matrix-check` - validate the future Mission
  Control enterprise status importer acceptance matrix against the generated fixture pack.
- `make mission-control-enterprise-status-reference-validator` - run the Ithildin-side reference
  validator for Mission Control enterprise status display/import fixtures.
- `make enterprise-dual-review-handoff` - generate the compact pointer for sending the current two
  recommended enterprise reviews, `ERG-003` and `ERG-002`, without approving runtime behavior.
- `make enterprise-dual-review-outbox` - copy the current `ERG-003` and `ERG-002` send-ready
  review files into one ignored outbox with an index and artifact hashes, without recording review
  or closing either lane.
- `make enterprise-review-send-manifest` - generate a checked send manifest for the current
  `ERG-003` and `ERG-002` outbox, response paths, and still-blocked boundaries.
- `make enterprise-review-send-checklist` - validate the operator checklist for attaching the
  current `ERG-003` and `ERG-002` review packets and routing responses through the fail-closed
  inbox.
- `make enterprise-review-send-quickstart` - generate a one-page operator index naming the exact
  `ERG-003`/`ERG-002` directories, prompt files, hash manifests, and raw-response placeholders.
- `make enterprise-review-submission-prompt` - generate a paste-ready operator prompt for sending
  the current `ERG-003` and `ERG-002` review packets as separate review requests.
- `make enterprise-review-send-receipt-template` - generate an ignored operator receipt template
  for recording send timestamps, reviewer/thread placeholders, packet hashes, and raw-response paths
  after the human send step, without recording review or closing lanes.
- `make enterprise-review-send-package` - generate a compact operator package index over the
  current `ERG-003` and `ERG-002` prompts, lane attachment manifests, hash manifests, receipt
  template, and response inbox paths without recording review or closing lanes.
- `make enterprise-review-send-session-record` - generate an ignored non-authoritative
  send-session scaffold tying the current package hashes, lane prompts, raw-response paths, and
  operator fill-in fields together without recording review or closing lanes.
- `make enterprise-review-handoff-drill` - generate a checked operator drill tying together the
  current send outbox, send manifest, response inbox, status board, and intake drill without
  recording review, normalizing real responses, or closing lanes.
- `make enterprise-dual-response-inbox` - create ignored raw-response placeholders and exact
  normalization/dry-run/closure commands for `ERG-003` and `ERG-002`, without normalizing responses
  or closing either lane.
- `make enterprise-dual-response-readiness` - summarize whether normalized responses are present for
  the current dual enterprise review handoff without recording review or closing either lane.
- `make enterprise-response-waiting-room` - summarize whether ignored `ERG-003`/`ERG-002`
  raw-response files are still placeholders or look ready for paste preflight, without reading
  response contents into output.
- `make enterprise-response-status-board` - summarize normalized-response presence across all
  enterprise review lanes and fail closed until any present response is handled by lane intake.
- `make enterprise-response-status-board-snapshot` - write an ignored, hashed, read-only snapshot of
  the enterprise response status board for operator handoff without normalizing responses or closing
  lanes.
- `make enterprise-response-normalization-coverage` - verify every enterprise response-board lane
  has a supported external-response normalization area and finding namespace without normalizing
  responses or closing lanes.
- `make enterprise-response-inbox` - create ignored raw-response placeholders and exact
  normalization/dry-run/closure commands for all enterprise response lanes without normalizing
  responses or closing any lane.
- `make enterprise-response-intake-drill` - run fixture-only response-intake drills across all
  enterprise lanes, restoring ignored response state and proving no review is recorded or lane is
  closed.
- `make enterprise-response-command-matrix` - validate the committed operator command matrix for
  applying future enterprise reviewer responses through generated raw-response paths, normalizers,
  dry-runs, closure gates, response kits, and allowed transition states without recording review or
  closing lanes.
- `make enterprise-response-application-protocol` - validate the checked operator protocol for
  applying future enterprise reviewer responses through lane dry-runs, closure gates, and later
  committed decision records without approving runtime expansion.
- `make enterprise-response-application-rehearsal` - validate the active `ERG-003`/`ERG-002`
  response-application path end-to-end before real reviewer responses arrive, without normalizing
  responses, writing response files, recording review, or closing lanes.
- `make enterprise-response-intake-quickstart` - validate the compact operator quickstart for
  pasting future `ERG-003` and `ERG-002` responses into ignored raw-response paths and running the
  lane dry-run/closure sequence without recording review or approving runtime expansion.
- `make enterprise-response-paste-preflight` - validate pasted `ERG-003` and `ERG-002` raw reviewer
  responses are UTF-8, size-bounded, lane-matched, and non-placeholder before the existing normalizer
  path, without normalizing responses or recording review.
- `make enterprise-response-intake-refresh` - regenerate the current ignored response inboxes and
  rerun receive-side status, rehearsal, quickstart, and paste-preflight checks without normalizing
  responses, recording review, or closing lanes.
- `make enterprise-handoff-consistency-check` - validate the current `ERG-003`/`ERG-002`
  enterprise handoff docs all point to the dual-response inbox, receipt template, and paste
  preflight flow without recording review or closing lanes.
- `make enterprise-review-send-preflight` - run the final operator pre-send check across the
  current `ERG-003`/`ERG-002` send artifacts, response landing pad, handoff drill, response state,
  and consistency gate without recording review or closing lanes.
- `make enterprise-review-send-refresh` - regenerate the current ignored `ERG-003`/`ERG-002`
  send artifacts and response landing pad, then run the final pre-send preflight.
- `make post-rc-decision-gate` - validate the required post-RC decision-record gate before any
  frozen lane can move beyond documentation or planning into implementation work.
- `make post-rc-decision-record-template-check` - validate the reusable post-RC decision record
  template for future post-freeze lane decisions.
- `make post-rc-decision-record-examples-check` - validate example post-RC decision records for
  Mission Control display planning, sandbox/VM no-go, and post-freeze capability no-go lanes.
- `make post-rc-decision-register-check` - validate the current post-RC decision register across
  planning-only, no-go, and blocked enterprise-readiness lanes.
- `make public-security-product-positioning-decision-intake-check` - validate the `ERG-010`
  public/security-product positioning decision intake that keeps broader public/security,
  production, sandbox, EDR/MDM, SIEM custody, and compliance-product claims blocked.
- `make public-security-product-positioning-response-kit` - generate the ERG-010 response-intake
  kit for converting real reviewer feedback into normalized claim-boundary evidence without
  closing `ERG-010` or approving public/security-product positioning.
- `make production-identity-storage-architecture-check` - validate the design-only architecture
  packet for production identity and durable storage while keeping production IAM, runtime Postgres,
  remote admin use, and custody-grade audit claims blocked.
- `make production-identity-storage-disposition-packet` - generate the focused architecture
  disposition packet asking whether ERG-006/ERG-007 may continue planning while production identity,
  runtime Postgres, migrations, retention enforcement, and custody claims remain blocked.
- `make production-identity-storage-external-review-bundle` - generate the consolidated
  external-review launch bundle for ERG-006/ERG-007 production identity/storage architecture
  disposition without approving runtime identity, storage, migration, retention, or custody
  behavior.
- `make production-identity-storage-external-review-bundle-check` - validate the production
  identity/storage external-review launch bundle wiring, boundary flags, and artifact hashes.
- `make production-identity-storage-disposition-closure-check` - validate the fail-closed
  production identity/storage closure gate that keeps ERG-006/ERG-007 planning-only unless
  normalized source-level response evidence supports architecture continuation.
- `make production-identity-storage-response-dry-run` - exercise temporary normalized-response
  fixtures for the production identity/storage closure gate while restoring the ignored response
  path and keeping ERG-006/ERG-007 planning-only.
- `make production-identity-storage-response-kit` - generate the response-intake kit for converting
  real ERG-006/ERG-007 reviewer feedback into normalized evidence while keeping implementation
  planning, runtime identity, runtime storage, migrations, retention enforcement, and custody
  claims blocked.
- `make production-identity-storage-external-response-intake-check` - validate the response-intake
  template for production identity/storage reviewer feedback while keeping runtime identity and
  storage behavior blocked.
- `make siem-export-adapter-architecture-check` - validate the design-only SIEM export adapter
  architecture packet while keeping adapter runtime behavior, hosted telemetry, remote delivery,
  and SIEM custody claims blocked.
- `make siem-export-adapter-disposition-packet` - generate the focused SIEM adapter disposition
  packet asking whether ERG-008 may continue architecture planning while adapter runtime behavior,
  hosted telemetry, remote delivery, custody claims, and compliance claims remain blocked.
- `make siem-export-adapter-external-review-bundle` - generate the consolidated SIEM adapter
  external-review launch bundle for ERG-008 while keeping adapter runtime behavior and hosted
  delivery blocked.
- `make siem-export-adapter-external-review-bundle-check` - validate the SIEM adapter
  external-review launch bundle wiring, artifact hashes, command evidence, and non-approval
  boundary flags.
- `make siem-export-adapter-disposition-closure-check` - validate the fail-closed SIEM adapter
  closure gate that keeps ERG-008 planning-only unless normalized source-level response evidence
  supports architecture continuation.
- `make siem-export-adapter-response-dry-run` - exercise temporary normalized-response fixtures
  for the SIEM adapter closure gate while restoring the ignored response path and keeping ERG-008
  planning-only.
- `make siem-export-adapter-response-kit` - generate the response-intake kit for converting real
  ERG-008 reviewer feedback into normalized evidence while keeping implementation planning, SIEM
  adapter runtime behavior, hosted telemetry, remote delivery, and custody claims blocked.
- `make siem-export-adapter-external-response-intake-check` - validate the response-intake
  template for SIEM adapter reviewer feedback while keeping adapter runtime behavior, hosted
  telemetry, remote delivery, and custody claims blocked.
- `make compliance-mapping-architecture-check` - validate the design-only compliance mapping
  architecture packet while keeping compliance automation, legal conclusions, and regulated-industry
  compliance claims blocked.
- `make compliance-mapping-disposition-packet` - generate the focused compliance mapping
  disposition packet asking whether ERG-009 may continue architecture planning while runtime mapping,
  compliance automation, legal conclusions, automated certification, and regulated-industry
  compliance claims remain blocked.
- `make compliance-mapping-disposition-closure-check` - validate the fail-closed compliance mapping
  closure gate that keeps ERG-009 planning-only unless normalized source-level response evidence
  supports continued architecture planning.
- `make compliance-mapping-response-dry-run` - exercise temporary normalized-response fixtures for
  the compliance mapping closure gate while restoring the ignored response path and keeping
  ERG-009 planning-only.
- `make compliance-mapping-response-kit` - generate the response-intake kit for converting real
  ERG-009 reviewer feedback into normalized evidence while keeping implementation planning,
  runtime compliance mapping, compliance automation, legal advice, automated certification,
  regulated-industry compliance claims, and custody claims blocked.
- `make compliance-mapping-external-response-intake-check` - validate the response-intake template
  for compliance mapping reviewer feedback while keeping runtime mapping, compliance automation,
  legal advice, automated certification, regulated-industry compliance claims, and public/security
  product positioning blocked.
- `make enterprise-sandbox-control-plane-readiness-check` - validate the design-only enterprise
  sandbox/control-plane readiness map while keeping live VM/container inspection, sandbox
  orchestration, Mission Control runtime behavior, local model invocation, trusted-host promotion,
  SIEM adapter behavior, compliance automation, and new governed powers blocked.
- `make sandbox-vm-static-preflight-reviewer-reproduction-map-check` - validate the reviewer
  reproduction map for the CLI-only static sandbox/VM preflight lane while keeping `ERG-003`
  external-review-required and blocking live VM/container inspection, sandbox orchestration,
  Mission Control runtime behavior, local model invocation, trusted-host promotion, and network
  expansion.
- `make sandbox-vm-static-preflight-response-dry-run` - exercise temporary normalized-response
  fixtures against the `ERG-003` closure gate while restoring the ignored response path and not
  recording external review or closing the lane.
- `make sandbox-vm-static-preflight-response-kit` - generate the response-intake kit for
  converting real `ERG-003` reviewer feedback into normalized evidence while keeping `ERG-003`
  open until a later committed triage update and keeping `ERG-004` blocked.
- `make sandbox-vm-live-poc-response-kit` - generate the response-intake kit for converting real
  `ERG-004` decision-packet feedback into normalized evidence while keeping live POC implementation,
  runtime VM/container inspection, Mission Control runtime behavior, and new governed powers
  blocked.
- `make mission-control-display-integration-proposal-check` - validate the design-only Mission
  Control display/import proposal while confirming Mission Control does not become the executor,
  policy authority, approval authority, audit authority, local-model runner, VM/container manager,
  sandbox orchestrator, or trusted-host promotion path.
- `make mission-control-display-importer-plan-check` - validate the planning-only future Mission
  Control display importer implementation packet while keeping runtime importer behavior blocked.
- `make mission-control-display-decision-intake-check` - validate the post-RC decision-intake
  checklist for any future Mission Control display/importer implementation decision.
- `make mission-control-display-decision-record-skeleton-check` - validate the design-only
  Mission Control display decision-record skeleton that can be used after favorable normalized
  review evidence, while keeping runtime importer behavior and Mission Control authority transfer
  blocked.
- `make mission-control-display-review-packet` - generate the focused Mission Control display
  review packet with proposal, schema, negative fixtures, seed handoff evidence, command evidence,
  and artifact hashes.
- `make mission-control-display-disposition-packet` - generate the Mission Control display
  disposition packet asking whether ERG-002 may continue design-only planning while runtime importer
  behavior and authority transfer remain blocked.
- `make mission-control-display-external-review-bundle` - generate the 10-file Mission Control
  display/importer external-review launch bundle with display packet, disposition packet,
  readiness packet, contracts, response/closure evidence, queue status, command evidence, and
  artifact hashes while keeping runtime importer behavior blocked.
- `make mission-control-display-external-response-intake-check` - validate the response-intake
  template for Mission Control display/importer disposition responses while keeping runtime importer
  behavior and authority transfer blocked.
- `make mission-control-display-response-dry-run` - exercise temporary normalized-response fixtures
  for the Mission Control display/importer closure gate while restoring the ignored response path
  and keeping `ERG-002` planning-only.
- `make mission-control-display-response-kit` - generate the Mission Control display/importer
  response-intake kit with normalized-response examples, closure commands, boundary evidence, and
  artifact hashes while keeping runtime importer behavior blocked.
- `make mission-control-display-response-application-preflight-check` - validate the checked bridge
  between the all-lane enterprise response inbox and the ERG-002 lane-local normalized response path
  before a real Mission Control display/importer reviewer response is used.
- `make mission-control-display-response-application-record-check` - validate the manager-owned
  ERG-002 response-application record without recording review, closing ERG-002, or approving
  Mission Control runtime/importer authority.
- `make mission-control-display-response-application-playbook-check` - validate the ERG-002
  response-application command order and allowed committed file scope before any real response is
  applied.
- `make mission-control-display-next-review-ready-check` - verify the Mission Control
  display/importer external-review bundle, readiness packet, response kit, dry run, and fail-closed
  closure posture are ready for operator handoff without closing `ERG-002`.
- `make mission-control-integration-readiness-packet` - generate the consolidated Mission Control
  display/importer readiness handoff packet for the future Mission Control-side file/import display
  task while keeping Ithildin runtime behavior and Mission Control authority transfer blocked.
- `make mission-control-integration-implementation-ticket-check` - validate the planning-only
  Mission Control repository implementation ticket for a future display-only importer while keeping
  Mission Control outside Ithildin execution, policy, approval, audit, sandbox, local-model,
  SIEM, identity, and compliance authority.
- `make mission-control-handoff-schema-contract-check` - validate the Ithildin-side Mission
  Control handoff schema contract and the current `mission-control-handoff.json` seed payload while
  keeping the integration file/import-only and display-only.
- `make mission-control-handoff-negative-fixtures-check` - validate the future Mission Control
  importer/display negative cases for malformed, stale, unsafe-path, overclaiming, or content-leaking
  handoff payloads without calling Mission Control or adding runtime behavior.
- `make sandbox-vm-worker-boundary-charter-check` - validate the design-only sandbox/VM worker
  boundary charter for future operator-managed sandbox proof-of-concept planning while confirming
  Ithildin still does not orchestrate a VM/container or claim OS isolation.
- `make sandbox-vm-live-poc-evidence-contract-check` - validate the future live sandbox/VM POC
  evidence contract while confirming cross-source evidence planning does not approve live runtime
  authority.
- `make sandbox-vm-live-poc-preconditions-map-check` - validate the blocked `ERG-004`
  preconditions map while confirming favorable `ERG-003` disposition, a later decision record,
  cleanup/failure evidence, and role separation are required before any live POC planning.
- `make sandbox-vm-live-poc-preconditions-ready-check` - validate the blocked `ERG-004`
  aggregate readiness/status check while confirming the lane wiring is valid but implementation
  planning remains blocked on favorable `ERG-003` disposition and normalized `ERG-004` response
  evidence.
- `make sandbox-vm-live-poc-post-erg003-handoff-check` - validate the post-`ERG-003` handoff map
  for the still-blocked `ERG-004` live sandbox/VM proof-of-concept lane.
- `make sandbox-vm-live-poc-external-response-intake-check` - validate the blocked `ERG-004`
  external response intake template while confirming reviewer responses cannot mutate findings,
  close the gap, or approve live sandbox/VM runtime work.
- `make sandbox-vm-live-poc-decision-closure-check` - validate the blocked `ERG-004` fail-closed
  closure gate while confirming normalized source-level response evidence and favorable `ERG-003`
  disposition are required before any later decision-record consideration.
- `make sandbox-vm-live-poc-decision-record-skeleton-check` - validate the blocked `ERG-004`
  decision-record skeleton for a future implementation-planning-only decision while keeping live
  VM/container inspection, sandbox orchestration, Mission Control runtime behavior, local model
  invocation, and runtime implementation blocked.
- `make sandbox-vm-static-preflight-disposition-record-skeleton-check` - validate the `ERG-003`
  static preflight disposition-record skeleton for a future source-reviewed local-preview static
  preflight disposition while keeping `ERG-004`, live sandbox/VM work, runtime implementation, and
  new powers blocked.
- `make sandbox-vm-live-poc-response-dry-run` - exercise temporary normalized-response fixtures
  against the blocked `ERG-004` closure gate while restoring the ignored response path and not
  recording external review or approving live sandbox/VM runtime work.
- `make sandbox-vm-live-poc-prerequisite-disposition-dry-run` - exercise temporary `ERG-003`
  disposition-record fixtures before live POC planning while proving favorable static-preflight
  evidence satisfies only a prerequisite and does not unblock `ERG-004`.
- `make sandbox-vm-live-poc-decision-packet` - generate the blocked `ERG-004` external decision
  packet with readiness evidence, prerequisite static-preflight pointers, reviewer questions,
  command evidence, and artifact hashes without approving live sandbox/VM runtime work.
- `make sandbox-vm-live-poc-external-review-bundle` - generate the blocked `ERG-004` external
  review launch bundle that consolidates the decision packet, evidence contract, preconditions,
  response/closure dry runs, queue status, command evidence, and artifact hashes without approving
  implementation planning or live sandbox/VM runtime work.
- `make sandbox-vm-static-preflight-disposition-packet` - generate the `ERG-003` external
  disposition handoff packet,
  [docs/codex/sandbox-vm-static-preflight-disposition-packet.md](docs/codex/sandbox-vm-static-preflight-disposition-packet.md),
  with source-review pointers, reviewer questions, intake instructions, command evidence, and
  artifact hashes while keeping live sandbox/VM runtime work blocked.
- `make sandbox-vm-static-preflight-external-review-bundle` - generate the 10-file launch bundle
  for the recommended `ERG-003` static sandbox/VM preflight external/source review while keeping
  live sandbox/VM runtime work blocked.
- `make sandbox-vm-static-preflight-reviewed-packet-hash` - print the exact `sha256:...` hash to
  pass as `--reviewed-packet-hash` when normalizing real `ERG-003` external/source feedback.
- `make sandbox-vm-profile-contract-check` - validate the design-only sandbox/VM profile contract
  for future operator-supplied sandbox metadata while confirming no runtime profile loader,
  sandbox orchestration, local model invocation, or trusted-host promotion is added.
- `make sandbox-vm-preflight-contract-check` - validate the design-only sandbox/VM preflight
  contract for future platform, mount/root, network, ingress/egress, cleanup, and warning evidence
  while confirming no live preflight runner or sandbox control is added.
- `make sandbox-vm-poc-review-packet` - generate the focused sandbox/VM proof-of-concept review
  packet with boundary, profile, preflight, Mission Control handoff, Hello World artifact evidence,
  promotion evidence, command evidence, and artifact hashes.
- `make sandbox-vm-static-profile-preflight-plan-check` - validate the design-only implementation
  plan for a future static operator-managed sandbox profile fixture and read-only preflight runner
  while confirming runtime sandbox control remains blocked.
- `make sandbox-vm-static-preflight` - run the CLI-only static profile preflight over the committed
  local-preview fixture, returning safe labels and review/no-go decisions without inspecting a live
  VM/container.
- `make sandbox-vm-static-preflight-negative-transcripts` - generate observed negative transcripts
  for malformed or overclaiming static sandbox profile fixtures.
- `make sandbox-vm-static-preflight-implementation-gate` - validate the CLI-only fixture preflight
  runner boundary decision while confirming no API/MCP, governed tool, sandbox control, Mission
  Control runtime, local-model, promotion, or network expansion is approved.
- `make sandbox-vm-static-preflight-source-review-packet` - generate the focused source-review
  handoff packet for deciding whether a future read-only static profile preflight runner may be
  planned; it remains fixture/design-only and adds no runtime sandbox control.
- `make sandbox-vm-static-preflight-triage-update-check` - validate the safe committed triage-update
  checklist for a future favorable `ERG-003` external/source response while keeping live sandbox/VM
  runtime work blocked.
- `make sandbox-vm-static-preflight-response-application-record-check` - validate the process-only
  response-application record for applying a real favorable `ERG-003` external/source response
  while keeping `ERG-004`, live sandbox/VM runtime work, Mission Control runtime behavior, local
  model invocation, and new powers blocked.
- `make sandbox-vm-static-preflight-response-application-playbook-check` - validate the
  manager-owned playbook for applying a real `ERG-003` reviewer response with explicit inputs,
  command order, allowed committed files, stop conditions, and blocked runtime boundaries.
- `make sandbox-vm-static-preflight-response-application-preflight-check` - validate the checked
  bridge between the all-lane enterprise response inbox and the ERG-003 lane-local normalized
  response path before applying a real `ERG-003` reviewer disposition.
- `make project-dependency-summary-proposal-check` - validate the historical design-only
  `project.dependency.summary` proposal artifact.
- `make project-dependency-summary-implementation-plan-check` - validate the historical
  `project.dependency.summary` implementation-planning artifact.
- `make project-dependency-summary-design-review-packet` - generate the historical design-review
  packet for `project.dependency.summary`.
- `make project-dependency-summary-implementation-gate` - validate the bounded read-only
  implementation decision for `project.dependency.summary`.
- `make project-dependency-summary-source-review-bundle` - build the focused source/test/evidence
  handoff for the approved `project.dependency.summary` implementation.
- `make project-structure-summary-proposal-check` - validate the historical design-only
  `project.structure.summary` proposal artifact.
- `make project-structure-summary-implementation-plan-check` - validate the historical
  implementation-planning packet for `project.structure.summary`.
- `make project-structure-summary-implementation-gate` - validate the bounded read-only
  implementation decision for `project.structure.summary`.
- `make project-structure-summary-source-review-bundle` - build the focused source/test/evidence
  handoff for the approved `project.structure.summary` implementation.
- `make project-structure-summary-design-review-packet` - generate the historical design-review
  packet for the selected `project.structure.summary` proposal.
- `make project-docs-summary-proposal-check` - validate the current design-only
  `project.docs.summary` proposal without authorizing runtime work.
- `make project-docs-summary-implementation-plan-check` - validate the
  `project.docs.summary` implementation-planning packet without authorizing runtime work.
- `make project-docs-summary-implementation-gate` - validate the bounded read-only
  implementation decision for `project.docs.summary`.
- `make project-docs-summary-source-review-bundle` - build the focused source/test/evidence
  handoff for the approved `project.docs.summary` implementation.
- `make project-docs-summary-design-review-packet` - generate the design-review packet for the
  selected `project.docs.summary` proposal.
- `make project-language-summary-proposal-check` - validate the current design-only
  `project.language.summary` proposal without authorizing runtime work.
- `make project-language-summary-implementation-plan-check` - validate the
  `project.language.summary` implementation-planning packet without authorizing runtime work.
- `make project-language-summary-implementation-gate` - validate the bounded read-only
  implementation decision for `project.language.summary`.
- `make project-language-summary-source-review-bundle` - build the focused source/test/evidence
  handoff for the approved `project.language.summary` implementation.
- `make project-language-summary-design-review-packet` - generate the design-review packet for
  the selected `project.language.summary` proposal.
- `make project-config-summary-proposal-check` - validate the current design-only
  `project.config.summary` proposal without authorizing runtime work.
- `make project-config-summary-implementation-plan-check` - validate the
  `project.config.summary` implementation-planning packet without authorizing runtime work.
- `make project-config-summary-implementation-gate` - validate the bounded read-only
  implementation decision for `project.config.summary`.
- `make project-config-summary-source-review-bundle` - build the focused source/test/evidence
  handoff for the approved `project.config.summary` implementation.
- `make project-ci-summary-proposal-check` - validate the current design-only
  `project.ci.summary` proposal without authorizing runtime work.
- `make project-ci-summary-implementation-plan-check` - validate the
  `project.ci.summary` implementation-planning packet without authorizing runtime work.
- `make project-ci-summary-implementation-gate` - validate the bounded read-only
  implementation decision for `project.ci.summary`.
- `make project-ci-summary-source-review-bundle` - build the focused source/test/evidence
  handoff for the approved `project.ci.summary` implementation.
- `make project-ci-summary-design-review-packet` - generate the design-review packet for the
  selected `project.ci.summary` proposal.
- `make project-release-summary-proposal-check` - validate the selected
  `project.release.summary` design-only proposal without authorizing runtime work.
- `make project-release-summary-implementation-plan-check` - validate the
  `project.release.summary` implementation-planning packet without authorizing runtime work.
- `make project-release-summary-preimplementation-check` - validate the fixture/test contract and
  readiness wiring for `project.release.summary` without authorizing runtime work.
- `make project-release-summary-implementation-gate` - validate the approved limited
  read-only implementation boundary without authorizing runtime work; the current gate
  intentionally rejects `project.release.summary` manifest or runtime source until a later explicit
  implementation checkpoint replaces the preimplementation guard.
- `make project-release-summary-transition-check` - validate the canonical transition checklist for
  the later manager-owned `project.release.summary` implementation sprint without adding runtime
  behavior.
- `make project-release-summary-review-handoff-check` - validate the implemented source-review handoff
  for `project.release.summary` without claiming runtime source exists.
- `make project-release-summary-design-review-packet` - generate the design-review packet for
  the selected `project.release.summary` proposal.
- `make project-release-summary-source-review-bundle` - generate the ignored implemented
  source-review packet for `project.release.summary`.
- `make project-risk-summary-proposal-check` - validate the selected design-only
  `project.risk.summary` proposal that preceded runtime implementation.
- `make project-risk-summary-implementation-plan-check` - validate the
  `project.risk.summary` implementation-planning packet.
- `make project-risk-summary-implementation-gate` - validate the bounded read-only
  implementation boundary and current runtime wiring for `project.risk.summary`.
- `make project-risk-summary-preimplementation-check` - validate the retained fixture and strict
  non-leak expectations for `project.risk.summary`.
- `make project-risk-summary-review-handoff-check` - validate the implemented source-review and
  negative-transcript handoff for `project.risk.summary`.
- `make project-risk-summary-design-review-packet` - generate the design-review packet for the
  historical `project.risk.summary` proposal.
- `make project-risk-summary-source-review-bundle` - generate the implemented
  source-review handoff bundle for `project.risk.summary`.
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
- `make git-tag-metadata-source-review-bundle` - build the focused source/test/evidence handoff for the approved `git.show.tag_metadata` implementation.
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
captures the same-run release transcript for the review bundle, runs the filesystem contract check,
signed evidence demo, negative transcripts, operator sandbox, live-demo, and operator workbench
packets, focused v0.6 dispatch packets, consolidated packet, packet redaction scan, and docs site.
Use
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
The v1.0 RC roadmap is in
[docs/codex/v1.0-rc-roadmap.md](docs/codex/v1.0-rc-roadmap.md); it defines the remaining
local-first release-candidate phases without approving production/security-product positioning or
new governed tool powers.
The canonical v1.0 RC status map is
[docs/codex/v1.0-rc-status.md](docs/codex/v1.0-rc-status.md) and is checked with
`make v1-rc-status-check`; read it before historical v0.x/v3 packet archaeology when deciding what
is implemented, blocked, deferred, or still pending for local-preview RC.
The conservative v1.0 progress assessment is
[docs/codex/v1.0-progress-assessment.md](docs/codex/v1.0-progress-assessment.md) and is checked
with `make v1-progress-assessment`; it records rough local-preview and enterprise-readiness
completion bands without approving new runtime powers or public/security-product positioning.
The technical MVP ticket map is
[docs/codex/technical-mvp-ticket-map.md](docs/codex/technical-mvp-ticket-map.md) and is checked
with `make technical-mvp-ticket-map`; it turns the current roadmap into explicit MVP tickets for
the governed gateway foundation, read-only/Git intelligence tools, evidence/packet machinery,
operator workbench trial, Mission Control handoff, sandbox/VM readiness, trusted-host promotion,
and enterprise architecture lanes.
The technical MVP operator-trial readiness view is
[docs/codex/technical-mvp-operator-trial-readiness.md](docs/codex/technical-mvp-operator-trial-readiness.md)
and is checked with `make technical-mvp-operator-trial-readiness`; it consolidates the checked
state into the remaining hands-on local-preview operator trial commands without starting services,
calling governed tools, or approving sandbox/VM lifecycle control.
The development efficiency status is
[docs/codex/development-efficiency-status.md](docs/codex/development-efficiency-status.md)
and is checked with `make development-efficiency-status`; it combines validation-decision,
release-check profile, technical MVP readiness, and enterprise-current-checkpoint evidence into one
small decision view without replacing `make release-check` or `make review-candidate`.
The v1.0 RC feature-freeze decision is
[docs/codex/v1.0-rc-feature-freeze.md](docs/codex/v1.0-rc-feature-freeze.md) and is checked with
`make v1-rc-feature-freeze`; it blocks new manifests, executors, policy powers, MCP/API behavior,
UI runtime controls, and product-positioning expansion unless a post-RC decision explicitly
unfreezes a lane.
The v1.0 external review prompt is
[docs/codex/v1.0-rc-external-review-prompt.md](docs/codex/v1.0-rc-external-review-prompt.md) and is
checked with `make v1-rc-external-review-prompt-check`; it is the current prompt to send with the
compact v1.0 RC packet for GPT 5.5 Pro / Very High or human review.
The v1.0 final handoff map is
[docs/codex/v1.0-rc-final-handoff.md](docs/codex/v1.0-rc-final-handoff.md) and is checked with
`make v1-rc-final-handoff-check`; it records current go/no-go status, packet order, required
commands, and what the handoff does and does not prove.
The v1.0 post-review triage map is
[docs/codex/v1.0-rc-post-review-triage.md](docs/codex/v1.0-rc-post-review-triage.md) and is
checked with `make v1-rc-post-review-triage-check`; it records how to normalize external feedback,
create findings, and preserve the feature freeze after review.
The v1.0 operator quickstart is
[docs/codex/v1.0-operator-quickstart.md](docs/codex/v1.0-operator-quickstart.md) and is checked
with `make v1-operator-quickstart-check`; it is the current zero-to-one local demo path from
preflight through cleanup.
The v1.0 operator trial checklist is
[docs/codex/v1.0-operator-trial-checklist.md](docs/codex/v1.0-operator-trial-checklist.md) and is
checked with `make v1-operator-trial-checklist-check`; it turns the quickstart into a repeatable
pass/fail local trial record without approving runtime powers or product-positioning claims.
The v1.0 operator trial record is
[docs/codex/v1.0-operator-trial-record.md](docs/codex/v1.0-operator-trial-record.md), generated
with `make v1-operator-trial-record`, and checked with `make v1-operator-trial-record-check`; it
captures the current checklist-style handoff state, enterprise next-action state, and waiting-room
counts as ignored local evidence without starting services, calling governed tools, normalizing
responses, closing lanes, or approving public/security-product positioning.
The v1.0 workbench/evidence closure map is
[docs/codex/v1.0-workbench-evidence-closure.md](docs/codex/v1.0-workbench-evidence-closure.md)
and is checked with `make v1-workbench-evidence-check`; it ties the local review console, Agent Run
evidence, approvals, audit, signed evidence, demo artifacts, and review packets into one
operator-facing evidence story.
The v1.0 assurance closure map is
[docs/codex/v1.0-assurance-closure.md](docs/codex/v1.0-assurance-closure.md) and is checked with
`make v1-assurance-closure-check`; it summarizes local-preview findings, accepted risks, closure
matrix evidence, and remaining external-pending rows without claiming production or external closure.
The v1.0 RC readiness gate is
[docs/codex/v1.0-rc-readiness-gate.md](docs/codex/v1.0-rc-readiness-gate.md) and is checked with
`make v1-rc-readiness`; use `make v1-rc-packet` for the compact ignored handoff packet.
`make review-candidate` regenerates that compact packet as part of the broader local handoff gate so
the v1.0 RC status, workbench evidence map, Mission Control handoff, sandbox-promotion evidence
contract, and artifact hashes are refreshed together.
The enterprise readiness runway is
[docs/codex/enterprise-readiness-runway.md](docs/codex/enterprise-readiness-runway.md) and is
checked with `make enterprise-readiness-runway-check`; it defines the post-v1 path through Mission
Control display integration, sandbox/VM proof of concept, trusted-host promotion, production
IAM/storage/audit architecture, SIEM-shaped exports, and compliance mapping support while
keeping all enterprise powers design-only today.
The enterprise readiness gap matrix is
[docs/codex/enterprise-readiness-gap-matrix.md](docs/codex/enterprise-readiness-gap-matrix.md),
checked with `make enterprise-readiness-gap-matrix-check`; it records which enterprise lanes are
closed only for local preview, planning-only, external-review-required, or blocked, and which
production/security claims remain unavailable.
The enterprise progress model is
[docs/codex/enterprise-progress-model.md](docs/codex/enterprise-progress-model.md), checked with
`make enterprise-progress-model`; it translates the current v1.0 and enterprise checkpoints into a
conservative progress ladder while keeping runtime expansion, live VM/container work, Mission
Control execution authority, trusted-host promotion, and public/security-product positioning
blocked.
The enterprise dependency ladder is
[docs/codex/enterprise-dependency-ladder.md](docs/codex/enterprise-dependency-ladder.md), checked
with `make enterprise-dependency-ladder`; it keeps `ERG-003`, `ERG-002`, later live sandbox/VM
planning, Mission Control display/import planning, and enterprise architecture lanes in their
allowed order without promoting any lane by hand.
The enterprise transition map is
[docs/codex/enterprise-transition-map.md](docs/codex/enterprise-transition-map.md), checked with
`make enterprise-transition-map`; it records the only allowed post-review next states for `ERG-003`,
`ERG-002`, `ERG-004`, and later enterprise lanes while keeping runtime authority, public/security-
product positioning, and new power classes blocked.
The enterprise north-star roadmap is
[docs/codex/enterprise-north-star-roadmap.md](docs/codex/enterprise-north-star-roadmap.md),
checked with `make enterprise-north-star-roadmap`; it is the operator-facing read-first map from
v1.0 local-preview RC through `ERG-003`, `ERG-002`, Stage 2 sandbox/VM, Mission Control display,
and enterprise architecture lanes without approving runtime powers.
The enterprise operator next-action summary is
[docs/codex/enterprise-operator-next-action.md](docs/codex/enterprise-operator-next-action.md),
checked with `make enterprise-operator-next-action`; it reports the current allowed operator step
from the checked enterprise state, pointing to `make enterprise-review-send-refresh` or
`make enterprise-response-intake-refresh` as appropriate, without recording review, normalizing
responses, closing lanes, or approving runtime powers.
The enterprise external-review queue is
[docs/codex/enterprise-external-review-queue.md](docs/codex/enterprise-external-review-queue.md),
checked with `make enterprise-external-review-queue-check`; it orders the post-RC review lanes,
points to each current packet and response-intake path, names `ERG-003` static sandbox/VM preflight
as the next recommended review, and keeps every queued lane runtime-disabled until a later committed
decision record changes that posture.
The compact next-review handoff is
[docs/codex/enterprise-next-review-handoff.md](docs/codex/enterprise-next-review-handoff.md),
generated with `make enterprise-next-review-handoff`; it points to the exact `ERG-003` packet files
to send and the fail-closed response path to use afterward.
The next-review ready check is
[docs/codex/enterprise-next-review-ready-check.md](docs/codex/enterprise-next-review-ready-check.md),
checked with `make enterprise-next-review-ready-check`; it verifies the `ERG-003` packet, handoff,
reviewed-packet hash helper, and closure-gate waiting state before operator handoff.
The enterprise review send-readiness summary is
[docs/codex/enterprise-review-send-readiness.md](docs/codex/enterprise-review-send-readiness.md),
checked with `make enterprise-review-send-readiness`; it summarizes packet handoff readiness across
enterprise review lanes while keeping implementation approval, runtime behavior, and lane closure
separate.
The enterprise current checkpoint is
[docs/codex/enterprise-current-checkpoint.md](docs/codex/enterprise-current-checkpoint.md),
checked with `make enterprise-current-checkpoint`; it gives the compact current operator truth:
v1.0 RC artifacts are ready to regenerate, `ERG-003`/`ERG-002` are the send set, no normalized
responses are present, and runtime expansion remains blocked.
The enterprise status export is
[docs/codex/enterprise-status-export.md](docs/codex/enterprise-status-export.md), generated with
`make enterprise-status-export` and checked with `make enterprise-status-export-check`; it writes a
display-only JSON/Markdown snapshot for operator dashboards and Mission Control display/import
experiments while keeping Mission Control runtime behavior, live VM/container inspection, sandbox
orchestration, SIEM adapter behavior, compliance automation, public/security-product positioning,
and new governed tool powers blocked.
The Mission Control enterprise status import contract is
[docs/codex/mission-control-enterprise-status-import-contract.md](docs/codex/mission-control-enterprise-status-import-contract.md),
checked with `make mission-control-enterprise-status-import-check`; it defines how a future Mission
Control importer may display the enterprise status export as non-authoritative status while keeping
execution, policy, approval, audit, lane closure, and runtime authority with Ithildin.
The Mission Control enterprise status fixtures are
[docs/codex/mission-control-enterprise-status-fixtures.md](docs/codex/mission-control-enterprise-status-fixtures.md),
generated with `make mission-control-enterprise-status-fixtures` and checked with
`make mission-control-enterprise-status-fixtures-check`; they provide one valid and twelve negative
display/import payloads for future Mission Control tests without calling Mission Control or
approving runtime importer behavior.
The Mission Control enterprise status acceptance matrix is
[docs/codex/mission-control-enterprise-status-acceptance-matrix.md](docs/codex/mission-control-enterprise-status-acceptance-matrix.md),
checked with `make mission-control-enterprise-status-acceptance-matrix-check`; it maps those
enterprise status fixtures to expected display-only importer states, safe rejection labels, warning
chips, and forbidden displays while keeping Mission Control runtime behavior blocked.
The Mission Control enterprise status reference validator is
[docs/codex/mission-control-enterprise-status-reference-validator.md](docs/codex/mission-control-enterprise-status-reference-validator.md),
checked with `make mission-control-enterprise-status-reference-validator`; it validates the
enterprise status fixture pack as a display-only oracle for future Mission Control tests without
calling Mission Control, calling Ithildin APIs, approving callbacks, or approving runtime importer
behavior.
The dual-review handoff is
[docs/codex/enterprise-dual-review-handoff.md](docs/codex/enterprise-dual-review-handoff.md),
generated with `make enterprise-dual-review-handoff`; it points to the current `ERG-003` and
`ERG-002` packets and their response paths without closing either lane or approving runtime powers.
The dual-review outbox is
[docs/codex/enterprise-dual-review-outbox.md](docs/codex/enterprise-dual-review-outbox.md),
generated with `make enterprise-dual-review-outbox`; it copies the current `ERG-003` and `ERG-002`
send-ready files into one ignored outbox with artifact hashes while still not recording review or
closing either lane.
The enterprise review send manifest is
[docs/codex/enterprise-review-send-manifest.md](docs/codex/enterprise-review-send-manifest.md),
generated with `make enterprise-review-send-manifest`; it records the current send set, outbox
hash-manifest pointer, lane-specific response path, and blocked boundaries while still not
recording review, normalizing responses, or closing either lane.
The enterprise review send checklist is
[docs/codex/enterprise-review-send-checklist.md](docs/codex/enterprise-review-send-checklist.md),
checked with `make enterprise-review-send-checklist`; it gives the operator the exact current
attachments, prompt files, response inbox paths, and post-response commands for the `ERG-003` and
`ERG-002` send set while still not recording review, normalizing responses, or closing either lane.
The enterprise review send quickstart is
[docs/codex/enterprise-review-send-quickstart.md](docs/codex/enterprise-review-send-quickstart.md),
generated with `make enterprise-review-send-quickstart`; it gives the operator a one-page generated
index over the current `ERG-003` and `ERG-002` send directories, prompt files, hash manifests, and
raw-response placeholders while still not recording review, normalizing responses, or closing either
lane.
The enterprise review submission prompt is
[docs/codex/enterprise-review-submission-prompt.md](docs/codex/enterprise-review-submission-prompt.md),
generated with `make enterprise-review-submission-prompt`; it gives the operator paste-ready
instructions for separate `ERG-003` and `ERG-002` review requests while still not recording review,
normalizing responses, or closing either lane.
The enterprise review send receipt template is
[docs/codex/enterprise-review-send-receipt-template.md](docs/codex/enterprise-review-send-receipt-template.md),
generated with `make enterprise-review-send-receipt-template`; it gives the operator a local ignored
template for tying sent-thread metadata and raw-response paths back to the generated packet hashes
after the human send step while still not recording review, normalizing responses, writing raw
responses, or closing either lane.
The enterprise review send package is
[docs/codex/enterprise-review-send-package.md](docs/codex/enterprise-review-send-package.md),
generated with `make enterprise-review-send-package`; it gives the operator a compact generated
index over the current `ERG-003` and `ERG-002` prompts, lane attachment manifests, hash manifests,
submission prompt, send receipt template, and response inbox paths while still not recording review,
normalizing responses, writing raw responses, or closing either lane.
The enterprise review send session record is
[docs/codex/enterprise-review-send-session-record.md](docs/codex/enterprise-review-send-session-record.md),
generated with `make enterprise-review-send-session-record`; it gives the operator a local
non-authoritative scaffold for recording the human send event against the current package hashes,
lane prompts, and raw-response landing pads while still not recording review, normalizing
responses, writing response files, or closing either lane.
The enterprise review handoff drill is
[docs/codex/enterprise-review-handoff-drill.md](docs/codex/enterprise-review-handoff-drill.md),
generated with `make enterprise-review-handoff-drill`; it ties together the outbox, send manifest,
response inbox, response status board, and fixture-only intake drill so the operator can practice
the send/receive sequence without recording review, normalizing real responses, or closing lanes.
The dual-response inbox is
[docs/codex/enterprise-dual-response-inbox.md](docs/codex/enterprise-dual-response-inbox.md),
generated with `make enterprise-dual-response-inbox`; it creates ignored raw-response placeholders
and exact normalization, dry-run, and closure-gate commands for `ERG-003` and `ERG-002` while still
not normalizing responses, mutating findings, or closing either lane.
The dual-response readiness summary is
[docs/codex/enterprise-dual-response-readiness.md](docs/codex/enterprise-dual-response-readiness.md),
checked with `make enterprise-dual-response-readiness`; it reports whether normalized review
responses are present and which lane-specific dry-run command should run next.
The enterprise response waiting room is
[docs/codex/enterprise-response-waiting-room.md](docs/codex/enterprise-response-waiting-room.md),
checked with `make enterprise-response-waiting-room`; it reports whether ignored `ERG-003` and
`ERG-002` raw-response files are still placeholders or appear ready for paste preflight without
normalizing responses, recording review, or closing either lane.
The enterprise response status board is
[docs/codex/enterprise-response-status-board.md](docs/codex/enterprise-response-status-board.md),
checked with `make enterprise-response-status-board`; it aggregates normalized-response state for
all enterprise review lanes without recording review, mutating findings, or closing lanes.
The enterprise response command matrix is
[docs/codex/enterprise-response-command-matrix.md](docs/codex/enterprise-response-command-matrix.md),
checked with `make enterprise-response-command-matrix`; it records the operator command sequence for
each enterprise response lane, including generated raw-response path, normalizer, dry-run, closure
gate, response kit, and maximum allowed transition, while still not recording review or closing any
lane.
The enterprise response application protocol is
[docs/codex/enterprise-response-application-protocol.md](docs/codex/enterprise-response-application-protocol.md),
checked with `make enterprise-response-application-protocol`; it gives the operator the
fail-closed sequence for turning future reviewer responses into lane-specific dry-run, closure-gate,
and committed decision-record work without approving runtime expansion.
The enterprise response application rehearsal is
[docs/codex/enterprise-response-application-rehearsal.md](docs/codex/enterprise-response-application-rehearsal.md),
checked with `make enterprise-response-application-rehearsal`; it proves the current `ERG-003` and
`ERG-002` response-application preflight path is wired before real reviewer responses arrive,
without normalizing responses, writing response files, recording review, or closing lanes.
The enterprise response intake quickstart is
[docs/codex/enterprise-response-intake-quickstart.md](docs/codex/enterprise-response-intake-quickstart.md),
checked with `make enterprise-response-intake-quickstart`; it gives the operator the compact
`ERG-003` and `ERG-002` raw-response paths, normalizer commands, lane dry-runs, closure gates, and
stop conditions for after reviewer responses arrive without recording review or approving runtime
expansion. Use `make enterprise-response-intake-refresh` to regenerate the ignored receive-side
artifacts and rerun the receive-side checks in one command.
The enterprise response paste preflight is
[docs/codex/enterprise-response-paste-preflight.md](docs/codex/enterprise-response-paste-preflight.md),
checked with `make enterprise-response-paste-preflight`; it checks pasted `ERG-003` and `ERG-002`
raw responses before normalization without writing normalized responses, recording review, or
closing enterprise lanes.
The enterprise handoff consistency gate is
[docs/codex/enterprise-handoff-consistency.md](docs/codex/enterprise-handoff-consistency.md),
checked with `make enterprise-handoff-consistency-check`; it keeps the current `ERG-003` and
`ERG-002` send/receive docs aligned to the dual-response inbox, receipt template, and paste
preflight flow without recording review, normalizing responses, or closing either lane.
The enterprise review send preflight is
[docs/codex/enterprise-review-send-preflight.md](docs/codex/enterprise-review-send-preflight.md),
checked with `make enterprise-review-send-preflight`; it gives the operator one final pre-send
status across the current send artifacts, response landing pad, handoff drill, response state, and
handoff consistency gate without sending packets, recording review, or closing either lane. Use
`make enterprise-review-send-refresh` to regenerate the ignored send artifacts and run that
preflight in one command.
The sandbox/control-plane readiness map is
[docs/codex/enterprise-sandbox-control-plane-readiness.md](docs/codex/enterprise-sandbox-control-plane-readiness.md)
and is checked with `make enterprise-sandbox-control-plane-readiness-check`; it links Mission
Control display planning, sandbox/VM static preflight, live sandbox/VM POC decision evidence, and
trusted-host promotion into one status source while keeping runtime sandbox, local-model, promotion,
SIEM, compliance, and security-product claims blocked.
The post-RC decision gate is
[docs/codex/post-rc-decision-gate.md](docs/codex/post-rc-decision-gate.md) and is checked with
`make post-rc-decision-gate`; it requires a written decision record, scope, forbidden scope,
review evidence, tests, accepted-risk impact, tool-count impact, and go/no-go outcome before any
frozen lane can move beyond documentation or planning.
The production identity and storage architecture packet is
[docs/codex/production-identity-storage-architecture.md](docs/codex/production-identity-storage-architecture.md)
and is checked with `make production-identity-storage-architecture-check`; it defines the future
`ERG-006`/`ERG-007` identity, tenancy, storage, migration, retention, backup/restore, and evidence
questions while keeping production IAM, runtime Postgres, remote admin use, and custody-grade audit
claims blocked.
Generate the production identity and storage disposition packet with
`make production-identity-storage-disposition-packet`; it asks whether the current ERG-006/ERG-007
architecture evidence is coherent enough to continue planning while keeping production identity,
not runtime Postgres, database migrations, backup/restore runtime behavior, retention enforcement,
hosted control plane, custody-grade audit claims, compliance automation, and public/security-product
positioning blocked.
The external-review launch bundle is
[docs/codex/production-identity-storage-external-review-bundle.md](docs/codex/production-identity-storage-external-review-bundle.md)
and is generated with `make production-identity-storage-external-review-bundle`; it consolidates
the architecture/disposition packet, response-intake template, fail-closed closure gate,
response-dry-run evidence, queue status, and command evidence into one reviewer handoff while
keeping `ERG-006`/`ERG-007` planning-only.
The production identity and storage external response intake template is in
[docs/codex/production-identity-storage-external-response-intake.md](docs/codex/production-identity-storage-external-response-intake.md)
and is checked with `make production-identity-storage-external-response-intake-check`; it defines
the `EXT-PROD-IAM-STORAGE-###` finding namespace and `production-identity-storage` normalizer
command for recording reviewer responses without mutating findings, closing `ERG-006`/`ERG-007`,
or approving production identity/storage runtime behavior.
The production identity and storage disposition closure gate is in
[docs/codex/production-identity-storage-disposition-closure-gate.md](docs/codex/production-identity-storage-disposition-closure-gate.md)
and is checked with `make production-identity-storage-disposition-closure-check`; it keeps
`ERG-006` and `ERG-007` planning-only unless normalized source-level response evidence supports
architecture continuation and contains no critical/high findings.
The production identity and storage response dry run is in
[docs/codex/production-identity-storage-response-dry-run.md](docs/codex/production-identity-storage-response-dry-run.md)
and is checked with `make production-identity-storage-response-dry-run`; it temporarily exercises
favorable and unfavorable normalized-response fixtures while restoring the ignored response path and
without closing `ERG-006`/`ERG-007` or approving implementation planning.
The production identity and storage response kit is in
[docs/codex/production-identity-storage-response-kit.md](docs/codex/production-identity-storage-response-kit.md)
and is generated with `make production-identity-storage-response-kit`; it packages response-intake
guidance, normalized-response examples, closure commands, command evidence, and artifact hashes for
real reviewer feedback without closing `ERG-006` or `ERG-007`, approving implementation planning,
or approving runtime identity/storage behavior.
The SIEM export adapter architecture packet is
[docs/codex/siem-export-adapter-architecture.md](docs/codex/siem-export-adapter-architecture.md)
and is checked with `make siem-export-adapter-architecture-check`; it defines future adapter
profile, schema compatibility, delivery, retry, backpressure, signing, diagnostics, and review
questions while keeping SIEM adapter runtime behavior, hosted telemetry, remote delivery, and
security-operations control-plane claims blocked.
Generate the SIEM export adapter disposition packet with
`make siem-export-adapter-disposition-packet`; it asks whether the current ERG-008 architecture
evidence is coherent enough to continue planning while adapter runtime behavior, hosted telemetry,
remote delivery, custody-grade audit claims, external notarization, immutable storage, compliance
automation, and public/security-product positioning remain blocked.
The SIEM export adapter external-review launch bundle is
[docs/codex/siem-export-adapter-external-review-bundle.md](docs/codex/siem-export-adapter-external-review-bundle.md)
and is generated with `make siem-export-adapter-external-review-bundle`; it consolidates the
disposition packet, architecture evidence, intake/closure/dry-run docs, queue status, and command
evidence for ERG-008 review while keeping SIEM adapter runtime behavior blocked.
The SIEM export adapter external response intake template is in
[docs/codex/siem-export-adapter-external-response-intake.md](docs/codex/siem-export-adapter-external-response-intake.md)
and is checked with `make siem-export-adapter-external-response-intake-check`; it defines the
`EXT-SIEM-ADAPTER-###` finding namespace and `siem-export-adapter` normalizer command for recording
reviewer responses without mutating findings, closing `ERG-008`, or approving SIEM adapter runtime
behavior.
The SIEM export adapter disposition closure gate is in
[docs/codex/siem-export-adapter-disposition-closure-gate.md](docs/codex/siem-export-adapter-disposition-closure-gate.md)
and is checked with `make siem-export-adapter-disposition-closure-check`; it keeps `ERG-008`
planning-only unless normalized source-level response evidence supports architecture continuation
and contains no critical/high findings.
The SIEM export adapter response dry run is in
[docs/codex/siem-export-adapter-response-dry-run.md](docs/codex/siem-export-adapter-response-dry-run.md)
and is checked with `make siem-export-adapter-response-dry-run`; it temporarily exercises favorable
and unfavorable normalized-response fixtures while restoring the ignored response path and without
closing `ERG-008` or approving implementation planning.
The SIEM export adapter response kit is in
[docs/codex/siem-export-adapter-response-kit.md](docs/codex/siem-export-adapter-response-kit.md)
and is generated with `make siem-export-adapter-response-kit`; it packages response-intake
guidance, normalized-response examples, closure commands, command evidence, and artifact hashes for
real reviewer feedback without closing `ERG-008`, approving implementation planning, or approving
runtime SIEM adapter behavior.
The compliance mapping architecture packet is
[docs/codex/compliance-mapping-architecture.md](docs/codex/compliance-mapping-architecture.md)
and is checked with `make compliance-mapping-architecture-check`; it defines future framework
scope, mapping-template, evidence allowlist/denylist, operator responsibility, legal-review, and
accepted-risk questions while keeping compliance automation, legal conclusions, automated
certification, and regulated-industry compliance claims blocked.
Generate the compliance mapping disposition packet with
`make compliance-mapping-disposition-packet`; it asks whether the current ERG-009 architecture
evidence is coherent enough to continue planning while runtime compliance mapping, legal advice,
automated certification, regulated-industry compliance claims, custody claims, and
public/security-product positioning remain blocked.
Generate the consolidated compliance mapping external-review bundle with
`make compliance-mapping-external-review-bundle`; validate its wiring with
`make compliance-mapping-external-review-bundle-check`. The bundle packages the ERG-009 disposition
packet, architecture contracts, response-intake and closure gates, dry-run evidence, queue status,
command evidence, and artifact hashes without closing ERG-009 or approving runtime compliance
mapping.
The compliance mapping external response intake template is in
[docs/codex/compliance-mapping-external-response-intake.md](docs/codex/compliance-mapping-external-response-intake.md)
and is checked with `make compliance-mapping-external-response-intake-check`; it defines the
`EXT-COMPLIANCE-MAPPING-###` finding namespace and `compliance-mapping` normalizer command for
recording reviewer responses without mutating findings, closing `ERG-009`, or approving runtime
compliance mapping, compliance automation, legal advice, automated certification, or
regulated-industry compliance claims.
The fail-closed compliance mapping disposition closure gate is in
[docs/codex/compliance-mapping-disposition-closure-gate.md](docs/codex/compliance-mapping-disposition-closure-gate.md)
and is checked with `make compliance-mapping-disposition-closure-check`; it keeps `ERG-009`
planning-only unless normalized source-level response evidence supports continued architecture
planning and contains no critical/high findings.
The compliance mapping response dry run is in
[docs/codex/compliance-mapping-response-dry-run.md](docs/codex/compliance-mapping-response-dry-run.md)
and is checked with `make compliance-mapping-response-dry-run`; it temporarily exercises favorable
and unfavorable normalized-response fixtures, restores the ignored response path, and does not
record external review, mutate findings, close `ERG-009`, or approve implementation/runtime
compliance mapping.
The compliance mapping response kit is in
[docs/codex/compliance-mapping-response-kit.md](docs/codex/compliance-mapping-response-kit.md)
and is generated with `make compliance-mapping-response-kit`; it packages response-intake
guidance, normalized-response examples, closure commands, command evidence, and artifact hashes for
real reviewer feedback without closing `ERG-009`, approving implementation planning, or approving
runtime compliance mapping, compliance automation, legal advice, automated certification,
regulated-industry compliance claims, or custody-grade audit claims; those claims remain blocked.
Use the post-RC decision record template at
[docs/codex/post-rc-decision-record-template.md](docs/codex/post-rc-decision-record-template.md),
checked with `make post-rc-decision-record-template-check`, when drafting any such future decision.
Use the example decision records at
[docs/codex/post-rc-decision-record-examples.md](docs/codex/post-rc-decision-record-examples.md),
checked with `make post-rc-decision-record-examples-check`, as the baseline shape for
Mission Control planning-only, sandbox/VM no-go, and post-freeze capability no-go decisions; these
post-RC decision record examples are sample records, not runtime approvals.
Use the post-RC decision register at
[docs/codex/post-rc-decision-register.md](docs/codex/post-rc-decision-register.md), checked with
`make post-rc-decision-register-check`, as the current source of truth for which enterprise lanes
are planning-only, no-go, or still blocked.
The public/security-product positioning decision intake is in
[docs/codex/public-security-product-positioning-decision-intake.md](docs/codex/public-security-product-positioning-decision-intake.md),
checked with `make public-security-product-positioning-decision-intake-check`; it records
`PRD-PUBLIC-POSITIONING-001` as a no-go lane and keeps broad public/security-product,
production/security/compliance, sandbox, EDR/MDM, SIEM custody, compliance automation, hosted MCP,
runtime Postgres, production identity, and hosted telemetry claims blocked unless a later committed
decision record, evidence packet, and external/source review explicitly change that posture.
The fail-closed public/security-product positioning decision closure gate is in
[docs/codex/public-security-product-positioning-decision-closure-gate.md](docs/codex/public-security-product-positioning-decision-closure-gate.md),
checked with `make public-security-product-positioning-decision-closure-check`; it keeps `ERG-010`
blocked unless normalized source-level or packet-and-source review evidence supports a future
claim-specific decision record and contains no critical/high findings, and it still does not approve
public/security-product positioning or production/security/compliance positioning.
Generate the consolidated public positioning external-review bundle with
`make public-positioning-external-review-bundle`; validate its wiring with
`make public-positioning-external-review-bundle-check`. The bundle packages the ERG-010 intake,
closure gates, current no-go decision evidence, accepted-risk context, enterprise queue status,
command evidence, and artifact hashes without closing ERG-010 or approving public/security-product
positioning.
Generate the public/security-product positioning response kit with
`make public-security-product-positioning-response-kit`; validate its wiring with
`make public-security-product-positioning-response-kit-check`. The kit packages response-intake
guidance, normalized response examples, closure triage commands, boundary status, and command
evidence for converting real reviewer feedback into a later claim-decision record without closing
ERG-010 or approving public/security-product positioning.
The residual docs/claims public-preview disposition closure gate is in
[docs/codex/docs-claims-public-preview-disposition-closure-gate.md](docs/codex/docs-claims-public-preview-disposition-closure-gate.md),
checked with `make docs-claims-public-preview-disposition-closure-check`; it keeps legacy
docs/claims rows external-pending unless normalized packet-only or stronger review evidence supports
local-preview wording closure, and it still does not approve capability expansion, public/security-
product positioning, runtime behavior, or new governed tool powers.
The Mission Control display integration proposal is
[docs/codex/mission-control-display-integration-proposal.md](docs/codex/mission-control-display-integration-proposal.md)
and is checked with `make mission-control-display-integration-proposal-check`; it keeps the first
cross-project step to file/import display of Ithildin evidence labels, hashes, warnings, and links,
with Mission Control explicitly outside execution, policy, approval, audit, local-model, VM,
sandbox-orchestration, and trusted-host promotion authority.
The Mission Control display importer implementation plan is
[docs/codex/mission-control-display-importer-plan.md](docs/codex/mission-control-display-importer-plan.md)
and is checked with `make mission-control-display-importer-plan-check`; it defines the future
file/import validation order, display states, warning chips, and negative fixture coverage while
keeping runtime importer implementation blocked.
The Mission Control display decision intake is
[docs/codex/mission-control-display-decision-intake.md](docs/codex/mission-control-display-decision-intake.md)
and is checked with `make mission-control-display-decision-intake-check`; it records the exact
preconditions, allowed outcomes, negative evidence, and blocked authority claims before any future
Mission Control display/importer implementation decision may be recorded.
The Mission Control-side handoff plan is
[docs/codex/mission-control-side-handoff-plan.md](docs/codex/mission-control-side-handoff-plan.md)
and is checked with `make mission-control-side-handoff-plan-check`; it is the paste-ready
Mission Control repository work order for a future display-only importer, with explicit inputs,
validation stages, tests, evidence, stop conditions, and no authority transfer.
The Mission Control integration implementation ticket is
[docs/codex/mission-control-integration-implementation-ticket.md](docs/codex/mission-control-integration-implementation-ticket.md)
and is checked with `make mission-control-integration-implementation-ticket-check`; it converts the
Ithildin packet/schema/fixture evidence into a concrete Mission Control repository task list while
keeping the future importer display-only and local-file/import-only.
The Ithildin-side handoff schema contract is
[docs/codex/mission-control-handoff-schema-contract.md](docs/codex/mission-control-handoff-schema-contract.md)
and is checked with `make mission-control-handoff-schema-contract-check`; it validates the current
`mission-control-handoff.json` seed shape, required false authority flags, display allowlist,
hidden-field denylist, relative attachment paths, and no-runtime/no-new-powers boundary.
The Mission Control handoff negative fixture plan is
[docs/codex/mission-control-handoff-negative-fixtures.md](docs/codex/mission-control-handoff-negative-fixtures.md)
and is checked with `make mission-control-handoff-negative-fixtures-check`; it mutates the current
handoff seed in memory and verifies that schema mismatches, live-integration claims, authority
overclaims, unsafe paths, missing warning/denylist fields, raw contents, and raw prompts are
rejected before any Mission Control importer is implemented.
The Mission Control handoff fixture pack is
[docs/codex/mission-control-handoff-fixture-pack.md](docs/codex/mission-control-handoff-fixture-pack.md)
and is generated with `make mission-control-handoff-fixture-pack`; it writes concrete positive and
negative JSON fixtures under `var/review-packets/v3/mission-control-handoff-fixtures/` for future
Mission Control importer tests without approving runtime importer behavior or callbacks into
Ithildin.
The Mission Control importer acceptance matrix is
[docs/codex/mission-control-importer-acceptance-matrix.md](docs/codex/mission-control-importer-acceptance-matrix.md)
and is checked with `make mission-control-importer-acceptance-matrix-check`; it maps the generated
positive and negative handoff fixtures to expected display-only importer states, warning labels,
safe rejection reasons, and forbidden fields while keeping runtime importer behavior blocked.
The Mission Control handoff reference validator is
[docs/codex/mission-control-handoff-reference-validator.md](docs/codex/mission-control-handoff-reference-validator.md)
and is checked with `make mission-control-handoff-reference-validator`; it validates the generated
fixture pack as a display-only oracle for future Mission Control tests without calling Mission
Control, calling Ithildin APIs, approving callbacks, or approving runtime importer behavior.
The Mission Control enterprise status acceptance matrix is
[docs/codex/mission-control-enterprise-status-acceptance-matrix.md](docs/codex/mission-control-enterprise-status-acceptance-matrix.md)
and is checked with `make mission-control-enterprise-status-acceptance-matrix-check`; it maps the
enterprise status export fixtures to expected display-only importer states and safe rejection labels
without approving Mission Control runtime importer behavior.
The Mission Control enterprise status reference validator is
[docs/codex/mission-control-enterprise-status-reference-validator.md](docs/codex/mission-control-enterprise-status-reference-validator.md)
and is checked with `make mission-control-enterprise-status-reference-validator`; it gives the
future Mission Control importer a stable display-only oracle for accepting `MC-STATUS-VALID-001`
and rejecting `MC-STATUS-NEG-001` through `MC-STATUS-NEG-010`.
Generate the focused Mission Control display review packet with
`make mission-control-display-review-packet`; it bundles the display proposal, handoff schema,
negative fixtures, Hello World seed evidence, command evidence, and artifact hashes for future
Mission Control-side planning while keeping runtime importer behavior blocked.
Generate the Mission Control display disposition packet with
`make mission-control-display-disposition-packet`; it asks whether the current ERG-002 evidence is
coherent enough to continue design-only Mission Control-side planning, while keeping runtime
importer behavior, execution authority, policy authority, approval authority, audit authority, local
model invocation, sandbox orchestration, trusted-host promotion, SIEM adapter behavior, and new
power classes blocked.
Generate the Mission Control display external-review launch bundle with
`make mission-control-display-external-review-bundle`; it consolidates the display review packet,
disposition packet, integration readiness packet, schema/handoff contracts, negative fixtures,
response intake, fail-closed closure gate, response dry run, enterprise queue status, and command
evidence into one handoff while keeping `ERG-002` planning-only and runtime importer behavior
blocked.
The Mission Control display external response intake template is
[docs/codex/mission-control-display-external-response-intake.md](docs/codex/mission-control-display-external-response-intake.md)
and is checked with `make mission-control-display-external-response-intake-check`; it defines the
`EXT-MC-DISPLAY-###` finding namespace, allowed reviewer-response outcomes, and the rule that a
favorable response does not close `ERG-002` or approve runtime importer behavior.
The Mission Control display disposition closure gate is in
[docs/codex/mission-control-display-disposition-closure-gate.md](docs/codex/mission-control-display-disposition-closure-gate.md)
and is checked with `make mission-control-display-disposition-closure-check`; it keeps `ERG-002`
planning-only unless normalized source-level response evidence explicitly supports design-only
continuation and contains no critical/high findings.
The Mission Control display response dry run is in
[docs/codex/mission-control-display-response-dry-run.md](docs/codex/mission-control-display-response-dry-run.md)
and is checked with `make mission-control-display-response-dry-run`; it temporarily exercises
favorable and unfavorable normalized-response fixtures while restoring the ignored response path and
without closing `ERG-002` or approving runtime importer behavior.
The Mission Control display response kit is in
[docs/codex/mission-control-display-response-kit.md](docs/codex/mission-control-display-response-kit.md)
and is generated with `make mission-control-display-response-kit`; it packages response-intake
guidance, normalized-response examples, closure commands, boundary status, command evidence, and
artifact hashes without recording review, closing `ERG-002`, or approving runtime importer
behavior.
The Mission Control display response-application preflight is in
[docs/codex/mission-control-display-response-application-preflight.md](docs/codex/mission-control-display-response-application-preflight.md)
and is checked with `make mission-control-display-response-application-preflight-check`; it keeps
the all-lane raw response inbox path and ERG-002 normalized response path aligned before a real
reviewer response is used, without normalizing responses, closing `ERG-002`, or approving Mission
Control runtime importer behavior.
The Mission Control display response-application record is in
[docs/codex/mission-control-display-response-application-record.md](docs/codex/mission-control-display-response-application-record.md)
and is checked with `make mission-control-display-response-application-record-check`; it records the
manager-owned checklist for applying a real favorable ERG-002 reviewer response without closing
`ERG-002` by itself or approving runtime importer behavior. The companion playbook is in
[docs/codex/mission-control-display-response-application-playbook.md](docs/codex/mission-control-display-response-application-playbook.md)
and is checked with `make mission-control-display-response-application-playbook-check`; it defines
the command order, allowed committed files, and stop conditions for using a real response to support
a later design-only decision record.
The Mission Control display next-review ready check is in
[docs/codex/mission-control-display-next-review-ready-check.md](docs/codex/mission-control-display-next-review-ready-check.md)
and is checked with `make mission-control-display-next-review-ready-check`; it verifies the ERG-002
packet bundle, readiness packet, response kit, dry run, and fail-closed closure posture are ready
for operator handoff without closing `ERG-002` or approving Mission Control runtime authority.
The Mission Control display decision-record skeleton is in
[docs/codex/mission-control-display-decision-record-skeleton.md](docs/codex/mission-control-display-decision-record-skeleton.md)
and is checked with `make mission-control-display-decision-record-skeleton-check`; it defines the
only design-only post-RC decision shape a favorable normalized ERG-002 response may support, while
keeping Mission Control runtime importer behavior and authority transfer blocked.
Generate the Mission Control integration readiness packet with
`make mission-control-integration-readiness-packet`; it consolidates the display proposal, importer
plan, disposition packet, handoff schema, negative fixtures, side handoff, implementation ticket,
and command evidence into one Mission Control-side handoff packet while keeping `ERG-002`
planning-only and not closed.
The next sandbox/VM planning artifact is
[docs/codex/sandbox-vm-worker-boundary-charter.md](docs/codex/sandbox-vm-worker-boundary-charter.md)
and is checked with `make sandbox-vm-worker-boundary-charter-check`; it defines future sandbox
profile evidence, negative cases, and role separation while keeping VM/container lifecycle, local
model invocation, sandbox orchestration, and host promotion unimplemented.
The companion profile contract is
[docs/codex/sandbox-vm-profile-contract.md](docs/codex/sandbox-vm-profile-contract.md) and is
checked with `make sandbox-vm-profile-contract-check`; it defines the future operator-supplied
profile fields, forbidden fields, validation decisions, and `not_promoted` posture without adding a
runtime profile loader or sandbox control.
The follow-on preflight contract is
[docs/codex/sandbox-vm-preflight-contract.md](docs/codex/sandbox-vm-preflight-contract.md) and is
checked with `make sandbox-vm-preflight-contract-check`; it defines the future go/no-go evidence for
platform support, mount/root labels, network posture, artifact ingress/egress, cleanup/failure
transcripts, and warning chips without adding a live preflight runner.
Generate the focused sandbox/VM proof-of-concept review packet with
`make sandbox-vm-poc-review-packet`; it bundles the sandbox/VM boundary charter, profile contract,
preflight contract, Mission Control handoff docs, Hello World observed artifact evidence, artifact
write source-review handoff, promotion evidence contract, command evidence, and artifact hashes for
review before any live VM, local-model, or preflight-runner implementation is planned.
The follow-on implementation-planning packet is
[docs/codex/sandbox-vm-static-profile-preflight-plan.md](docs/codex/sandbox-vm-static-profile-preflight-plan.md)
and is checked with `make sandbox-vm-static-profile-preflight-plan-check`; it defines the future
static profile fixture and read-only preflight runner boundary while keeping live VM control,
Mission Control runtime behavior, local model invocation, and trusted-host promotion blocked.
The fixture contract is
[docs/codex/sandbox-vm-static-profile-fixture-contract.md](docs/codex/sandbox-vm-static-profile-fixture-contract.md)
and is checked with `make sandbox-vm-static-profile-fixture-contract-check`; it commits a
non-production static profile example with labels and false authority flags only, without adding a
runtime loader, live preflight runner, VM/container control, Mission Control execution, or local
model behavior.
The negative fixture plan is
[docs/codex/sandbox-vm-static-profile-negative-fixtures.md](docs/codex/sandbox-vm-static-profile-negative-fixtures.md)
and is checked with `make sandbox-vm-static-profile-negative-fixtures-check`; it mutates the
static profile example in memory to prove overclaims, raw path-shaped fields, broad network
posture, promotion claims, and authority flags fail closed with safe reason labels.
The implementation decision is
[docs/codex/sandbox-vm-static-preflight-implementation-decision.md](docs/codex/sandbox-vm-static-preflight-implementation-decision.md)
and is checked with `make sandbox-vm-static-preflight-implementation-gate`; it approves only the
CLI-only fixture preflight runner, not API/MCP behavior, sandbox orchestration, Mission
Control runtime behavior, local model invocation, trusted-host promotion, or new governed powers.
The focused source-review handoff is
[docs/codex/sandbox-vm-static-preflight-source-review.md](docs/codex/sandbox-vm-static-preflight-source-review.md)
and is generated with `make sandbox-vm-static-preflight-source-review-packet`; it packages the
CLI-only fixture preflight runner for focused review without approving live VM control, Mission
Control runtime behavior, local model invocation, or trusted-host promotion.
Generate the external disposition packet,
[docs/codex/sandbox-vm-static-preflight-disposition-packet.md](docs/codex/sandbox-vm-static-preflight-disposition-packet.md),
with `make sandbox-vm-static-preflight-disposition-packet`; it packages the source-review packet
pointer, disposition questions, intake template, command evidence, and artifact hashes for deciding
whether `ERG-003` can later move to `closed_local_preview_static_preflight` without approving live
sandbox/VM runtime work.
The static preflight external-review launch bundle is
[docs/codex/sandbox-vm-static-preflight-external-review-bundle.md](docs/codex/sandbox-vm-static-preflight-external-review-bundle.md),
with `make sandbox-vm-static-preflight-external-review-bundle`; it consolidates the source-review
packet, disposition packet, response/closure/triage path, reproduction map, queue status, and
command evidence into one 10-file handoff without closing `ERG-003` or approving live sandbox/VM
runtime work.
The static preflight response kit is
[docs/codex/sandbox-vm-static-preflight-response-kit.md](docs/codex/sandbox-vm-static-preflight-response-kit.md),
with `make sandbox-vm-static-preflight-response-kit`; it packages response-intake guidance,
normalized-response examples, closure/triage commands, queue status, and artifact hashes for real
reviewer feedback without closing `ERG-003`, unblocking `ERG-004`, or approving live sandbox/VM
runtime work.
The live POC response kit is
[docs/codex/sandbox-vm-live-poc-response-kit.md](docs/codex/sandbox-vm-live-poc-response-kit.md),
with `make sandbox-vm-live-poc-response-kit`; it packages response-intake guidance,
normalized-response examples, closure/decision-record commands, queue status, and artifact hashes
for real `ERG-004` decision-packet feedback without closing `ERG-004`, approving implementation
planning, or approving live sandbox/VM runtime work.
The live POC external-review launch bundle is
[docs/codex/sandbox-vm-live-poc-external-review-bundle.md](docs/codex/sandbox-vm-live-poc-external-review-bundle.md),
with `make sandbox-vm-live-poc-external-review-bundle`; it consolidates the blocked `ERG-004`
decision packet, contracts, preconditions, response/closure dry runs, queue status, command
evidence, and artifact hashes into one reviewer handoff without closing `ERG-004`, approving
implementation planning, or approving live sandbox/VM runtime work.
The external disposition plan is
[docs/codex/sandbox-vm-static-preflight-disposition-plan.md](docs/codex/sandbox-vm-static-preflight-disposition-plan.md)
and is checked with `make sandbox-vm-static-preflight-disposition-plan-check`; it defines the
reviewer questions, allowed outcomes, closure evidence, and post-disposition boundary for `ERG-003`
without closing the lane or approving live sandbox/VM runtime work.
The fail-closed disposition closure gate is
[docs/codex/sandbox-vm-static-preflight-disposition-closure-gate.md](docs/codex/sandbox-vm-static-preflight-disposition-closure-gate.md)
and is checked with `make sandbox-vm-static-preflight-disposition-closure-check`; it reports
`closure_ready: false` until normalized source-level response evidence exists, and it still does not
approve live sandbox/VM runtime work.
The static preflight disposition-record skeleton is
[docs/codex/sandbox-vm-static-preflight-disposition-record-skeleton.md](docs/codex/sandbox-vm-static-preflight-disposition-record-skeleton.md)
and is checked with `make sandbox-vm-static-preflight-disposition-record-skeleton-check`; it defines
the only future `ERG-003` movement to `closed_local_preview_static_preflight` after favorable
source-level evidence while keeping `ERG-004`, live POC planning, runtime implementation, sandbox
orchestration, Mission Control runtime behavior, local model invocation, trusted-host promotion, and
new governed tool powers blocked.
The external response intake template is
[docs/codex/sandbox-vm-static-preflight-external-response-intake.md](docs/codex/sandbox-vm-static-preflight-external-response-intake.md)
and is checked with `make sandbox-vm-static-preflight-external-response-intake-check`; it defines
the `EXT-SVP-###` namespace and normalizer command for reviewer responses without mutating findings,
closing `ERG-003`, or approving live sandbox/VM runtime work.
Use `make sandbox-vm-static-preflight-reviewed-packet-hash` after generating the external-review
bundle to get the exact `--reviewed-packet-hash` value for that normalization command.
The static preflight response dry run is
[docs/codex/sandbox-vm-static-preflight-response-dry-run.md](docs/codex/sandbox-vm-static-preflight-response-dry-run.md)
and is checked with `make sandbox-vm-static-preflight-response-dry-run`; it temporarily exercises
favorable and unfavorable normalized-response fixtures against the fail-closed closure gate while
restoring the ignored response path and without recording external review.
The static preflight triage-update checklist is
[docs/codex/sandbox-vm-static-preflight-triage-update.md](docs/codex/sandbox-vm-static-preflight-triage-update.md)
and is checked with `make sandbox-vm-static-preflight-triage-update-check`; it defines the safe
committed update path after real favorable `ERG-003` evidence while keeping `ERG-004`, live
sandbox/VM runtime work, local model invocation, Mission Control runtime behavior, and trusted-host
promotion blocked.
The static preflight response-application record is
[docs/codex/sandbox-vm-static-preflight-response-application-record.md](docs/codex/sandbox-vm-static-preflight-response-application-record.md)
and is checked with `make sandbox-vm-static-preflight-response-application-record-check`; it gives a
manager-owned checklist for applying a real reviewer response without closing `ERG-003` by itself or
unblocking `ERG-004`, live sandbox/VM runtime work, Mission Control runtime behavior, local model
invocation, trusted-host promotion, or new governed tool powers.
The static preflight response-application playbook is
[docs/codex/sandbox-vm-static-preflight-response-application-playbook.md](docs/codex/sandbox-vm-static-preflight-response-application-playbook.md)
and is checked with `make sandbox-vm-static-preflight-response-application-playbook-check`; it
spells out the exact manager-owned input paths, command sequence, allowed committed files,
stop conditions, and final gates for applying a real `ERG-003` response without unblocking live
sandbox/VM runtime work, Mission Control runtime behavior, local model invocation, trusted-host
promotion, or broader Ithildin authority.
The static preflight response-application preflight is
[docs/codex/sandbox-vm-static-preflight-response-application-preflight.md](docs/codex/sandbox-vm-static-preflight-response-application-preflight.md)
and is checked with `make sandbox-vm-static-preflight-response-application-preflight-check`; it
keeps the all-lane raw response inbox path and ERG-003 normalized response path aligned before a
real reviewer response is applied, without normalizing responses, closing `ERG-003`, unblocking
`ERG-004`, or approving live sandbox/VM runtime behavior.
The reviewer reproduction map is
[docs/codex/sandbox-vm-static-preflight-reviewer-reproduction-map.md](docs/codex/sandbox-vm-static-preflight-reviewer-reproduction-map.md)
and is checked with `make sandbox-vm-static-preflight-reviewer-reproduction-map-check`; it gives
reviewers a compact command/evidence path for reproducing the static preflight lane while keeping
`ERG-003` external-review-required until a later committed triage update.
The live sandbox/VM POC decision intake is
[docs/codex/sandbox-vm-live-poc-decision-intake.md](docs/codex/sandbox-vm-live-poc-decision-intake.md)
and is checked with `make sandbox-vm-live-poc-decision-intake-check`; it records the evidence
required before a future post-RC decision record may consider `ERG-004`, while keeping live
VM/container inspection, Mission Control runtime behavior, local model invocation, sandbox
orchestration, trusted-host promotion, and public/security-product positioning blocked.
The live sandbox/VM POC evidence contract is
[docs/codex/sandbox-vm-live-poc-evidence-contract.md](docs/codex/sandbox-vm-live-poc-evidence-contract.md)
and is checked with `make sandbox-vm-live-poc-evidence-contract-check`; it defines the future
cross-source evidence bundle for operator intent, Ithildin run/audit evidence, operator-managed
sandbox evidence, local model/client evidence, and optional Mission Control display evidence without
approving live VM/container inspection or runtime authority.
The live sandbox/VM POC preconditions map is
[docs/codex/sandbox-vm-live-poc-preconditions-map.md](docs/codex/sandbox-vm-live-poc-preconditions-map.md)
and is checked with `make sandbox-vm-live-poc-preconditions-map-check`; it ties favorable `ERG-003`
disposition, the future decision-record path, operator-managed VM/container assumptions,
cleanup/failure transcripts, and cross-source evidence into one blocked-lane readiness checklist
without approving live VM/container inspection or runtime authority.
The live sandbox/VM POC preconditions ready check is
[docs/codex/sandbox-vm-live-poc-preconditions-ready-check.md](docs/codex/sandbox-vm-live-poc-preconditions-ready-check.md)
and is checked with `make sandbox-vm-live-poc-preconditions-ready-check`; it aggregates the
blocked-lane ERG-004 checks and reports that the wiring is valid while implementation planning
remains blocked on favorable `ERG-003` disposition and normalized `ERG-004` response evidence.
The live sandbox/VM POC post-ERG-003 handoff is
[docs/codex/sandbox-vm-live-poc-post-erg003-handoff.md](docs/codex/sandbox-vm-live-poc-post-erg003-handoff.md)
and is checked with `make sandbox-vm-live-poc-post-erg003-handoff-check`; it explains the still
blocked sequence to follow after favorable `ERG-003` evidence is committed, without approving live
VM/container inspection, local model invocation, Mission Control runtime behavior, or runtime
implementation.
The live sandbox/VM POC external response intake template is
[docs/codex/sandbox-vm-live-poc-external-response-intake.md](docs/codex/sandbox-vm-live-poc-external-response-intake.md)
and is checked with `make sandbox-vm-live-poc-external-response-intake-check`; it defines the
`EXT-LIVE-POC-###` namespace and response-normalizer command for reviewer responses without
mutating findings, closing `ERG-004`, approving implementation planning, or approving live
sandbox/VM runtime work.
The live sandbox/VM POC decision closure gate is
[docs/codex/sandbox-vm-live-poc-decision-closure-gate.md](docs/codex/sandbox-vm-live-poc-decision-closure-gate.md)
and is checked with `make sandbox-vm-live-poc-decision-closure-check`; it reports
`closure_ready: false` until normalized source-level response evidence exists, favorable `ERG-003`
disposition is recorded, and a reviewer allows only later implementation-planning consideration.
The live sandbox/VM POC decision-record skeleton is in
[docs/codex/sandbox-vm-live-poc-decision-record-skeleton.md](docs/codex/sandbox-vm-live-poc-decision-record-skeleton.md)
and is checked with `make sandbox-vm-live-poc-decision-record-skeleton-check`; it defines the only
implementation-planning-only post-RC decision shape a favorable normalized ERG-004 response may
support, while keeping runtime implementation, live VM/container inspection, sandbox orchestration,
Mission Control runtime behavior, local model invocation, trusted-host promotion, and new tool
powers blocked.
The live sandbox/VM POC response dry run is
[docs/codex/sandbox-vm-live-poc-response-dry-run.md](docs/codex/sandbox-vm-live-poc-response-dry-run.md)
and is checked with `make sandbox-vm-live-poc-response-dry-run`; it temporarily exercises favorable
and unfavorable normalized-response fixtures, including missing favorable `ERG-003` disposition,
then restores the ignored response path without recording external review or approving live
sandbox/VM runtime work.
The live sandbox/VM POC prerequisite disposition dry run is
[docs/codex/sandbox-vm-live-poc-prerequisite-disposition-dry-run.md](docs/codex/sandbox-vm-live-poc-prerequisite-disposition-dry-run.md)
and is checked with `make sandbox-vm-live-poc-prerequisite-disposition-dry-run`; it temporarily
exercises favorable and unfavorable `ERG-003` disposition-record fixtures before live POC planning
while proving that favorable static-preflight evidence satisfies only a prerequisite and does not
unblock `ERG-004`.
The live sandbox/VM POC decision packet is
[docs/codex/sandbox-vm-live-poc-decision-packet.md](docs/codex/sandbox-vm-live-poc-decision-packet.md)
and is generated with `make sandbox-vm-live-poc-decision-packet`; it packages the decision intake,
evidence contract, enterprise sandbox readiness map, prerequisite static-preflight disposition
evidence, command output, and artifact hashes while keeping `ERG-004` blocked.
The internal source-review pass is
[docs/codex/v3-sandbox-vm-static-preflight-internal-review.md](docs/codex/v3-sandbox-vm-static-preflight-internal-review.md);
it records the CLI-only fixture preflight runner as locally reviewed after tightening echoed label
handling, while keeping external/source review, live VM inspection, Mission Control runtime
behavior, and sandbox orchestration pending or blocked.
The governed artifact transfer lab note is
[docs/codex/governed-artifact-transfer-lab.md](docs/codex/governed-artifact-transfer-lab.md);
it now includes a Stage 1 Part 1 Ithildin-only known-good packet, a Stage 1 Part 2 Mission Control
handoff wrapper, and a Stage 2 simulated sandbox transfer generated with
`make governed-artifact-transfer-stage2`; real VM/sandbox orchestration remains a future gated
implementation decision.
The Hello World sandbox demo roadmap is in
[docs/codex/hello-world-sandbox-demo-roadmap.md](docs/codex/hello-world-sandbox-demo-roadmap.md)
and is checked with `make hello-world-sandbox-demo-check`; it defines the end-to-end Mission
Control + local LLM + Ithildin demo target around bounded `sandbox.artifact.write_text`, and the
tool count remains `24`.
Generate the evidence-only packet with `make hello-world-sandbox-demo-packet`; validate it with
`make hello-world-sandbox-demo-packet-check`. The packet writes only ignored/local review artifacts,
records that the bounded sandbox write capability exists, but does not perform governed tool calls,
Mission Control runtime behavior, real VM startup, sandbox orchestration, shell execution, or host
promotion.
Generate the observed Hello World packet with `make hello-world-sandbox-observed-demo`; validate it
with `make hello-world-sandbox-observed-demo-check`. That packet performs the existing governed
`sandbox.artifact.write_text` approval/execution flow in a temporary local fixture workspace while
keeping Mission Control, local LLM execution, VM/container lifecycle, sandbox orchestration, shell
execution, and host promotion disabled.
Generate the Mission Control handoff packet with `make hello-world-mission-control-handoff`;
validate it with `make hello-world-mission-control-handoff-check`. That packet is metadata-only:
Mission Control may display/import evidence labels, hashes, approval status, and warning chips, but
it does not execute governed actions, replace Ithildin policy, call a local model, start a
VM/container, orchestrate a sandbox, or promote files to the trusted host.
Validate the future promotion evidence shape with `make sandbox-promotion-evidence-contract-check`;
that contract defines labels, hashes, approval evidence, and review states for a later explicit
promotion implementation, but it does not approve trusted-host writes today.
The trusted-host promotion decision intake is in
[docs/codex/trusted-host-promotion-decision-intake.md](docs/codex/trusted-host-promotion-decision-intake.md)
and is checked with `make trusted-host-promotion-decision-intake-check`; it defines the required
decision evidence, negative evidence, and allowed future outcomes before any promotion runtime path
can be considered.
The design-only trusted-host promotion state machine is in
[docs/codex/trusted-host-promotion-state-machine.md](docs/codex/trusted-host-promotion-state-machine.md)
and is checked with `make trusted-host-promotion-state-machine-check`; it defines future state
labels, allowed transitions, safe evidence fields, and transition-denial cases.
The design-only trusted-host promotion negative fixture contract is in
[docs/codex/trusted-host-promotion-negative-fixtures.md](docs/codex/trusted-host-promotion-negative-fixtures.md)
and is checked with `make trusted-host-promotion-negative-fixtures-check`; it defines the future
denial transcript families for conflict, replay, stale evidence, unsafe labels, sensitive payloads,
and product-boundary overclaims before any promotion implementation can be considered.
The design-only trusted-host promotion zone contract is in
[docs/codex/trusted-host-promotion-zone-contract.md](docs/codex/trusted-host-promotion-zone-contract.md)
and is checked with `make trusted-host-promotion-zone-contract-check`; it defines future
`sandbox://`, `host-staging://`, `approved://`, and `evidence://` labels without granting
filesystem authority.
The design-only trusted-host promotion implementation-plan skeleton is in
[docs/codex/trusted-host-promotion-implementation-plan.md](docs/codex/trusted-host-promotion-implementation-plan.md)
and is checked with `make trusted-host-promotion-implementation-plan-check`; it gathers the
evidence contract, decision intake, state machine, negative fixtures, and zone contract into the
minimum future runtime-plan checklist while keeping host promotion unapproved.
The focused trusted-host promotion source-review handoff is in
[docs/codex/trusted-host-promotion-source-review.md](docs/codex/trusted-host-promotion-source-review.md)
and is generated with `make trusted-host-promotion-source-review-packet`; it asks reviewers whether
the lane may continue as design-only planning and does not approve runtime host promotion.
The trusted-host promotion disposition packet is in
[docs/codex/trusted-host-promotion-disposition-packet.md](docs/codex/trusted-host-promotion-disposition-packet.md)
and is generated with `make trusted-host-promotion-disposition-packet`; it packages the source-review
pointer, disposition question set, command evidence, and artifact hashes for reviewer handoff
without approving trusted-host promotion or direct host writes.
The trusted-host promotion external response intake template is in
[docs/codex/trusted-host-promotion-external-response-intake.md](docs/codex/trusted-host-promotion-external-response-intake.md)
and is checked with `make trusted-host-promotion-external-response-intake-check`; it defines the
`EXT-TRUSTED-HOST-###` finding namespace and `trusted-host-promotion` normalizer command for
recording reviewer responses without mutating findings, closing `ERG-005`, or approving runtime
host promotion.
The trusted-host promotion disposition closure gate is in
[docs/codex/trusted-host-promotion-disposition-closure-gate.md](docs/codex/trusted-host-promotion-disposition-closure-gate.md)
and is checked with `make trusted-host-promotion-disposition-closure-check`; it keeps `ERG-005`
blocked unless normalized source-level response evidence explicitly supports design-only
continuation and contains no critical/high findings.
The trusted-host promotion response dry run is in
[docs/codex/trusted-host-promotion-response-dry-run.md](docs/codex/trusted-host-promotion-response-dry-run.md)
and is checked with `make trusted-host-promotion-response-dry-run`; it temporarily exercises
favorable and unfavorable normalized-response fixtures while restoring the ignored response path and
without closing `ERG-005` or approving implementation planning.
The trusted-host promotion response kit is in
[docs/codex/trusted-host-promotion-response-kit.md](docs/codex/trusted-host-promotion-response-kit.md)
and is generated with `make trusted-host-promotion-response-kit`; it packages response-intake
guidance, normalized-response examples, closure commands, queue status, command evidence, and
artifact hashes for real reviewer feedback without closing `ERG-005`, approving implementation
planning, or approving trusted-host promotion.
The internal trusted-host promotion source-review pass is in
[docs/codex/v3-trusted-host-promotion-internal-review.md](docs/codex/v3-trusted-host-promotion-internal-review.md)
and is checked with `make trusted-host-promotion-internal-review-check`; it records
`continue_design_only` posture and keeps implementation blocked pending future decision/external
review.
Its implementation-planning packet is
[docs/codex/capability-implementation-plans/sandbox-artifact-write-text.md](docs/codex/capability-implementation-plans/sandbox-artifact-write-text.md);
fixture and denial expectations are in
[docs/codex/sandbox-artifact-write-text-fixture-plan.md](docs/codex/sandbox-artifact-write-text-fixture-plan.md)
and
[docs/codex/sandbox-artifact-write-text-negative-transcripts.md](docs/codex/sandbox-artifact-write-text-negative-transcripts.md);
observed local fixture approval/execution evidence is in
[docs/codex/sandbox-artifact-observed-demo.md](docs/codex/sandbox-artifact-observed-demo.md)
and generated with `make sandbox-artifact-observed-demo`;
the future source-review lane is
[docs/codex/sandbox-artifact-write-text-source-review.md](docs/codex/sandbox-artifact-write-text-source-review.md).
Generate observed denial transcripts with `make sandbox-artifact-write-text-negative-transcripts`;
generate the focused source-review handoff with
`make sandbox-artifact-write-text-source-review-bundle`.
The historical preimplementation check remains available for lineage, but active readiness now uses
the runtime implementation gate.
The approved future implementation boundary is recorded in
[docs/codex/sandbox-artifact-write-text-implementation-decision.md](docs/codex/sandbox-artifact-write-text-implementation-decision.md)
and checked with `make sandbox-artifact-write-text-implementation-gate`; the gate confirms the
bounded local-preview runtime implementation and keeps host promotion, VM/container lifecycle,
Mission Control runtime behavior, shell execution, and broad writes blocked.
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
The next selected bounded read-only Git metadata lane is `git.show.tag_metadata`; its current
planning docs are
[docs/codex/v0.9-git-tag-metadata-selection.md](docs/codex/v0.9-git-tag-metadata-selection.md),
[docs/codex/capability-proposals/git-show-tag-metadata.md](docs/codex/capability-proposals/git-show-tag-metadata.md),
and
[docs/codex/capability-implementation-plans/git-show-tag-metadata.md](docs/codex/capability-implementation-plans/git-show-tag-metadata.md).
The approved implementation boundary is
[docs/codex/v0.9-git-tag-metadata-implementation.md](docs/codex/v0.9-git-tag-metadata-implementation.md);
runtime implementation is now limited to that boundary and checked with
`make git-tag-metadata-implementation-gate`. The focused source-review handoff is
[docs/codex/v0.9-git-tag-metadata-source-review.md](docs/codex/v0.9-git-tag-metadata-source-review.md);
the ignored output is `var/review-packets/v0.9/git-tag-metadata-source-review/`.
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
[docs/codex/v3-next-capability-candidate-evaluation-2.md](docs/codex/v3-next-capability-candidate-evaluation-2.md),
[docs/codex/metadata-privacy-policy.md](docs/codex/metadata-privacy-policy.md),
[docs/codex/read-only-metadata-capability-checklist.md](docs/codex/read-only-metadata-capability-checklist.md),
[docs/codex/read-only-capability-source-review-template.md](docs/codex/read-only-capability-source-review-template.md),
and [docs/codex/v3-readiness-debt-register.md](docs/codex/v3-readiness-debt-register.md); they are
checked with `make read-only-metadata-capability-check` and
`make read-only-capability-inventory-gate`. The next-capability preflight is
[docs/codex/next-capability-readiness.md](docs/codex/next-capability-readiness.md) and is checked
with `make next-capability-readiness`; it records that `project.release.summary` has advanced
through a bounded read-only implementation, internal source review, and source-review handoff while
broader capability expansion remains blocked. The most recent implemented candidate is
[docs/codex/capability-proposals/project-risk-summary.md](docs/codex/capability-proposals/project-risk-summary.md),
checked with `make project-risk-summary-proposal-check`. Its historical implementation-planning packet is
[docs/codex/capability-implementation-plans/project-risk-summary.md](docs/codex/capability-implementation-plans/project-risk-summary.md)
and is checked with `make project-risk-summary-implementation-plan-check`; its implementation boundary is
recorded in
[docs/codex/v3-project-risk-summary-implementation.md](docs/codex/v3-project-risk-summary-implementation.md)
and checked with `make project-risk-summary-implementation-gate`; fixture and handoff evidence are
checked with `make project-risk-summary-preimplementation-check` and
`make project-risk-summary-review-handoff-check`; generate its implemented source-review packet with
`make project-risk-summary-source-review-bundle`. No next design-only candidate is selected yet.
The implemented tool is risk-signal count metadata only, not vulnerability scanning, dependency analysis,
compliance automation, security assurance, scanner execution, registry/network access, or shell
execution. The previous selected candidate,
[docs/codex/capability-proposals/project-ci-summary.md](docs/codex/capability-proposals/project-ci-summary.md),
advanced through implementation planning and source-review handoff. Its implementation-planning
packet is
[docs/codex/capability-implementation-plans/project-ci-summary.md](docs/codex/capability-implementation-plans/project-ci-summary.md)
and is checked with `make project-ci-summary-implementation-plan-check`; the bounded
implementation decision is
[docs/codex/v3-project-ci-summary-implementation.md](docs/codex/v3-project-ci-summary-implementation.md)
and is checked with `make project-ci-summary-implementation-gate`; generate its focused
source-review handoff with `make project-ci-summary-source-review-bundle` and its historical
design-review packet with `make project-ci-summary-design-review-packet`. The earlier selected
candidate,
[docs/codex/capability-proposals/project-config-summary.md](docs/codex/capability-proposals/project-config-summary.md),
advanced through implementation planning and source-review handoff. Its implementation-planning packet is
[docs/codex/capability-implementation-plans/project-config-summary.md](docs/codex/capability-implementation-plans/project-config-summary.md)
and is checked with `make project-config-summary-implementation-plan-check`; the bounded
implementation decision is
[docs/codex/v3-project-config-summary-implementation.md](docs/codex/v3-project-config-summary-implementation.md)
and is checked with `make project-config-summary-implementation-gate`; generate its focused
source-review handoff with `make project-config-summary-source-review-bundle`. The previous
selected candidate,
[docs/codex/capability-proposals/project-language-summary.md](docs/codex/capability-proposals/project-language-summary.md),
advanced through implementation planning and source-review handoff. Its implementation-planning packet is
[docs/codex/capability-implementation-plans/project-language-summary.md](docs/codex/capability-implementation-plans/project-language-summary.md)
and is checked with `make project-language-summary-implementation-plan-check`; the bounded
implementation decision is
[docs/codex/v3-project-language-summary-implementation.md](docs/codex/v3-project-language-summary-implementation.md)
and is checked with `make project-language-summary-implementation-gate`; generate its focused
source-review handoff with `make project-language-summary-source-review-bundle`. Runtime
implementation remains limited to that explicit decision. The
historical test-summary proposal is
[docs/codex/capability-proposals/project-test-summary.md](docs/codex/capability-proposals/project-test-summary.md),
checked with `make project-test-summary-proposal-check`. Its implementation-planning packet is
[docs/codex/capability-implementation-plans/project-test-summary.md](docs/codex/capability-implementation-plans/project-test-summary.md)
and is checked with `make project-test-summary-implementation-plan-check`; the bounded
implementation decision is
[docs/codex/v3-project-test-summary-implementation.md](docs/codex/v3-project-test-summary-implementation.md)
and is checked with `make project-test-summary-implementation-gate`; generate its focused
source-review handoff with `make project-test-summary-source-review-bundle`. The historical selected design-only candidate is
[docs/codex/capability-proposals/project-structure-summary.md](docs/codex/capability-proposals/project-structure-summary.md)
and is checked with `make project-structure-summary-proposal-check`; its implementation-planning
packet is
[docs/codex/capability-implementation-plans/project-structure-summary.md](docs/codex/capability-implementation-plans/project-structure-summary.md)
and is checked with `make project-structure-summary-implementation-plan-check`; the bounded
implementation decision is
[docs/codex/v3-project-structure-summary-implementation.md](docs/codex/v3-project-structure-summary-implementation.md)
and is checked with `make project-structure-summary-implementation-gate`; generate its focused
source-review handoff with `make project-structure-summary-source-review-bundle`. The consolidated
eleven-tool project intelligence slice is
[docs/codex/read-only-project-intelligence.md](docs/codex/read-only-project-intelligence.md) and is
checked with `make read-only-project-intelligence`. The historical design-only candidate evaluation is
[docs/codex/v3-next-capability-candidate-evaluation.md](docs/codex/v3-next-capability-candidate-evaluation.md),
and the newer planning-only candidate evaluation is
[docs/codex/v3-next-capability-candidate-evaluation-2.md](docs/codex/v3-next-capability-candidate-evaluation-2.md);
the historical `project.dependency.summary` selection is
[docs/codex/v3-project-dependency-summary-selection.md](docs/codex/v3-project-dependency-summary-selection.md),
checked with `make v3-next-capability-candidate-check`. The proposal for that now-implemented
candidate is
[docs/codex/capability-proposals/project-dependency-summary.md](docs/codex/capability-proposals/project-dependency-summary.md)
and is checked with `make project-dependency-summary-proposal-check`; the implementation-planning
packet is
[docs/codex/capability-implementation-plans/project-dependency-summary.md](docs/codex/capability-implementation-plans/project-dependency-summary.md)
and is checked with `make project-dependency-summary-implementation-plan-check`; the design-review
packet is generated with `make project-dependency-summary-design-review-packet`. Its implementation
record is [docs/codex/v3-project-dependency-summary-implementation.md](docs/codex/v3-project-dependency-summary-implementation.md)
and the source-review handoff is [docs/codex/v3-project-dependency-summary-source-review.md](docs/codex/v3-project-dependency-summary-source-review.md).
The proposal for the now-implemented historical
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
If an ignored local review-run manifest has stale commit or dirty metadata after a new commit,
`make review-run-manifest-refresh` is the explicit local-only fix before re-running validation.
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

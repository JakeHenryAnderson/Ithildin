# GPT-5.6 Codex Readiness and Skill Candidates

Status: implemented instruction/configuration audit and pre-skill design record.

## Configuration Map

- Personal default: GPT-5.6 Sol, medium reasoning, cached search, pragmatic responses,
  workspace-scoped writes, and on-request escalation.
- Personal profiles: Terra/medium for bounded efficient work, Luna/low for mechanical bulk work,
  and Sol/xhigh/read-only for deep review.
- Repository guidance: root `AGENTS.md` owns the product boundary, model ladder, completion contract,
  gates, and stop conditions. `docs/AGENTS.md` owns evidence/status wording. `scripts/AGENTS.md` owns
  deterministic generator and fail-closed check conventions.
- Enforcement remains in tests, gates, policy, source review, and human decisions. Instruction files
  coordinate agents but are not a security boundary.

## Audit Findings and Applied Decisions

1. The personal default already used Sol/medium and cached search. The stale 5.5/5.4-mini model
   ladder in personal and repository instructions was the highest-impact contradiction; it is now
   aligned to Sol, Terra, and Luna.
2. Personal execution defaults were broader than the recommended day-to-day posture. Future tasks
   now default to workspace-write with on-request escalation; explicitly authorized sessions may
   still choose broader permissions.
3. The root instruction file mixed universal boundaries with subtree procedure. Evidence wording and
   script/gate conventions now live in nested files so unrelated work does not load those details.
4. The repository already had authoritative focused and full gates. The completion contract now
   requires proportional verification and final diff review without making every small edit run the
   full release pipeline.
5. Repeated evidence workflows are credible skill candidates, but none is created by this change.
   Trigger design and accidental activation risk require review first.

## Model and Effort Assignment

| Workflow | Default | Escalate when |
| --- | --- | --- |
| Implementation, debugging, code-linked docs | Sol / medium | trust boundary, persistent failure, or cross-layer ambiguity |
| Repository maps, inventories, fixture/docs cleanup | Terra / medium | findings require product or safety judgment |
| Repetitive metadata or test-matrix mechanics | Luna / low-medium | outputs are not objectively comparable or testable |
| Architecture, policy/executor interaction, threat review | Sol / high-xhigh | use a separate decision gate for exceptional risk |
| Completed-change independent review | read-only reviewer; Ultra only when justified | independent lanes materially improve confidence |

One agent owns implementation. Parallel agents are primarily independent read-only investigators or
reviewers; their output never replaces the main agent's scope and safety judgment.

## Skill Candidates

Rank = expected recurrence and time saved, discounted for maintenance and accidental-trigger risk.

### 1. Review Finding Triage

- Trigger: a real or fixture review response must be normalized, mapped, and checked for closure.
- Must not trigger: no response exists, the lane is ambiguous, or the request asks the agent to
  invent a disposition.
- Inputs: raw response, lane response kit, finding namespace, current closure matrix.
- Procedure: verify provenance -> dry-run normalization -> map findings -> identify conflicts ->
  prepare proposed updates -> run lane checks -> stop before closure unless authorized evidence
  satisfies the gate.
- Side effects: write only normalized/proposed response artifacts in the selected lane.
- Stop: malformed provenance, cross-lane findings, critical/high boundary issue, or implied approval.
- Output: triage report, proposed file set, checks, and unresolved human decisions.
- Support: `SKILL.md`, response-kit reference, and a thin wrapper around existing scripts; no assets.

### 2. ERG Packet Assembly and Validation

- Trigger: refresh or validate a named ERG packet from committed source inputs.
- Must not trigger: select a new ERG lane, send a packet, or treat generation as external review.
- Inputs: ERG id, source bundle, generator/check targets, destination class.
- Procedure: identify authoritative source -> run focused checks -> generate -> verify inventory and
  hashes -> compare status language -> report dirty state and limitations.
- Side effects: regenerate only the named packet under existing targets.
- Stop: missing source, hash mismatch, stale route conflict, or tool-count/boundary change.
- Output: packet path, inventory, hashes, validation result, and non-claims.
- Support: `SKILL.md`, target map reference, existing generators; no new generator abstraction.

### 3. Release Evidence Checkpoint

- Trigger: a meaningful handoff or release-candidate checkpoint needs reproducible evidence.
- Must not trigger: ordinary focused development checks or a request to declare release approval.
- Inputs: commit/dirty state, validation profile, expected packet set.
- Procedure: preflight state -> run impact/profile guidance -> run authoritative full gates -> capture
  transcript -> verify artifact freshness -> summarize blockers without changing dispositions.
- Side effects: generated release evidence only.
- Stop: dirty-state policy conflict, repeated gate failure, or stale/mismatched artifacts.
- Output: checkpoint summary with exact commit, commands, artifacts, and blockers.
- Support: `SKILL.md`, validation timing reference, existing transcript tools.

### 4. Capability Boundary Review

- Trigger: a proposal might add a governed tool, power class, runtime authority, or product claim.
- Must not trigger: routine implementation wholly inside an already approved plan and gate.
- Inputs: proposal, current registry/tool count, boundary docs, threat model, required review lane.
- Procedure: classify power change -> compare deferred list -> enumerate affected enforcement layers ->
  require proposal/plan/gate/review artifacts -> return decision questions only.
- Side effects: planning documents only; read-only by default.
- Stop: ambiguous authority, security regression, or pressure to infer approval.
- Output: boundary classification, affected controls, required artifacts, and human decision gate.
- Support: `SKILL.md` plus concise boundary and tool-count references; no scripts initially.

### 5. Artifact Integrity and Dirty-State Verification

- Trigger: a packet, bundle, or handoff requires byte/hash and source-state verification.
- Must not trigger: signatures, custody, or notarization claims beyond existing evidence semantics.
- Inputs: artifact root, manifest, source commit, allowed ignored/generated paths.
- Procedure: constrain paths -> recompute sizes/hashes -> compare inventory -> report commit and dirty
  state -> flag unhashed/unexpected files -> preserve redaction boundaries.
- Side effects: read-only unless explicitly asked to regenerate an existing manifest.
- Stop: path escape, sensitive metadata, mismatch, or unsupported provenance claim.
- Output: deterministic integrity report and clearly bounded claim.
- Support: `SKILL.md` and existing hash helpers; add a script only if current helpers cannot compose.

## Daily Task Shape

Use: one concrete goal; relevant paths and authoritative requirements; authorized and prohibited
scope; smallest-complete-change process; observable done criteria; focused and broader validation;
and a final report naming changed files, checks, unresolved risk, and human decisions. Start a fresh
task for each coherent ticket or decision lane.

## Verification

Run:

```sh
codex --strict-config --version
codex --profile efficient --strict-config --version
codex --profile bulk --strict-config --version
codex --profile deep-review --strict-config --version
make agent-workflow-check
uv run pytest tests/test_release_readiness.py tests/test_docs_site.py -q
make lint
```

These checks validate configuration and documentation wiring. They do not approve a capability,
perform the ERG-005 walkthrough, close an enterprise lane, or make Ithildin enterprise-ready.

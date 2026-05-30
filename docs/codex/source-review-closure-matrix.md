# Source Review Closure Matrix

This matrix tracks external/source review closure for the v0.2 review candidate for the v0.1
local-preview runtime boundary. Initial status is `pending external review` until a reviewer records
findings and disposition.

For v0.3-prep, this matrix now separates internal review, internal AI/subagent pressure testing,
external review, finding records, and closure evidence. The task band is recorded in
[v0.3-milestone-manifest.md](v0.3-milestone-manifest.md). Internal review can increase confidence
and create findings, but it cannot mark an external/source-review row closed.

| Area | Files/functions to inspect | Reviewer | Date | Findings count | Blocking findings | Disposition | Closure notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fs.read` | `apps/api/src/ithildin_api/read_tools.py`; `FilesystemReadTools.read_file`; `ReadToolExecutor.execute`; `docs/codex/filesystem-executor-contract.md` | Codex internal source review pass 1 | 2026-05-30 | 1 | 0 | internal reviewed; pending external review | ISR-002 is addressed by Task 080 filesystem contract and capability check; external review remains pending. Path normalization, hidden/sensitive denial, symlink/hardlink behavior, read limits, and redaction handoff inspected. |
| `fs.patch.propose` | `apps/api/src/ithildin_api/patches.py`; `PatchProposalService.create_proposal`; unified-diff parser/applicator helpers; `docs/codex/filesystem-executor-contract.md` | Codex internal source review pass 1 | 2026-05-30 | 1 | 0 | internal reviewed; pending external review | ISR-002 also applies to proposal target path semantics and is addressed by Task 080 contract/regressions; external review remains pending. Stored proposal hash, base hash, target-path scope, binary/encoding denial, and stale context handling inspected. |
| `fs.patch.apply` | `apps/api/src/ithildin_api/patches.py`; `PatchProposalService.apply_approved`; `ApprovalService.begin_execution`; `docs/codex/filesystem-executor-contract.md` | Codex internal source review pass 1 | 2026-05-30 | 2 | 0 | internal reviewed; pending external review | ISR-001 is addressed by Task 079 read-only recovery evidence; ISR-002 is addressed by Task 080 filesystem contract and capability check. One-time approval consumption, proposal/base/manifest/policy/schema binding, atomic replace, replay/crash behavior inspected. |
| `http.fetch` | `apps/api/src/ithildin_api/http_tools.py`; `HttpFetchExecutor.fetch`; allowlist and resolver helpers | Codex internal source review pass 1 | 2026-05-30 | 0 | 0 | internal reviewed; pending external review | URL parsing, exact allowlist, redirect revalidation, DNS/IP checks, proxy suppression, and safe errors inspected. |
| Audit export/signing | `packages/audit-core/src/ithildin_audit_core/`; signed export helpers; API export route | Codex internal source review pass 1 | 2026-05-30 | 0 | 0 | internal reviewed; pending external review | JSONL digest binding, Ed25519 signature verification, public-key substitution, metadata/event ordering inspected. |
| Manifest-lock verification | `apps/api/src/ithildin_api/manifest_lock.py`; registry startup verification | Codex internal source review pass 1 | 2026-05-30 | 0 | 0 | internal reviewed; pending external review | Canonical lock payload, stale/missing entries, signature bundle verification, and key ID mismatch behavior inspected. |
| Policy preview/impact | `apps/api/src/ithildin_api/policy_preview.py`; `scripts/policy_impact.py`; policy evaluator | Codex internal source review pass 1 | 2026-05-30 | 0 | 0 | internal reviewed; pending external review | Principal/resource normalization parity with runtime, fixture consistency, and OPA/YAML evidence boundaries inspected. |
| MCP ingress | `apps/mcp-server/src/ithildin_mcp_server/`; adapter list/call handlers | Codex internal source review pass 1 | 2026-05-30 | 0 | 0 | internal reviewed; pending external review | Adapter thinness, schema/policy/approval/audit delegation, principal handling, and no-bypass path inspected. |
| Review-console approval flow | `apps/ui/src/App.tsx`; approval review API consumers | Codex internal source review pass 1 | 2026-05-30 | 0 | 0 | internal reviewed; pending external review | Binding evidence visibility, approve/deny payloads, stale/replay/expiry state clarity, and lack of direct execution controls inspected. |

## v2 Closure State

This v2 overlay is the working table for Tasks 085-112. It records each assurance layer separately
so later automation can update internal findings without overstating external closure.

| Area | Internal review | Subagent review | External review | Finding records | Blocking status | Closure evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `fs.read` | Pass 1 complete; Task 090 adversarial race harness and Task 091 contract enforcement added | Pending Wave 2 | Pending external review | ISR-002 | No blocking finding open | Task 080 contract/check evidence; Task 090 symlink/hardlink swap coverage; Task 091 release-check filesystem-contract-check gate; subagent blocker closed by failing unsupported profiles and hardening `fs.search` open path |
| `fs.patch.propose` | Pass 1 complete; Task 090 adversarial race harness and Task 091 contract enforcement added | Pending Wave 2 | Pending external review | ISR-002 | No blocking finding open | Task 080 contract/check evidence; Task 090 symlink/hardlink swap coverage; Task 091 release-check filesystem-contract-check gate |
| `fs.patch.apply` | Pass 1 complete; Task 088 failure simulations and Task 089 state-machine contract added | Pending Wave 2 | Pending external review | ISR-001, ISR-002 | No blocking finding open | Task 079 recovery evidence; Task 088 apply-attempt creation and status-failure simulations; Task 089 state-machine contract; parent-directory symlink swap regression added |
| `http.fetch` | Pass 1 complete; Task 092 canonicalization suite and Task 093 executor contract added | Wave 3 subagent review complete | Pending external review | SUB-001 | No blocking finding open | Task 092 malformed port, obfuscated IP, IPv4-mapped IPv6, redirect allowlist coverage; Task 093 HTTP executor contract; SUB-001 fixed internally by default pinned transport; external/source review still pending |
| Audit export/signing | Pass 1 complete; Task 094 replay/substitution tests and Task 095 evidence versioning added | Wave 3 subagent review complete | Pending external review | None | No blocking finding open | Task 094 wrong trusted public key and reordered-event substitution tests; trusted-public-key requirement; Task 095 evidence-contract versioning |
| Manifest-lock verification | Pass 1 complete; Task 094 replay/substitution tests and Task 095 evidence versioning added | Wave 3 subagent review complete; future Wave 5 validation remains | Pending external review | None | No blocking finding open | Task 094 signature replay against different lock path; trusted-public-key requirement; Task 095 evidence-contract versioning and future Task 105 validation suite |
| Policy preview/impact | Pass 1 complete; Task 096 parity harness and Task 097 OPA decision added | Pending Wave 4 | Pending external review | None | No blocking finding open | Task 096 preview/runtime parity fixtures compare preview decision evidence with runtime `policy.evaluated` audit metadata; Task 097 keeps YAML canonical for parity gates and OPA as optional verified sidecar evidence pending an OPA fixture runner |
| MCP ingress | Pass 1 complete; Task 098 bypass audit added | Pending Wave 4 | Pending external review | None | No blocking finding open | Task 098 tests fixed-principal audit evidence, unknown-tool denial audit, MCP-exposed listing, and role-filtered visibility; remote MCP remains deferred |
| Review-console approval flow | Pass 1 complete; Tasks 099-100 UI assurance added | Pending Wave 4 | Pending external review | None | No blocking finding open | Tasks 099-100 expose copyable approval binding evidence, approval scope hash, policy reason, patch-apply diagnostics, and trust warning banners without adding repair or mutation behavior |
| Negative review evidence | Packet recipes complete; Task 101 transcript expansion added | Pending Wave 5 | Pending external review | None | No blocking finding open | Task 101 expands observed transcripts to manifest-lock tamper, policy parity mismatch, and patch-apply ambiguous diagnostics in addition to path, symlink, stale-base, HTTP redirect, principal, and replay denials |

## v2 Update Rules

- `Internal review` records Codex/manual implementation-assurance passes only.
- `Subagent review` records internal high-intelligence pressure tests only.
- `External review` remains `pending external review` until GPT 5.5 Pro / Very High or a human
  expert reviews the relevant source and evidence.
- `Finding records` must point to structured finding IDs from the reviewer finding template or the
  Task 087 intake directory once available.
- `Blocking status` must say whether any critical/high finding is open.
- `Closure evidence` must cite concrete tasks, tests, command outputs, docs, or accepted deferrals.

## Closure Rule

A row is closed only when blocking findings are resolved or explicitly accepted as deferred with a
documented rationale. Closing this matrix does not make Ithildin production software; it only records
source-review disposition for the local-preview boundary.

Internal AI/subagent reviews may add findings and notes, but those rows must remain labeled as
internal review. External review closure requires GPT 5.5 Pro / Very High or human expert review of
the relevant source and evidence.

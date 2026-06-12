# Reviewer Reproduction Map

**Current status:** v0.8 roadmap/product-risk consultation after v0.6/v0.7 focused
source-review lane closure for the v0.1 local-preview runtime boundary; some generated paths retain
historical v0.2 names.

This map gives external reviewers a repeatable way to reproduce the current review packet evidence.
It is a review aid for the v0.1 local-preview runtime boundary and later review-closure waves, not
a claim of production security or implementation correctness.

Run all commands from the Ithildin repo root:

```sh
cd /Users/jake/Documents/Codex/Ithildin
```

## One-Command Handoff

Run `make review-candidate` to execute the full local handoff sequence. It runs `release-check`,
`filesystem-contract-check`, `signed-evidence-demo`, `negative-review-transcripts`,
operator sandbox packet, Agent Run correlation packet, `live-demo-status`, `live-demo-smoke`,
`live-demo-evidence-summary`, `live-demo-packet`, `workbench-evidence-packet`,
`v06-review-dispatch-packets`, `review-packet-bundle`,
`review-packet-consolidated`, packet redaction scan, and `docs-site`, then prints the consolidated
packet path. `release-check` includes
`make workbench-readiness`, `make adversarial-corpus-check`, `make resource-limit-check`, and
`make demo-scenario-pack`. Use
[demo-scenario-pack-v2.md](demo-scenario-pack-v2.md) as the concise scenario map for positive,
negative, signing, filesystem, and review-packet demos.
Use [live-demo-runbook.md](live-demo-runbook.md) for the local workbench demo sequence and
[review-docs-index.md](review-docs-index.md) to orient reviewers before attaching the packet.

For an evidence-only local workbench wrapper, run `make demo-workbench`. It regenerates live-demo
status/smoke/summary, operator sandbox, Agent Run correlation, demo readiness summary, operator demo
walkthrough, guide, reset guidance, workbench smoke, and operator workbench packet artifacts without
starting services or approving actions. For only the ready/missing/optional/deferred digest, run
`make demo-readiness-summary`; for the front-door expected screens, evidence files, next human
steps, and reset guidance, run `make demo-operator-walkthrough`; for the detailed
preflight-to-cleanup stage table, run `make operator-demo-guide`. For current seed/reachability
and next-command status, run `make demo-state-report`. For read-only repeat/recovery guidance, run
`make demo-reset-guide`. After an optional mediated `make demo-flow`, inspect
`DEMO_FLOW_RESULT.md`, then validate the result with `make demo-flow-result-check` and the wiring
with `make demo-flow-readiness`. After exporting run evidence, run `make demo-observed-summary`
for the compact observed-demo entry point. For a focused demo evidence closure packet, run
`make demo-evidence-packet` and validate it with `make demo-evidence-readiness`. To refresh the
whole non-service-starting demo handoff, run `make guided-demo`, then validate it with
`make guided-demo-readiness`. Inspect the focused packet with `make workbench-evidence-packet`; open
`var/review-packets/v3/operator-workbench/WORKBENCH_DEMO_INDEX.md` first. For only the
deterministic operator-flow transcript, run `make demo-workbench-smoke`.

Run `make internal-review-packet` when you want v2 local AI/subagent source-review prompts under
`var/review-packets/v0.3/internal-ai-review-packet/`. That packet is internal pressure-test
material only and does not replace external/source review.
Run `make reviewer-findings-check` after converting any internal AI/subagent, GPT 5.5 Pro, or human
review note into a structured finding file. The check validates
[reviewer-finding-intake.md](reviewer-finding-intake.md) records before the closure matrix changes.
Use [autonomous-sprint-guardrails.md](autonomous-sprint-guardrails.md) to decide when autonomous
work must stop for status, reassessment, or external consultation.

## Command Sequence

1. `make release-check`

   Expected outcome: passes after manifest-lock verification, release/evidence guardrails,
   evidence-contract validation, policy fixtures, pytest, ruff, mypy, UI typecheck, docs-site build,
   and UI production build.

2. `make release-evidence`

   Expected outcome: prints secret-free JSON showing a clean or intentionally noted git state,
   current manifest lock, tool count, policy/principal/workspace status, audit verification state,
   local-only security posture, review-doc hashes, and release-check transcript fields.

3. `make release-evidence-validate FILE=release-evidence.json`

   Expected outcome: validates a saved evidence snapshot against the v0.3-prep release-evidence
   schema contract. This is normally exercised on bundle-generated evidence.

4. `make release-packet`

   Expected outcome: prints a markdown review summary with repo root, commit, dirty state, trust
   evidence, deferred boundaries, review-doc hashes, and the note that the packet command does not
   itself run `make release-check`.

5. `make determinism-check`

   Expected outcome: runs pytest collection twice, confirms collection output is stable, and checks
   committed tests for obvious nondeterministic patterns such as sleeps, unseeded random calls, and
   hard-coded `/tmp` paths.

6. `make evidence-contracts-check`

   Expected outcome: validates `docs/codex/evidence-contracts-v2.json` and confirms the prose
   evidence-contract guide names the active local-preview contract version.

7. `make adversarial-corpus-check`

   Expected outcome: validates `tests/fixtures/adversarial_corpus_manifest.json`, confirms every
   corpus ID is unique, every referenced artifact exists, and every corpus has command/category
   metadata.

8. `make resource-limit-check`

   Expected outcome: validates local-preview read, patch, HTTP, search, and git-log limits against
   bounded ceilings and reports an empty HTTP allowlist as deny-by-default.

9. `make signed-evidence-demo`

   Expected outcome: creates ignored non-production fixture evidence under
   `var/review-packets/v0.2/signed-evidence-demo/`. The demo summary reports verified local audit
   export signing, verified manifest-lock signing, a tamper-failing audit bundle, and SHA-256
   digests for the generated demo artifacts.

10. `make signed-evidence-demo-verify`

   Expected outcome: verifies the signed audit demo bundle, confirms the tampered audit bundle does
   not verify, and verifies the demo manifest-lock signature using the generated demo public keys.

11. `make negative-review-transcripts`

   Expected outcome: creates ignored observed-denial transcripts under
   `var/review-packets/v0.2/negative-review-transcripts/`, covering traversal, symlink escape,
   stale-base patch apply, private redirect, unknown principal, disabled principal, and replayed
   approval.

12. `make v06-review-dispatch-packets`

   Expected outcome: creates focused v0.6 source-review dispatch packets under
   `var/review-packets/v0.6/dispatch/`, including `dispatch-packet-hashes.json` for patch apply,
   filesystem, HTTP fetch, signed evidence, policy/registry, MCP ingress, review console, and
   release automation review lanes.

13. `make review-packet-diff OLD=old-packet NEW=new-packet`

   Expected outcome: prints added, removed, changed, and unchanged artifact counts for two generated
   packets using `artifact-hashes.json` when available.

14. `make review-packet-diff-gate OLD=old-packet NEW=new-packet`

   Expected outcome: requires `artifact-hashes.json` in both packets and fails if a previously
   comparable artifact was removed. Added or changed artifacts are reported for reviewer attention.

15. `make filesystem-contract-check`

   Expected outcome: prints secret-free local platform and filesystem capability evidence. On
   macOS/Linux with `O_NOFOLLOW`, the support status should be `supported`; Windows/WSL are reported
   as unsupported/untested for local-preview workspace/race claims.

16. `make filesystem-source-review-bundle`

   Expected outcome: creates an ignored focused source-review handoff under
   `var/review-packets/v0.7/filesystem-source-review/`. This directly answers `EXT-FS-001` by
   attaching the filesystem/platform implementation files, focused tests, contract docs,
   `make filesystem-contract-check` output, `/system/status.filesystem` evidence, and artifact
   hashes for source-level external review.

17. `make http-fetch-source-review-bundle`

   Expected outcome: creates an ignored focused source-review handoff under
   `var/review-packets/v0.7/http-fetch-source-review/`. This attaches the `http.fetch`
   implementation path, canonicalization corpus, focused HTTP tests, contract docs, prior internal
   HTTP findings, policy-parity evidence, and artifact hashes for source-level external review.

18. `make signed-evidence-source-review-bundle`

   Expected outcome: creates an ignored focused source-review handoff under
   `var/review-packets/v0.7/signed-evidence-source-review/`. This attaches audit signing/export
   code, audit writer verification, manifest-lock signature code, API/CLI/demo wiring, focused
   audit/signing tests, contract docs, prior internal signed-evidence findings, demo verification
   evidence, and artifact hashes for source-level external review.

19. `make policy-registry-source-review-bundle`

   Expected outcome: creates an ignored focused source-review handoff under
   `var/review-packets/v0.7/policy-registry-source-review/`. This attaches policy-core evaluator
   code, preview/runtime parity paths, policy fixtures, manifest/principal/workspace registry
   loading, duplicate-key rejection, manifest-lock evidence, focused tests, prior internal
   policy/registry findings, command evidence, and artifact hashes for source-level external review.

20. `make mcp-ingress-source-review-bundle`

   Expected outcome: creates an ignored focused source-review handoff under
   `var/review-packets/v0.7/mcp-ingress-source-review/`. This attaches the stdio MCP adapter,
   shared governed-call path, trusted identity/registry helpers, MCP visibility and exposure-gate
   findings, focused MCP tests, command evidence, and artifact hashes for source-level external
   review.

21. `make review-console-source-review-bundle`

   Expected outcome: creates an ignored focused source-review handoff under
   `var/review-packets/v0.7/review-console-source-review/`. This attaches the React console,
   local admin API routes, approval review/mutation and patch diagnostics paths, focused API/UI
   validation, prior review-console findings, command evidence, and artifact hashes for
   source-level external review.

22. `make release-automation-source-review-bundle`

   Expected outcome: creates an ignored focused source-review handoff under
   `var/review-packets/v0.7/release-automation-source-review/`. This attaches release evidence,
   guardrails, packet/bundle generation, redaction scan, response normalization, closure/capability
   gates, release-readiness tests, prior release-automation findings, command evidence, and artifact
   hashes for source-level external review.

23. `make git-commit-metadata-source-review-bundle`

   Expected outcome: creates an ignored focused source-review handoff under
   `var/review-packets/v0.9/git-commit-metadata-source-review/`. This attaches the
   `git.show.commit_metadata` manifest, implementation path, focused tests, policy-parity fixture,
   implementation record, no-new-powers evidence, command evidence, and artifact hashes for
   source-level external review.

24. `make git-ref-summary-proposal-check`

   Expected outcome: validates the design-only `git.show.ref_summary` proposal, confirms the tool
   count remains unchanged, and confirms the proposal does not authorize manifests, executors,
   policy rules, MCP exposure, or runtime behavior.

25. `make git-ref-summary-implementation-plan-check`

   Expected outcome: validates the implementation-planning packet for `git.show.ref_summary`,
   records the historical implementation-planning checklist, and confirms the plan remains bounded
   to one read-only local metadata capability.

26. `make git-ref-summary-implementation-gate`

   Expected outcome: validates the approved bounded read-only `git.show.ref_summary`
   implementation boundary, including no raw ref names, no stable ref-name hashes, no remote refs,
   no shell, no raw diffs, no file contents, and tool count `14`.

27. `make git-ref-summary-source-review-bundle`

   Expected outcome: creates an ignored focused source-review handoff under
   `var/review-packets/v0.9/git-ref-summary-source-review/`. This attaches the
   `git.show.ref_summary` manifest, implementation path, focused tests, policy-parity fixture,
   implementation record, no-new-powers evidence, command evidence, and artifact hashes for
   source-level review.

28. `make read-only-metadata-capability-check`

   Expected outcome: validates the shared read-only metadata contract, metadata privacy policy,
   reusable capability checklist, source-review template, and v3 readiness debt register without
   authorizing runtime behavior or new power classes.

29. `make read-only-capability-inventory-gate`

   Expected outcome: validates the current approved bounded read-only metadata capability inventory,
   including the `git.show.commit_metadata`, `git.show.ref_summary`, and
   `project.manifest.summary` manifests, implementation gates, source-review handoffs, and
   release-check wiring.

30. `make v3-next-capability-candidate-check`

   Expected outcome: validates the design-only `project.dependency.summary` candidate selection.

31. `make next-capability-readiness`

   Expected outcome: validates the current bounded metadata inventory, no-new-powers evidence,
   candidate lineage, review-doc/docs-site inclusion, release-check wiring, and the preflight
   requirements before implementing another capability. It reports the next candidate as unselected
   and implementation as blocked.

32. `make project-manifest-summary-proposal-check`

   Expected outcome: validates the design-only `project.manifest.summary` proposal, including its
   manifest allowlist, strict schema contract, privacy policy, parser sketch, negative transcript
   plan, and explicit no-runtime-change boundary.

33. `make project-manifest-summary-implementation-plan-check`

   Expected outcome: validates the implementation-planning packet for `project.manifest.summary`,
   including the strict input/output schema, manifest allowlist, count-only parser plan,
   privacy/redaction plan, negative transcript plan, resource limits, and continued blocked runtime
   boundary.

34. `make project-manifest-summary-implementation-gate`

   Expected outcome: validates the bounded read-only implementation decision for
   `project.manifest.summary`, including no shell, no package-manager execution, no registry/network
   access, no dependency names, no script values, and no new powerful tool class.

35. `make project-manifest-summary-source-review-bundle`

   Expected outcome: creates an ignored focused source-review handoff under
   `var/review-packets/v0.9/project-manifest-summary-source-review/`. This attaches the
   `project.manifest.summary` manifest, implementation path, focused tests, policy-parity fixture,
   implementation record, no-new-powers evidence, command evidence, and artifact hashes for
   source-level review.

36. `make project-dependency-summary-proposal-check`

   Expected outcome: validates the design-only count-only `project.dependency.summary` proposal
   without authorizing runtime work.

37. `make project-dependency-summary-implementation-plan-check`

   Expected outcome: validates the implementation-planning packet for `project.dependency.summary`
   while keeping manifests, executors, policy rules, MCP exposure, and runtime behavior blocked.

38. `make project-dependency-summary-design-review-packet`

   Expected outcome: creates an ignored focused design-review handoff under
   `var/review-packets/v3/project-dependency-summary-design-review/`.

39. `make project-structure-summary-proposal-check`

   Expected outcome: validates the design-only `project.structure.summary` proposal and confirms no
   manifest, executor, policy rule, MCP exposure, API behavior, UI behavior, or runtime behavior is
   added.

40. `make project-structure-summary-implementation-plan-check`

   Expected outcome: validates the implementation-planning packet for `project.structure.summary`
   while keeping manifests, executors, policy rules, MCP exposure, and runtime behavior blocked.

41. `make project-structure-summary-design-review-packet`

   Expected outcome: creates an ignored focused design-review handoff under
   `var/review-packets/v3/project-structure-summary-design-review/`.

42. `make review-packet-bundle`

   Expected outcome: creates an ignored bundle under `var/review-packets/v0.2/` with release
   command outputs, `filesystem-contract-check.txt`, copied review docs,
   `review-doc-hashes.json`, `artifact-hashes.json`, and the signed-evidence demo summary when
   step 9 was run first.

43. `make review-packet-consolidated`

   Expected outcome: creates the 10-attachment-friendly packet under
   `var/review-packets/v0.2/GPT-5.5-Pro-consolidated/`, plus
   `consolidated-attachment-hashes.json` for the eight markdown attachments.

44. `make packet-redaction-scan`

   Expected outcome: scans the latest generated review bundle and consolidated packet for obvious
   private-key material, concrete admin-token assignments, sample development tokens, forbidden
   runtime file types, and non-text packet artifacts.

45. `make docs-site`

   Expected outcome: builds the ignored local docs site under `site/`, including this reproduction
   map and the security/evidence review docs.

## Where To Inspect Evidence

- Release-check transcript: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-check.txt`
- Filesystem contract check transcript: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/filesystem-contract-check.txt`
- Filesystem source-review bundle: `var/review-packets/v0.7/filesystem-source-review/`
- HTTP fetch source-review bundle: `var/review-packets/v0.7/http-fetch-source-review/`
- Signed evidence source-review bundle: `var/review-packets/v0.7/signed-evidence-source-review/`
- Policy/registry source-review bundle: `var/review-packets/v0.7/policy-registry-source-review/`
- MCP ingress source-review bundle: `var/review-packets/v0.7/mcp-ingress-source-review/`
- Review console/admin source-review bundle: `var/review-packets/v0.7/review-console-source-review/`
- Release/evidence automation source-review bundle: `var/review-packets/v0.7/release-automation-source-review/`
- git.show.commit_metadata source-review bundle: `var/review-packets/v0.9/git-commit-metadata-source-review/`
- git.show.ref_summary source-review bundle: `var/review-packets/v0.9/git-ref-summary-source-review/`
- project.manifest.summary source-review bundle: `var/review-packets/v0.9/project-manifest-summary-source-review/`
- project.dependency.summary design-review packet: `var/review-packets/v3/project-dependency-summary-design-review/`
- project.structure.summary design-review packet: `var/review-packets/v3/project-structure-summary-design-review/`
- Release evidence JSON: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-evidence.json`
- Review packet markdown: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-packet.md`
- Review packet JSON: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-packet.json`
- Test determinism gate: `make determinism-check`
- Evidence contract index: [evidence-contracts-v2.json](evidence-contracts-v2.json)
- Review document hashes: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/review-doc-hashes.json`
- Packet redaction scan: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/packet-redaction-scan.txt`
- Generated artifact hashes: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/artifact-hashes.json`
- Consolidated attachment hashes: `var/review-packets/v0.2/GPT-5.5-Pro-consolidated/consolidated-attachment-hashes.json`
- v0.6 focused dispatch packets: `var/review-packets/v0.6/dispatch/dispatch-packet-hashes.json`
- Signed evidence demo summary: `var/review-packets/v0.2/signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md`
- Negative review transcripts: `var/review-packets/v0.2/negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md`
- Negative review recipes: [negative-review-recipes.md](negative-review-recipes.md)
- v0.3 review packet: [v0.3-review-packet.md](v0.3-review-packet.md)
- v0.3 external review prompt: [v0.3-external-review-prompt.md](v0.3-external-review-prompt.md)
- External review intake and closure: [external-review-intake-and-closure.md](external-review-intake-and-closure.md)
- v0.3 boundary decision: [v0.3-boundary-decision.md](v0.3-boundary-decision.md)
- Source review closure matrix: [source-review-closure-matrix.md](source-review-closure-matrix.md)
- Internal source review pass 1: [internal-source-review-pass-1.md](internal-source-review-pass-1.md)
- Internal review packet v2: [internal-review-packet-v2.md](internal-review-packet-v2.md)
- Internal AI review workflow: [internal-ai-review-workflow.md](internal-ai-review-workflow.md)
- Autonomous sprint guardrails: [autonomous-sprint-guardrails.md](autonomous-sprint-guardrails.md)
- Reviewer finding template: [reviewer-finding-template.md](reviewer-finding-template.md)
- Reviewer finding intake: [reviewer-finding-intake.md](reviewer-finding-intake.md)
- Release evidence schema: [release-evidence-schema.md](release-evidence-schema.md)
- Review packet diff: [review-packet-diff.md](review-packet-diff.md)
- Local preview security matrix: [v0.1-security-test-matrix.md](v0.1-security-test-matrix.md)
- Executor contract set: [executor-contract-set.md](executor-contract-set.md)
- Audit integrity adversarial suite: [audit-integrity-adversarial-suite.md](audit-integrity-adversarial-suite.md)
- Filesystem executor contract: [filesystem-executor-contract.md](filesystem-executor-contract.md)
- HTTP fetch executor contract and corpus: [http-executor-contract.md](http-executor-contract.md),
  `tests/fixtures/http_canonicalization_corpus.json`
- Manifest validation suite: [manifest-validation-suite.md](manifest-validation-suite.md)
- Registry fail-closed suite: [registry-fail-closed-suite.md](registry-fail-closed-suite.md)
- Release guardrail expansion: [release-guardrail-expansion.md](release-guardrail-expansion.md)
- Packet redaction scanner: [packet-redaction-scanner.md](packet-redaction-scanner.md)
- Test determinism gate: [test-determinism-gate.md](test-determinism-gate.md)

## Reproduction Notes

- Runtime signing may be unconfigured by default. The signed-evidence demo is separate fixture
  evidence using generated local demo keys.
- The generated review bundle and demo directories are intentionally ignored and may be regenerated.
- Artifact hashes are for handoff integrity and reviewer convenience. They are not external
  notarization, custody-grade evidence, or official hosted supply-chain signing.
- If `make release-check` fails, treat the generated packet as a draft and inspect the failing
  command output before reviewing product claims.

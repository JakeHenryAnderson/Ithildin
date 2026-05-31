# Reviewer Reproduction Map

This map gives external reviewers a repeatable way to reproduce the v0.2 review packet evidence.
It is a review aid for a v0.2 review candidate for the v0.1 local-preview runtime boundary, not a
claim of production security or implementation correctness.

Run all commands from the Ithildin repo root:

```sh
cd /Users/jake/Documents/Codex/Ithildin
```

## One-Command Handoff

Run `make review-candidate` to execute the full local handoff sequence. It runs `release-check`,
`filesystem-contract-check`, `signed-evidence-demo`, `negative-review-transcripts`,
`review-packet-bundle`, `review-packet-consolidated`, packet redaction scan, and `docs-site`, then
prints the consolidated packet path. `release-check` includes `make adversarial-corpus-check`,
`make resource-limit-check`, and `make demo-scenario-pack`. Use
[demo-scenario-pack-v2.md](demo-scenario-pack-v2.md) as the concise scenario map for positive,
negative, signing, filesystem, and review-packet demos.

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

11. `make review-packet-diff OLD=old-packet NEW=new-packet`

   Expected outcome: prints added, removed, changed, and unchanged artifact counts for two generated
   packets using `artifact-hashes.json` when available.

12. `make review-packet-diff-gate OLD=old-packet NEW=new-packet`

   Expected outcome: requires `artifact-hashes.json` in both packets and fails if a previously
   comparable artifact was removed. Added or changed artifacts are reported for reviewer attention.

13. `make filesystem-contract-check`

   Expected outcome: prints secret-free local platform and filesystem capability evidence. On
   macOS/Linux with `O_NOFOLLOW`, the support status should be `supported`; Windows/WSL are reported
   as unsupported/untested for local-preview workspace/race claims.

14. `make review-packet-bundle`

   Expected outcome: creates an ignored bundle under `var/review-packets/v0.2/` with release
   command outputs, `filesystem-contract-check.txt`, copied review docs,
   `review-doc-hashes.json`, `artifact-hashes.json`, and the signed-evidence demo summary when
   step 9 was run first.

15. `make negative-review-transcripts`

   Expected outcome: creates ignored observed-denial transcripts under
   `var/review-packets/v0.2/negative-review-transcripts/`, covering traversal, symlink escape,
   stale-base patch apply, private redirect, unknown principal, disabled principal, and replayed
   approval.

16. `make review-packet-consolidated`

   Expected outcome: creates the 10-attachment-friendly packet under
   `var/review-packets/v0.2/GPT-5.5-Pro-consolidated/`, plus
   `consolidated-attachment-hashes.json` for the eight markdown attachments.

17. `make packet-redaction-scan`

   Expected outcome: scans the latest generated review bundle and consolidated packet for obvious
   private-key material, concrete admin-token assignments, sample development tokens, forbidden
   runtime file types, and non-text packet artifacts.

18. `make docs-site`

   Expected outcome: builds the ignored local docs site under `site/`, including this reproduction
   map and the security/evidence review docs.

## Where To Inspect Evidence

- Release-check transcript: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-check.txt`
- Filesystem contract check transcript: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/filesystem-contract-check.txt`
- Release evidence JSON: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-evidence.json`
- Review packet markdown: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-packet.md`
- Review packet JSON: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-packet.json`
- Test determinism gate: `make determinism-check`
- Evidence contract index: [evidence-contracts-v2.json](evidence-contracts-v2.json)
- Review document hashes: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/review-doc-hashes.json`
- Packet redaction scan: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/packet-redaction-scan.txt`
- Generated artifact hashes: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/artifact-hashes.json`
- Consolidated attachment hashes: `var/review-packets/v0.2/GPT-5.5-Pro-consolidated/consolidated-attachment-hashes.json`
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

- Runtime audit signing and manifest-lock signing may be unconfigured by default. The signed
  evidence demo is separate fixture evidence using generated local demo keys.
- The generated review bundle and demo directories are intentionally ignored and may be regenerated.
- Artifact hashes are for handoff integrity and reviewer convenience. They are not external
  notarization, custody-grade evidence, or official hosted supply-chain signing.
- If `make release-check` fails, treat the generated packet as a draft and inspect the failing
  command output before reviewing product claims.

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
`review-packet-bundle`, `review-packet-consolidated`, and `docs-site`, then prints the consolidated
packet path.

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

   Expected outcome: passes after manifest-lock verification, policy fixtures, pytest, ruff, mypy,
   UI typecheck, docs-site build, and UI production build.

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

5. `make signed-evidence-demo`

   Expected outcome: creates ignored non-production fixture evidence under
   `var/review-packets/v0.2/signed-evidence-demo/`. The demo summary reports verified local audit
   export signing, verified manifest-lock signing, a tamper-failing audit bundle, and SHA-256
   digests for the generated demo artifacts.

6. `make review-packet-diff OLD=old-packet NEW=new-packet`

   Expected outcome: prints added, removed, changed, and unchanged artifact counts for two generated
   packets using `artifact-hashes.json` when available.

5. `make filesystem-contract-check`

   Expected outcome: prints secret-free local platform and filesystem capability evidence. On
   macOS/Linux with `O_NOFOLLOW`, the support status should be `supported`; Windows/WSL are reported
   as unsupported/untested for local-preview workspace/race claims.

6. `make review-packet-bundle`

   Expected outcome: creates an ignored bundle under `var/review-packets/v0.2/` with release
   command outputs, `filesystem-contract-check.txt`, copied review docs,
   `review-doc-hashes.json`, `artifact-hashes.json`, and the signed-evidence demo summary when
   step 4 was run first.

7. `make negative-review-transcripts`

   Expected outcome: creates ignored observed-denial transcripts under
   `var/review-packets/v0.2/negative-review-transcripts/`, covering traversal, symlink escape,
   stale-base patch apply, private redirect, unknown principal, disabled principal, and replayed
   approval.

8. `make review-packet-consolidated`

   Expected outcome: creates the 10-attachment-friendly packet under
   `var/review-packets/v0.2/GPT-5.5-Pro-consolidated/`, plus
   `consolidated-attachment-hashes.json` for the eight markdown attachments.

9. `make docs-site`

   Expected outcome: builds the ignored local docs site under `site/`, including this reproduction
   map and the security/evidence review docs.

## Where To Inspect Evidence

- Release-check transcript: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-check.txt`
- Filesystem contract check transcript: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/filesystem-contract-check.txt`
- Release evidence JSON: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-evidence.json`
- Review packet markdown: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-packet.md`
- Review packet JSON: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-packet.json`
- Review document hashes: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/review-doc-hashes.json`
- Generated artifact hashes: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/artifact-hashes.json`
- Consolidated attachment hashes: `var/review-packets/v0.2/GPT-5.5-Pro-consolidated/consolidated-attachment-hashes.json`
- Signed evidence demo summary: `var/review-packets/v0.2/signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md`
- Negative review transcripts: `var/review-packets/v0.2/negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md`
- Negative review recipes: [negative-review-recipes.md](negative-review-recipes.md)
- v0.3 review packet: [v0.3-review-packet.md](v0.3-review-packet.md)
- v0.3 external review prompt: [v0.3-external-review-prompt.md](v0.3-external-review-prompt.md)
- External review intake and closure: [external-review-intake-and-closure.md](external-review-intake-and-closure.md)
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
- Manifest validation suite: [manifest-validation-suite.md](manifest-validation-suite.md)
- Registry fail-closed suite: [registry-fail-closed-suite.md](registry-fail-closed-suite.md)
- Release guardrail expansion: [release-guardrail-expansion.md](release-guardrail-expansion.md)

## Reproduction Notes

- Runtime audit signing and manifest-lock signing may be unconfigured by default. The signed
  evidence demo is separate fixture evidence using generated local demo keys.
- The generated review bundle and demo directories are intentionally ignored and may be regenerated.
- Artifact hashes are for handoff integrity and reviewer convenience. They are not external
  notarization, custody-grade evidence, or official hosted supply-chain signing.
- If `make release-check` fails, treat the generated packet as a draft and inspect the failing
  command output before reviewing product claims.

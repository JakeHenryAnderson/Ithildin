# Reviewer Reproduction Map

This map gives external reviewers a repeatable way to reproduce the v0.2 review packet evidence.
It is a review aid for a v0.2 review candidate for the v0.1 local-preview runtime boundary, not a
claim of production security or implementation correctness.

Run all commands from the Ithildin repo root:

```sh
cd /Users/jake/Documents/Codex/Ithildin
```

## Command Sequence

1. `make release-check`

   Expected outcome: passes after manifest-lock verification, policy fixtures, pytest, ruff, mypy,
   UI typecheck, docs-site build, and UI production build.

2. `make release-evidence`

   Expected outcome: prints secret-free JSON showing a clean or intentionally noted git state,
   current manifest lock, tool count, policy/principal/workspace status, audit verification state,
   local-only security posture, review-doc hashes, and release-check transcript fields.

3. `make release-packet`

   Expected outcome: prints a markdown review summary with repo root, commit, dirty state, trust
   evidence, deferred boundaries, review-doc hashes, and the note that the packet command does not
   itself run `make release-check`.

4. `make signed-evidence-demo`

   Expected outcome: creates ignored non-production fixture evidence under
   `var/review-packets/v0.2/signed-evidence-demo/`. The demo summary reports verified local audit
   export signing, verified manifest-lock signing, a tamper-failing audit bundle, and SHA-256
   digests for the generated demo artifacts.

5. `make review-packet-bundle`

   Expected outcome: creates an ignored bundle under `var/review-packets/v0.2/` with release
   command outputs, copied review docs, `review-doc-hashes.json`, `artifact-hashes.json`, and the
   signed-evidence demo summary when step 4 was run first.

6. `make review-packet-consolidated`

   Expected outcome: creates the 10-attachment-friendly packet under
   `var/review-packets/v0.2/GPT-5.5-Pro-consolidated/`, plus
   `consolidated-attachment-hashes.json` for the eight markdown attachments.

7. `make docs-site`

   Expected outcome: builds the ignored local docs site under `site/`, including this reproduction
   map and the security/evidence review docs.

## Where To Inspect Evidence

- Release-check transcript: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-check.txt`
- Release evidence JSON: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-evidence.json`
- Review packet markdown: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-packet.md`
- Review packet JSON: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/release-packet.json`
- Review document hashes: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/review-doc-hashes.json`
- Generated artifact hashes: `var/review-packets/v0.2/ithildin-v0.2-review-packet-*/artifact-hashes.json`
- Consolidated attachment hashes: `var/review-packets/v0.2/GPT-5.5-Pro-consolidated/consolidated-attachment-hashes.json`
- Signed evidence demo summary: `var/review-packets/v0.2/signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md`
- Negative review recipes: [negative-review-recipes.md](negative-review-recipes.md)
- Source review closure matrix: [source-review-closure-matrix.md](source-review-closure-matrix.md)
- Local preview security matrix: [v0.1-security-test-matrix.md](v0.1-security-test-matrix.md)

## Reproduction Notes

- Runtime audit signing and manifest-lock signing may be unconfigured by default. The signed
  evidence demo is separate fixture evidence using generated local demo keys.
- The generated review bundle and demo directories are intentionally ignored and may be regenerated.
- Artifact hashes are for handoff integrity and reviewer convenience. They are not external
  notarization, custody-grade evidence, or official hosted supply-chain signing.
- If `make release-check` fails, treat the generated packet as a draft and inspect the failing
  command output before reviewing product claims.

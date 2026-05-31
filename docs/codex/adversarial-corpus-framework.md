# Adversarial Corpus Framework

Task 142 adds a small manifest-backed framework for tracking Ithildin adversarial corpora without
adding tool powers or executor behavior.

The corpus manifest lives at `tests/fixtures/adversarial_corpus_manifest.json`. Each entry records:

- stable corpus ID;
- reviewed area;
- repo-relative artifact;
- command to run the relevant focused checks;
- implementation status;
- categories covered by that corpus.

Run the gate with:

```sh
make adversarial-corpus-check
uv run python scripts/adversarial_corpus_check.py --json
```

`make release-check` includes this gate. The checker fails if the manifest is missing, malformed,
has duplicate IDs, references missing artifacts, uses absolute or parent-relative artifact paths,
uses unknown statuses, or declares empty/duplicate categories.

## Initial Corpora

- `http-canonicalization-v2`: URL parsing, allowlist, redirect, DNS, and safe-error cases for
  `http.fetch`.
- `filesystem-race-v2`: path resolution, symlink, hardlink, stale-base, and safe-error evidence for
  filesystem reads/proposals/apply.
- `audit-integrity-v2`: audit hash-chain, SQLite/JSONL drift, export replay, signed-bundle, and
  safe-error checks.
- `negative-review-transcripts-v2`: observed fixture denial transcripts for path, HTTP, principal,
  approval, and evidence-tamper cases.

This framework is a review/evidence index. It is not a fuzzing engine, not an external audit, and
not a claim that the corpus proves complete coverage of an attack class.

# Script and Gate Instructions

These instructions extend the repository root `AGENTS.md` for files under `scripts/`.

- Prefer the standard library and existing report, hashing, path-safety, and fixture helpers.
- Checks must fail closed on missing, malformed, contradictory, or stale required evidence. Do not
  convert an unknown state into success for convenience.
- Keep generators deterministic. Generated artifacts must identify their inputs, boundaries, and
  what they do not prove; never encode approval or closure merely because generation succeeded.
- Preserve path confinement, redaction, manifest integrity, commit/dirty-state reporting, and
  negative-fixture coverage where the touched workflow relies on them.
- Add focused tests for success and negative cases. Run the specific script/check first, then the
  relevant pytest slice, lint, and the broader release gate when shared behavior or handoff evidence
  changes.
- A script may prepare or validate evidence but may not grant runtime authority, change governed
  tool count, or broaden the product boundary without the root capability process.

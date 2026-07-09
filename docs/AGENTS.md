# Documentation and Evidence Instructions

These instructions extend the repository root `AGENTS.md` for files under `docs/`.

- Preserve the distinction between planning, implementation, execution, approval, disposition,
  closure, and release. A packet or passing check is not evidence that a later state occurred.
- State observed facts separately from recommendations. Use the current governed tool count and
  active enterprise route from checked sources rather than copying old packet wording.
- Historical ERG artifacts remain lineage, not current routing authority. Do not delete or rewrite
  historical review evidence merely to simplify current navigation.
- Label generated, fixture, dry-run, internal-review, external-pending, and human-attested evidence
  accurately. Never present rehearsal or proxy review as independent approval.
- Keep commands runnable from the repository root. Verify links, referenced targets, and status
  claims with the narrowest relevant check.
- Do not edit generated files under `var/` directly. Change their source document or generator and
  regenerate only when the task requires refreshed artifacts.

For docs-only changes, run the root docs checks. If a change affects release status, review routing,
or generated evidence, also run the focused gate for that lane and review the resulting diff.

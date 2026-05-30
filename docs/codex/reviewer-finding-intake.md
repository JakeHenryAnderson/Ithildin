# Reviewer Finding Intake

Use `make reviewer-findings-check` to validate structured internal AI/subagent, external, and human
review findings before they affect the source-review closure matrix.

Finding records live under `docs/codex/findings/` as Markdown files. The directory may be empty. If
it is empty, the check passes with `0 finding(s)`.

## Required Fields

Each finding file must use the same field names as
[reviewer-finding-template.md](reviewer-finding-template.md):

- Finding ID
- Severity
- Area
- Affected files/functions
- Claim being tested
- Observed behavior
- Risk
- Recommended fix
- Blocking status
- Disposition
- Verification notes

Allowed finding ID prefixes are `ISR`, `EXT`, `SUB`, `AI`, and `V03`, followed by a three-digit
number. Allowed severities are `critical`, `high`, `medium`, `low`, and `informational`.

## Workflow

1. Convert reviewer notes into one Markdown file per finding.
2. Run `make reviewer-findings-check`.
3. Update [source-review-closure-matrix.md](source-review-closure-matrix.md) only after the finding
   file validates.
4. Stop autonomous implementation if a critical/high finding is open or if a finding changes the
   product boundary.

The check rejects duplicate IDs, missing required fields, invalid severities/statuses/dispositions,
and obvious secret-like markers. It is a structure gate, not a substitute for source review.

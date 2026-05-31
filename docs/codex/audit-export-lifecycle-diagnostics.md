# Audit Export Lifecycle Diagnostics

Task 132 expands local audit diagnostics with read-only lifecycle evidence. This does not add
retention deletion, repair, rollback, notarization, hosted custody, or broad filesystem behavior.

## Evidence Reported

`/audit-events/diagnostics` and `make audit-diagnostics` now report:

- SQLite database path, existence, size, and event count;
- JSONL path, existence, size, line count, parse error if present, and last JSONL event hash;
- audit chain verification status, first failure, event count, and head hash;
- lifecycle status: `clean`, `not_initialized`, `verification_failed`, `recovery_required`, or
  `ambiguous`;
- local retention mode: `local_manual`;
- explicit `retention_mutation_supported: false` and `repair_supported: false`;
- safe operator recommendation text.

## Lifecycle Meaning

- `clean`: SQLite and JSONL counts/head hashes agree and chain verification is valid.
- `not_initialized`: no local audit database exists yet.
- `verification_failed`: the canonical SQLite audit chain failed verification.
- `recovery_required`: SQLite verification is valid, but JSONL evidence does not match SQLite count
  or head hash.
- `ambiguous`: local files are missing or unreadable in a way that prevents confident lifecycle
  classification.

These diagnostics are intentionally descriptive. They do not rewrite evidence, complete exports,
truncate audit logs, repair chains, or claim custody-grade retention.

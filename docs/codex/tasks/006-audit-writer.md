# Task 006 - Audit Writer

## Goal

Record evidence for tool calls, policy decisions, approvals, and executions.

## Scope

- SQLite audit table.
- Append-only JSONL audit file.
- Hash chain.
- Redaction hooks.

## Acceptance Criteria

- Every event has an ID, timestamp, event type, request ID, and hash.
- Each JSONL record includes `prev_event_hash`.
- Audit write failure blocks governed execution.
- Redaction removes configured sensitive fields before persistence.
- Tests cover hash chaining, missing fields, and redaction.


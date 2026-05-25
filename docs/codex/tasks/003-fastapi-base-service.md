# Task 003 - FastAPI Base Service

## Goal

Create the base backend service for auth, config, persistence, approvals, registry, and audit APIs.

## Scope

- Health endpoint.
- Local bootstrap admin token.
- SQLite initialization.
- Config loading.
- Structured logging.

## Acceptance Criteria

- `GET /healthz` returns service health.
- Missing required config fails startup.
- Admin endpoints require the local bootstrap token.
- SQLite database is initialized idempotently.
- Tests cover health, auth success, and auth failure.


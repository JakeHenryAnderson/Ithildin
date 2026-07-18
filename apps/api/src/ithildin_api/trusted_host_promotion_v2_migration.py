"""Atomic version-2 approval and trusted-host promotion migration."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DATABASE_SCHEMA_VERSION = "2"
MINIMUM_WRITER_VERSION = "2"
APPROVAL_CONTRACT_VERSION = "2"
PROMOTION_AUTHORITY_SCHEMA_VERSION = "1"

TRUSTED_HOST_PROMOTION_TOOL = "trusted_host.promotion.stage"

LEGACY_APPROVAL_STATUSES = (
    "legacy_unbound",
    "legacy_denied",
    "legacy_expired",
    "legacy_executed",
    "legacy_failed",
    "legacy_superseded",
)
V2_APPROVAL_STATUSES = (
    "v2_created",
    "v2_pending",
    "v2_approved",
    "v2_executing",
    "v2_executed",
    "v2_denied",
    "v2_expired",
    "v2_superseded",
    "v2_failed",
)
LEGACY_PROPOSAL_STATUSES = (
    "legacy_unbound",
    "legacy_completed",
    "legacy_failed",
)
V2_PROPOSAL_STATUSES = (
    "v2_approval_required",
    "v2_completion_evidence_pending",
    "v2_approval_evidence_failed",
    "v2_authority_stale",
    "v2_failed",
    "v2_completed",
)
LEGACY_ATTEMPT_STATUSES = (
    "legacy_prepared",
    "legacy_staged",
    "legacy_recovery_required",
    "legacy_failed",
    "legacy_completed",
)
V2_ATTEMPT_STATUSES = (
    "v2_prepared",
    "v2_staged",
    "v2_placement_evidence_recovery_required",
    "v2_failed",
    "v2_completed",
)


class DatabaseMigrationError(RuntimeError):
    """Raised when the database cannot be opened by this writer safely."""


def initialize_or_migrate_database(db_path: Path) -> None:
    """Create or atomically migrate the coordinated v2 persistence contract."""

    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("BEGIN IMMEDIATE")
        _create_metadata_table(connection)
        current = _metadata_value(connection, "schema_version")
        minimum_writer = _metadata_value(connection, "minimum_writer_version")
        _validate_version_metadata(current=current, minimum_writer=minimum_writer)

        if current == DATABASE_SCHEMA_VERSION:
            _verify_v2_schema(connection)
        elif current in {None, "0", "1"}:
            _migrate_tables(connection)
        else:  # pragma: no cover - guarded above, retained as a fail-closed fence
            raise DatabaseMigrationError(f"unsupported database schema version: {current}")

        _set_metadata(connection, "schema_version", DATABASE_SCHEMA_VERSION)
        _set_metadata(connection, "minimum_writer_version", MINIMUM_WRITER_VERSION)
        _verify_v2_schema(connection)
        connection.execute("COMMIT")
    except (DatabaseMigrationError, sqlite3.DatabaseError):
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def verify_database_v2(db_path: Path) -> None:
    """Reject use of a store before the coordinated migration has completed."""

    try:
        with sqlite3.connect(db_path) as connection:
            current = _metadata_value(connection, "schema_version")
            minimum_writer = _metadata_value(connection, "minimum_writer_version")
            _validate_version_metadata(current=current, minimum_writer=minimum_writer)
            if current != DATABASE_SCHEMA_VERSION or minimum_writer != MINIMUM_WRITER_VERSION:
                raise DatabaseMigrationError("database v2 migration has not completed")
            _verify_v2_schema(connection)
    except sqlite3.DatabaseError as exc:
        raise DatabaseMigrationError("database v2 schema verification failed") from exc


def _validate_version_metadata(*, current: str | None, minimum_writer: str | None) -> None:
    for label, value in (("schema", current), ("minimum writer", minimum_writer)):
        if value is None:
            continue
        try:
            numeric = int(value)
        except ValueError as exc:
            raise DatabaseMigrationError(f"invalid database {label} version") from exc
        if numeric > int(DATABASE_SCHEMA_VERSION):
            raise DatabaseMigrationError(f"database {label} version is newer than this writer")
        if numeric < 0:
            raise DatabaseMigrationError(f"invalid database {label} version")


def _migrate_tables(connection: sqlite3.Connection) -> None:
    approval_exists = _table_exists(connection, "approvals")
    proposal_exists = _table_exists(connection, "trusted_host_promotion_proposals")
    attempt_exists = _table_exists(connection, "trusted_host_promotion_attempts")

    if approval_exists:
        connection.execute("ALTER TABLE approvals RENAME TO approvals_v1")
    if proposal_exists:
        connection.execute(
            "ALTER TABLE trusted_host_promotion_proposals "
            "RENAME TO trusted_host_promotion_proposals_v1"
        )
    if attempt_exists:
        connection.execute(
            "ALTER TABLE trusted_host_promotion_attempts "
            "RENAME TO trusted_host_promotion_attempts_v1"
        )

    _create_v2_tables(connection)

    if approval_exists:
        connection.execute(
            """
            INSERT INTO approvals (
                approval_id, request_id, request_hash, principal_json, tool_name,
                resource_json, status, summary, expires_at, one_time_scope_json,
                metadata_json, created_at, updated_at, approval_contract_version,
                requester_principal_id, requester_principal_generation,
                promotion_authority_hash, promotion_request_hash, decided_at,
                deciding_principal_id, deciding_principal_generation,
                decision_reason, decision_reason_hash,
                decision_authority_snapshot_hash, decision_hash,
                executor_principal_id, executor_principal_generation,
                legacy_decision_json
            )
            SELECT
                approval_id, request_id, request_hash, principal_json, tool_name,
                resource_json,
                CASE status
                    WHEN 'denied' THEN 'legacy_denied'
                    WHEN 'expired' THEN 'legacy_expired'
                    WHEN 'executed' THEN 'legacy_executed'
                    WHEN 'failed' THEN 'legacy_failed'
                    WHEN 'superseded' THEN 'legacy_superseded'
                    ELSE 'legacy_unbound'
                END,
                summary, expires_at, one_time_scope_json, metadata_json,
                created_at, updated_at, '1', NULL, NULL, NULL, NULL, NULL,
                NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                json_object(
                    'decided_by', decided_by,
                    'decision_reason', decision_reason
                )
            FROM approvals_v1
            """
        )
        connection.execute("DROP TABLE approvals_v1")

    if proposal_exists:
        connection.execute(
            """
            INSERT INTO trusted_host_promotion_proposals (
                proposal_id, request_id, status, created_at, updated_at,
                workspace_id, sandbox_descriptor_id, sandbox_descriptor_hash,
                sandbox_id, source_artifact_label, host_staging_label,
                artifact_sha256, artifact_size_bytes, artifact_media_label,
                proposal_hash, metadata_json, authority_schema_version,
                authority_snapshot_json, authority_snapshot_hash,
                requester_principal_id, requester_principal_generation,
                executor_principal_id, executor_principal_generation
            )
            SELECT
                proposal_id, request_id,
                CASE status
                    WHEN 'completed' THEN 'legacy_completed'
                    WHEN 'failed' THEN 'legacy_failed'
                    ELSE 'legacy_unbound'
                END,
                created_at, updated_at, workspace_id, sandbox_descriptor_id,
                sandbox_descriptor_hash, sandbox_id, source_artifact_label,
                host_staging_label, artifact_sha256, artifact_size_bytes,
                artifact_media_label, proposal_hash, metadata_json,
                NULL, NULL, NULL, NULL, NULL, NULL, NULL
            FROM trusted_host_promotion_proposals_v1
            """
        )
        connection.execute("DROP TABLE trusted_host_promotion_proposals_v1")

    if attempt_exists:
        connection.execute(
            """
            INSERT INTO trusted_host_promotion_attempts (
                attempt_id, approval_id, proposal_id, request_id, workspace_id,
                host_staging_label, artifact_sha256, staged_sha256, status,
                failure_reason, created_at, updated_at, metadata_json,
                record_version, authority_snapshot_hash,
                executor_principal_id, executor_principal_generation
            )
            SELECT
                attempt_id, approval_id, proposal_id, request_id, workspace_id,
                host_staging_label, artifact_sha256, staged_sha256,
                CASE status
                    WHEN 'prepared' THEN 'legacy_prepared'
                    WHEN 'staged' THEN 'legacy_staged'
                    WHEN 'recovery_required' THEN 'legacy_recovery_required'
                    WHEN 'completed' THEN 'legacy_completed'
                    ELSE 'legacy_failed'
                END,
                failure_reason, created_at, updated_at, metadata_json,
                '1', NULL, NULL, NULL
            FROM trusted_host_promotion_attempts_v1
            """
        )
        connection.execute("DROP TABLE trusted_host_promotion_attempts_v1")


def _create_v2_tables(connection: sqlite3.Connection) -> None:
    legacy_approval = _sql_values(LEGACY_APPROVAL_STATUSES)
    v2_approval = _sql_values(V2_APPROVAL_STATUSES)
    legacy_proposal = _sql_values(LEGACY_PROPOSAL_STATUSES)
    v2_proposal = _sql_values(V2_PROPOSAL_STATUSES)
    legacy_attempt = _sql_values(LEGACY_ATTEMPT_STATUSES)
    v2_attempt = _sql_values(V2_ATTEMPT_STATUSES)

    connection.execute(
        f"""
        CREATE TABLE approvals (
            approval_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            request_hash TEXT NOT NULL,
            principal_json TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            resource_json TEXT NOT NULL,
            status TEXT NOT NULL,
            summary TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            one_time_scope_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            approval_contract_version TEXT NOT NULL,
            requester_principal_id TEXT,
            requester_principal_generation TEXT,
            promotion_authority_hash TEXT,
            promotion_request_hash TEXT,
            decided_at TEXT,
            deciding_principal_id TEXT,
            deciding_principal_generation TEXT,
            decision_reason TEXT CHECK(decision_reason IS NULL OR length(decision_reason) <= 500),
            decision_reason_hash TEXT,
            decision_authority_snapshot_hash TEXT,
            decision_hash TEXT,
            executor_principal_id TEXT,
            executor_principal_generation TEXT,
            legacy_decision_json TEXT,
            CHECK (
                (approval_contract_version = '1' AND status IN ({legacy_approval})) OR
                (approval_contract_version = '2' AND status IN ({v2_approval}))
            ),
            CHECK (
                (approval_contract_version = '1' AND requester_principal_id IS NULL
                    AND requester_principal_generation IS NULL) OR
                (approval_contract_version = '2' AND requester_principal_id IS NOT NULL
                    AND requester_principal_generation IS NOT NULL)
            ),
            CHECK (
                (approval_contract_version = '2' AND tool_name = '{TRUSTED_HOST_PROMOTION_TOOL}'
                    AND promotion_authority_hash IS NOT NULL
                    AND promotion_request_hash IS NOT NULL) OR
                (NOT (approval_contract_version = '2'
                    AND tool_name = '{TRUSTED_HOST_PROMOTION_TOOL}')
                    AND promotion_authority_hash IS NULL
                    AND promotion_request_hash IS NULL)
            ),
            CHECK (
                (status IN ('v2_approved', 'v2_denied', 'v2_executing',
                    'v2_executed', 'v2_failed')
                    AND decided_at IS NOT NULL
                    AND deciding_principal_id IS NOT NULL
                    AND deciding_principal_generation IS NOT NULL
                    AND decision_reason_hash IS NOT NULL
                    AND decision_hash IS NOT NULL) OR
                (status NOT IN ('v2_approved', 'v2_denied', 'v2_executing',
                    'v2_executed', 'v2_failed')
                    AND decided_at IS NULL
                    AND deciding_principal_id IS NULL
                    AND deciding_principal_generation IS NULL
                    AND decision_reason IS NULL
                    AND decision_reason_hash IS NULL
                    AND decision_authority_snapshot_hash IS NULL
                    AND decision_hash IS NULL) OR
                (status IN ('v2_expired', 'v2_superseded')
                    AND decided_at IS NOT NULL
                    AND deciding_principal_id IS NOT NULL
                    AND deciding_principal_generation IS NOT NULL
                    AND decision_reason_hash IS NOT NULL
                    AND decision_hash IS NOT NULL)
            ),
            CHECK (
                (approval_contract_version = '1' AND legacy_decision_json IS NOT NULL) OR
                (approval_contract_version = '2' AND legacy_decision_json IS NULL)
            ),
            CHECK (
                (tool_name = '{TRUSTED_HOST_PROMOTION_TOOL}'
                    AND decision_hash IS NOT NULL
                    AND decision_authority_snapshot_hash = promotion_authority_hash) OR
                (tool_name = '{TRUSTED_HOST_PROMOTION_TOOL}' AND decision_hash IS NULL) OR
                (tool_name != '{TRUSTED_HOST_PROMOTION_TOOL}'
                    AND decision_authority_snapshot_hash IS NULL)
            ),
            CHECK (
                (executor_principal_id IS NULL
                    AND executor_principal_generation IS NULL) OR
                (executor_principal_id IS NOT NULL
                    AND executor_principal_generation IS NOT NULL)
            )
        )
        """
    )
    connection.execute(
        "CREATE INDEX approvals_status_updated_idx ON approvals(status, updated_at DESC)"
    )
    connection.execute(
        f"""
        CREATE TABLE trusted_host_promotion_proposals (
            proposal_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            sandbox_descriptor_id TEXT NOT NULL,
            sandbox_descriptor_hash TEXT NOT NULL,
            sandbox_id TEXT NOT NULL,
            source_artifact_label TEXT NOT NULL,
            host_staging_label TEXT NOT NULL,
            artifact_sha256 TEXT NOT NULL,
            artifact_size_bytes INTEGER NOT NULL,
            artifact_media_label TEXT NOT NULL,
            proposal_hash TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            authority_schema_version TEXT,
            authority_snapshot_json TEXT,
            authority_snapshot_hash TEXT,
            requester_principal_id TEXT,
            requester_principal_generation TEXT,
            executor_principal_id TEXT,
            executor_principal_generation TEXT,
            CHECK (
                (authority_schema_version IS NULL AND status IN ({legacy_proposal})
                    AND authority_snapshot_json IS NULL
                    AND authority_snapshot_hash IS NULL
                    AND requester_principal_id IS NULL
                    AND requester_principal_generation IS NULL) OR
                (authority_schema_version = '1' AND status IN ({v2_proposal})
                    AND authority_snapshot_json IS NOT NULL
                    AND authority_snapshot_hash IS NOT NULL
                    AND requester_principal_id IS NOT NULL
                    AND requester_principal_generation IS NOT NULL)
            ),
            CHECK (
                (executor_principal_id IS NULL
                    AND executor_principal_generation IS NULL) OR
                (executor_principal_id IS NOT NULL
                    AND executor_principal_generation IS NOT NULL)
            )
        )
        """
    )
    connection.execute(
        "CREATE INDEX promotion_authority_hash_idx ON "
        "trusted_host_promotion_proposals(authority_snapshot_hash)"
    )
    connection.execute(
        f"""
        CREATE TABLE trusted_host_promotion_attempts (
            attempt_id TEXT PRIMARY KEY,
            approval_id TEXT NOT NULL UNIQUE,
            proposal_id TEXT NOT NULL,
            request_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            host_staging_label TEXT NOT NULL,
            artifact_sha256 TEXT NOT NULL,
            staged_sha256 TEXT,
            status TEXT NOT NULL,
            failure_reason TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            record_version TEXT NOT NULL,
            authority_snapshot_hash TEXT,
            executor_principal_id TEXT,
            executor_principal_generation TEXT,
            CHECK (
                (record_version = '1' AND status IN ({legacy_attempt})
                    AND authority_snapshot_hash IS NULL
                    AND executor_principal_id IS NULL
                    AND executor_principal_generation IS NULL) OR
                (record_version = '2' AND status IN ({v2_attempt})
                    AND authority_snapshot_hash IS NOT NULL
                    AND executor_principal_id IS NOT NULL
                    AND executor_principal_generation IS NOT NULL)
            )
        )
        """
    )


def _verify_v2_schema(connection: sqlite3.Connection) -> None:
    required = {
        "approvals": {
            "approval_contract_version",
            "requester_principal_generation",
            "decision_hash",
            "executor_principal_generation",
        },
        "trusted_host_promotion_proposals": {
            "authority_schema_version",
            "authority_snapshot_hash",
            "requester_principal_generation",
        },
        "trusted_host_promotion_attempts": {
            "record_version",
            "authority_snapshot_hash",
            "executor_principal_generation",
        },
    }
    for table, expected_columns in required.items():
        if not _table_exists(connection, table):
            raise DatabaseMigrationError(f"database v2 table is missing: {table}")
        columns = {
            str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        missing = expected_columns - columns
        if missing:
            raise DatabaseMigrationError(f"database v2 table is incomplete: {table}")
    required_schema_fragments = {
        "approvals": {
            "approval_contract_version = '2'",
            "status IN ('v2_created', 'v2_pending'",
            "status IN ('legacy_unbound', 'legacy_denied'",
            "decision_authority_snapshot_hash = promotion_authority_hash",
            "executor_principal_id IS NULL",
        },
        "trusted_host_promotion_proposals": {
            "authority_schema_version = '1'",
            "status IN ('v2_approval_required'",
            "status IN ('legacy_unbound'",
        },
        "trusted_host_promotion_attempts": {
            "record_version = '2'",
            "status IN ('v2_prepared'",
            "status IN ('legacy_prepared'",
        },
    }
    for table, expected_fragments in required_schema_fragments.items():
        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        schema_sql = str(row[0]) if row is not None and row[0] is not None else ""
        missing_fragments = sorted(
            fragment for fragment in expected_fragments if fragment not in schema_sql
        )
        if missing_fragments:
            raise DatabaseMigrationError(f"database v2 constraints are incomplete: {table}")


def _create_metadata_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )


def _metadata_value(connection: sqlite3.Connection, key: str) -> str | None:
    if not _table_exists(connection, "app_metadata"):
        return None
    row = connection.execute(
        "SELECT value FROM app_metadata WHERE key = ?",
        (key,),
    ).fetchone()
    return str(row[0]) if row is not None else None


def _set_metadata(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        """
        INSERT INTO app_metadata (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _sql_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)

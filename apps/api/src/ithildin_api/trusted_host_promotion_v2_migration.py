"""Atomic version-2 approval and trusted-host promotion migration."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ithildin_api.database_migration_backup import (
    DatabaseBackupError,
    ensure_pre_v4_backup,
    ensure_pre_v5_backup,
)

DATABASE_SCHEMA_VERSION = "5"
MINIMUM_WRITER_VERSION = "5"
APPROVAL_CONTRACT_VERSION = "2"
PROMOTION_AUTHORITY_SCHEMA_VERSION = "1"

V2_TABLE_COLUMNS = {
    "approvals": (
        "approval_id",
        "request_id",
        "request_hash",
        "principal_json",
        "tool_name",
        "resource_json",
        "status",
        "summary",
        "expires_at",
        "one_time_scope_json",
        "metadata_json",
        "created_at",
        "updated_at",
        "approval_contract_version",
        "requester_principal_id",
        "requester_principal_generation",
        "promotion_authority_hash",
        "promotion_request_hash",
        "decided_at",
        "deciding_principal_id",
        "deciding_principal_generation",
        "decision_reason",
        "decision_reason_hash",
        "decision_authority_snapshot_hash",
        "decision_hash",
        "executor_principal_id",
        "executor_principal_generation",
        "legacy_decision_json",
    ),
    "trusted_host_promotion_proposals": (
        "proposal_id",
        "request_id",
        "status",
        "created_at",
        "updated_at",
        "workspace_id",
        "sandbox_descriptor_id",
        "sandbox_descriptor_hash",
        "sandbox_id",
        "source_artifact_label",
        "host_staging_label",
        "artifact_sha256",
        "artifact_size_bytes",
        "artifact_media_label",
        "proposal_hash",
        "metadata_json",
        "authority_schema_version",
        "authority_snapshot_json",
        "authority_snapshot_hash",
        "requester_principal_id",
        "requester_principal_generation",
        "executor_principal_id",
        "executor_principal_generation",
    ),
    "trusted_host_promotion_attempts": (
        "attempt_id",
        "approval_id",
        "proposal_id",
        "request_id",
        "workspace_id",
        "host_staging_label",
        "artifact_sha256",
        "staged_sha256",
        "status",
        "failure_reason",
        "created_at",
        "updated_at",
        "metadata_json",
        "record_version",
        "authority_snapshot_hash",
        "executor_principal_id",
        "executor_principal_generation",
    ),
}

MISSION_TABLE_COLUMNS = {
    "missions": (
        "mission_id",
        "requester_principal_id",
        "requester_identity_generation",
        "client_request_id",
        "admission_request_digest",
        "authority_snapshot_json",
        "authority_snapshot_hash",
        "target_node_id",
        "target_node_principal_id",
        "workspace_id",
        "configuration_generation",
        "configuration_digest",
        "policy_digest",
        "manifest_lock_digest",
        "mission_template_id",
        "template_registry_generation",
        "template_payload_digest",
        "envelope_digest",
        "requested_timeout_seconds",
        "lifecycle_state",
        "lifecycle_revision",
        "created_at",
        "updated_at",
        "admitted_at",
    ),
    "mission_audit_evidence_bindings": (
        "audit_event_id",
        "audit_event_hash",
        "owner_kind",
        "owner_id",
        "request_digest",
        "bound_at",
    ),
    "mission_transition_attempts": (
        "transition_id",
        "mission_id",
        "transition_kind",
        "prior_lifecycle_state",
        "prior_lifecycle_revision",
        "proposed_lifecycle_state",
        "proposed_lifecycle_revision",
        "request_digest",
        "safe_metadata_json",
        "evidence_status",
        "audit_event_id",
        "audit_event_hash",
        "failure_reason_code",
        "created_at",
        "finalized_at",
    ),
    "mission_claims": (
        "claim_id",
        "mission_id",
        "transition_id",
        "node_id",
        "node_identity_key_id",
        "envelope_digest",
        "authority_snapshot_json",
        "authority_snapshot_hash",
        "lifecycle_revision",
        "claim_status",
        "claimed_at",
        "expires_at",
    ),
    "mission_report_receipts": (
        "report_id",
        "mission_id",
        "claim_id",
        "node_id",
        "verified_node_identity_key_id",
        "envelope_digest",
        "expected_lifecycle_revision",
        "report_kind",
        "outcome_code",
        "reason_code",
        "artifact_digest",
        "request_digest",
        "receipt_posture_json",
        "receipt_disposition",
        "evidence_status",
        "audit_event_id",
        "audit_event_hash",
        "failure_reason_code",
        "received_at",
        "finalized_at",
    ),
    "mission_report_nonces": (
        "node_id",
        "nonce",
        "accepted_at",
    ),
}

PIS004A_TABLE_COLUMNS = {
    "identity_organizations": (
        "organization_id",
        "enabled",
        "created_at",
        "updated_at",
    ),
    "identity_provider_configurations": (
        "provider_configuration_id",
        "organization_id",
        "exact_issuer",
        "enabled",
        "generation",
        "created_at",
        "updated_at",
    ),
    "identity_principals": (
        "principal_id",
        "principal_type",
        "enabled",
        "identity_generation",
        "created_at",
        "updated_at",
    ),
    "identity_bindings": (
        "organization_id",
        "provider_configuration_id",
        "exact_issuer",
        "subject",
        "principal_id",
        "created_at",
    ),
    "identity_organization_memberships": (
        "organization_id",
        "principal_id",
        "enabled",
        "membership_generation",
        "roles_json",
        "created_at",
        "updated_at",
    ),
    "identity_workspaces": (
        "organization_id",
        "workspace_id",
        "enabled",
        "generation",
        "created_at",
        "updated_at",
    ),
    "identity_workspace_memberships": (
        "organization_id",
        "workspace_id",
        "principal_id",
        "enabled",
        "roles_json",
        "created_at",
        "updated_at",
    ),
    "identity_approval_requests": (
        "approval_request_id",
        "organization_id",
        "workspace_id",
        "requester_principal_id",
        "approval_class",
        "request_generation",
        "status",
        "created_at",
        "updated_at",
    ),
    "identity_session_families": (
        "family_id",
        "organization_id",
        "principal_id",
        "identity_generation",
        "membership_generation",
        "created_at",
        "revoked_at",
        "revocation_reason",
    ),
    "identity_sessions": (
        "session_id",
        "family_id",
        "handle_digest",
        "digest_key_generation",
        "session_audit_id",
        "csrf_digest",
        "authentication_method",
        "recent_auth_at",
        "created_at",
        "last_seen_at",
        "idle_expires_at",
        "absolute_expires_at",
        "status",
        "rotated_to_session_id",
        "revoked_at",
    ),
    "identity_preauthentication_transactions": (
        "transaction_id",
        "handle_digest",
        "digest_key_generation",
        "transaction_audit_id",
        "organization_id",
        "provider_configuration_id",
        "exact_issuer",
        "configured_redirect_uri",
        "allowed_origin",
        "state_digest",
        "nonce_digest",
        "pkce_verifier_envelope",
        "created_at",
        "expires_at",
        "status",
        "consumed_at",
    ),
    "identity_oidc_replays": (
        "organization_id",
        "provider_configuration_id",
        "token_digest",
        "first_seen_at",
        "expires_at",
    ),
}

PIS004A_INDEX_NAMES = (
    "identity_bindings_principal_idx",
    "identity_organization_memberships_principal_idx",
    "identity_workspace_memberships_principal_idx",
    "identity_approval_requests_scope_status_idx",
    "identity_sessions_family_status_idx",
    "identity_sessions_idle_expiry_idx",
    "identity_preauthentication_expiry_idx",
    "identity_oidc_replays_expiry_idx",
)

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
    "v2_executing",
    "v2_completion_evidence_pending",
    "v2_approval_evidence_failed",
    "v2_authority_stale",
    "v2_placement_evidence_recovery_required",
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
    """Create or atomically migrate the coordinated persistence contract."""

    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("BEGIN IMMEDIATE")
        current = _metadata_value(connection, "schema_version")
        minimum_writer = _metadata_value(connection, "minimum_writer_version")
        _validate_version_metadata(current=current, minimum_writer=minimum_writer)
        had_user_tables = _has_user_tables(connection)
        if current == "4":
            ensure_pre_v5_backup(
                locked_source=connection,
                db_path=db_path,
                source_schema_version=current,
                source_minimum_writer_version=minimum_writer,
            )
        elif current != DATABASE_SCHEMA_VERSION and (current is not None or had_user_tables):
            ensure_pre_v4_backup(
                locked_source=connection,
                db_path=db_path,
                source_schema_version=current or "unversioned",
                source_minimum_writer_version=minimum_writer,
            )
        _create_metadata_table(connection)

        if current == DATABASE_SCHEMA_VERSION:
            _verify_v2_schema(connection)
            _verify_mission_schema(connection)
            _verify_pis004a_schema(connection)
        elif current == "4":
            _verify_v2_schema(connection)
            _verify_mission_schema(connection)
            _migrate_v4_to_v5(connection)
        elif current == "3":
            _verify_v2_schema(connection)
            _migrate_v3_to_v4(connection)
            _migrate_v4_to_v5(connection)
        elif current == "2":
            _verify_v2_schema(connection, require_placement_states=False)
            _migrate_v2_to_v3(connection)
            _migrate_v3_to_v4(connection)
            _migrate_v4_to_v5(connection)
        elif current in {None, "0", "1"}:
            _migrate_tables(connection)
            _migrate_v3_to_v4(connection)
            _migrate_v4_to_v5(connection)
        else:  # pragma: no cover - guarded above, retained as a fail-closed fence
            raise DatabaseMigrationError(f"unsupported database schema version: {current}")

        _set_metadata(connection, "schema_version", DATABASE_SCHEMA_VERSION)
        _set_metadata(connection, "minimum_writer_version", MINIMUM_WRITER_VERSION)
        _verify_v2_schema(connection)
        _verify_mission_schema(connection)
        _verify_pis004a_schema(connection)
        connection.execute("COMMIT")
    except (DatabaseBackupError, DatabaseMigrationError, sqlite3.DatabaseError):
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def verify_database_v2(db_path: Path) -> None:
    """Reject use before the coordinated contract is on the current writer schema."""

    try:
        with sqlite3.connect(db_path) as connection:
            current = _metadata_value(connection, "schema_version")
            minimum_writer = _metadata_value(connection, "minimum_writer_version")
            _validate_version_metadata(current=current, minimum_writer=minimum_writer)
            if current != DATABASE_SCHEMA_VERSION or minimum_writer != MINIMUM_WRITER_VERSION:
                raise DatabaseMigrationError("coordinated database migration has not completed")
            _verify_v2_schema(connection)
            _verify_mission_schema(connection)
            _verify_pis004a_schema(connection)
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


def _migrate_v2_to_v3(connection: sqlite3.Connection) -> None:
    """Rebuild the closed v2 status constraints for placement and recovery states."""

    connection.execute("DROP INDEX IF EXISTS approvals_status_updated_idx")
    connection.execute("DROP INDEX IF EXISTS promotion_authority_hash_idx")
    for table in (
        "approvals",
        "trusted_host_promotion_proposals",
        "trusted_host_promotion_attempts",
    ):
        connection.execute(f"ALTER TABLE {table} RENAME TO {table}_v2")

    _create_v2_tables(connection)

    for table, columns in V2_TABLE_COLUMNS.items():
        column_list = ", ".join(columns)
        connection.execute(
            f"INSERT INTO {table} ({column_list}) "
            f"SELECT {column_list} FROM {table}_v2"
        )
        connection.execute(f"DROP TABLE {table}_v2")


def _migrate_v3_to_v4(connection: sqlite3.Connection) -> None:
    """Add the closed Mission Command authority tables in the coordinated transaction."""

    existing = [table for table in MISSION_TABLE_COLUMNS if _table_exists(connection, table)]
    if existing:
        raise DatabaseMigrationError(
            "database v3 contains unexpected Mission Command tables: " + ", ".join(existing)
        )
    _create_mission_tables(connection)


def _migrate_v4_to_v5(connection: sqlite3.Connection) -> None:
    """Add the local-only PIS-004A identity and session authority tables."""

    existing = [table for table in PIS004A_TABLE_COLUMNS if _table_exists(connection, table)]
    if existing:
        raise DatabaseMigrationError(
            "database v4 contains unexpected PIS-004A tables: " + ", ".join(existing)
        )
    _create_pis004a_tables(connection)


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


def _verify_v2_schema(
    connection: sqlite3.Connection,
    *,
    require_placement_states: bool = True,
) -> None:
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
    if require_placement_states:
        required_schema_fragments["trusted_host_promotion_proposals"].update(
            {
                "v2_executing",
                "v2_completion_evidence_pending",
                "v2_placement_evidence_recovery_required",
                "v2_completed",
            }
        )
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


def _create_mission_tables(connection: sqlite3.Connection) -> None:
    lifecycle_states = _sql_values(
        (
            "unadmitted",
            "queued",
            "claimed",
            "runner_reported_running",
            "runner_reported_succeeded",
            "runner_reported_failed",
            "canceled",
            "cancel_requested",
            "runner_reported_canceled",
            "claim_expired_review_required",
        )
    )
    evidence_statuses = _sql_values(("pending", "complete", "evidence_incomplete"))
    transition_kinds = _sql_values(
        (
            "admission_pending_evidence",
            "claim_pending_evidence",
            "cancellation_pending_evidence",
            "control_observation_pending_evidence",
            "report_pending_evidence",
            "claim_expiry_pending_evidence",
        )
    )
    connection.execute(
        f"""
        CREATE TABLE missions (
            mission_id TEXT PRIMARY KEY,
            requester_principal_id TEXT NOT NULL,
            requester_identity_generation TEXT NOT NULL,
            client_request_id TEXT NOT NULL,
            admission_request_digest TEXT NOT NULL,
            authority_snapshot_json TEXT NOT NULL,
            authority_snapshot_hash TEXT NOT NULL,
            target_node_id TEXT NOT NULL,
            target_node_principal_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            configuration_generation INTEGER NOT NULL,
            configuration_digest TEXT NOT NULL,
            policy_digest TEXT NOT NULL,
            manifest_lock_digest TEXT NOT NULL,
            mission_template_id TEXT NOT NULL,
            template_registry_generation TEXT NOT NULL,
            template_payload_digest TEXT NOT NULL,
            envelope_digest TEXT NOT NULL,
            requested_timeout_seconds INTEGER NOT NULL,
            lifecycle_state TEXT NOT NULL,
            lifecycle_revision INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            admitted_at TEXT,
            UNIQUE (
                requester_principal_id,
                requester_identity_generation,
                client_request_id
            ),
            CHECK (
                length(mission_id) = 40 AND substr(mission_id, 1, 8) = 'mission_'
                AND substr(mission_id, 9) NOT GLOB '*[^0-9a-f]*'
            ),
            CHECK (length(requester_principal_id) BETWEEN 1 AND 128),
            CHECK (length(client_request_id) BETWEEN 1 AND 128),
            CHECK (length(authority_snapshot_json) BETWEEN 2 AND 32768),
            CHECK (length(target_node_id) = 37 AND substr(target_node_id, 1, 5) = 'node_'
                AND substr(target_node_id, 6) NOT GLOB '*[^0-9a-f]*'),
            CHECK (configuration_generation >= 1),
            CHECK (mission_template_id = 'synthetic_read_review_v1'),
            CHECK (requested_timeout_seconds BETWEEN 60 AND 3600),
            CHECK (lifecycle_state IN ({lifecycle_states})),
            CHECK (lifecycle_revision >= 0),
            CHECK (
                (lifecycle_state = 'unadmitted' AND lifecycle_revision = 0
                    AND admitted_at IS NULL) OR
                (lifecycle_state != 'unadmitted' AND lifecycle_revision >= 1
                    AND admitted_at IS NOT NULL)
            ),
            CHECK (length(requester_identity_generation) = 71
                AND substr(requester_identity_generation, 1, 7) = 'sha256:'
                AND substr(requester_identity_generation, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(admission_request_digest) = 71
                AND substr(admission_request_digest, 1, 7) = 'sha256:'
                AND substr(admission_request_digest, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(authority_snapshot_hash) = 71
                AND substr(authority_snapshot_hash, 1, 7) = 'sha256:'
                AND substr(authority_snapshot_hash, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(configuration_digest) = 71
                AND substr(configuration_digest, 1, 7) = 'sha256:'
                AND substr(configuration_digest, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(policy_digest) = 71 AND substr(policy_digest, 1, 7) = 'sha256:'
                AND substr(policy_digest, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(manifest_lock_digest) = 71
                AND substr(manifest_lock_digest, 1, 7) = 'sha256:'
                AND substr(manifest_lock_digest, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(template_registry_generation) = 71
                AND substr(template_registry_generation, 1, 7) = 'sha256:'
                AND substr(template_registry_generation, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(template_payload_digest) = 71
                AND substr(template_payload_digest, 1, 7) = 'sha256:'
                AND substr(template_payload_digest, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(envelope_digest) = 71
                AND substr(envelope_digest, 1, 7) = 'sha256:'
                AND substr(envelope_digest, 8) NOT GLOB '*[^0-9a-f]*')
        )
        """
    )
    connection.execute(
        "CREATE INDEX missions_updated_idx ON missions(updated_at DESC, mission_id)"
    )
    connection.execute(
        """
        CREATE TABLE mission_audit_evidence_bindings (
            audit_event_id TEXT PRIMARY KEY,
            audit_event_hash TEXT NOT NULL UNIQUE,
            owner_kind TEXT NOT NULL,
            owner_id TEXT NOT NULL UNIQUE,
            request_digest TEXT NOT NULL,
            bound_at TEXT NOT NULL,
            CHECK (length(audit_event_id) = 36
                AND substr(audit_event_id, 1, 4) = 'evt_'
                AND substr(audit_event_id, 5) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(audit_event_hash) = 71
                AND substr(audit_event_hash, 1, 7) = 'sha256:'
                AND substr(audit_event_hash, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (owner_kind IN ('mission_transition', 'mission_report_receipt')),
            CHECK (
                (owner_kind = 'mission_transition' AND length(owner_id) = 44
                    AND substr(owner_id, 1, 12) = 'mtransition_'
                    AND substr(owner_id, 13) NOT GLOB '*[^0-9a-f]*') OR
                (owner_kind = 'mission_report_receipt' AND length(owner_id) = 40
                    AND substr(owner_id, 1, 8) = 'mreport_'
                    AND substr(owner_id, 9) NOT GLOB '*[^0-9a-f]*')
            ),
            CHECK (length(request_digest) = 71
                AND substr(request_digest, 1, 7) = 'sha256:'
                AND substr(request_digest, 8) NOT GLOB '*[^0-9a-f]*')
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE mission_transition_attempts (
            transition_id TEXT PRIMARY KEY,
            mission_id TEXT NOT NULL,
            transition_kind TEXT NOT NULL,
            prior_lifecycle_state TEXT NOT NULL,
            prior_lifecycle_revision INTEGER NOT NULL,
            proposed_lifecycle_state TEXT NOT NULL,
            proposed_lifecycle_revision INTEGER NOT NULL,
            request_digest TEXT NOT NULL,
            safe_metadata_json TEXT NOT NULL,
            evidence_status TEXT NOT NULL,
            audit_event_id TEXT,
            audit_event_hash TEXT,
            failure_reason_code TEXT,
            created_at TEXT NOT NULL,
            finalized_at TEXT,
            UNIQUE (mission_id, proposed_lifecycle_revision),
            UNIQUE (mission_id, transition_id),
            FOREIGN KEY (mission_id) REFERENCES missions(mission_id),
            FOREIGN KEY (audit_event_id)
                REFERENCES mission_audit_evidence_bindings(audit_event_id),
            CHECK (length(transition_id) = 44
                AND substr(transition_id, 1, 12) = 'mtransition_'
                AND substr(transition_id, 13) NOT GLOB '*[^0-9a-f]*'),
            CHECK (transition_kind IN ({transition_kinds})),
            CHECK (prior_lifecycle_state IN ({lifecycle_states})),
            CHECK (proposed_lifecycle_state IN ({lifecycle_states})),
            CHECK (prior_lifecycle_revision >= 0),
            CHECK (proposed_lifecycle_revision = prior_lifecycle_revision + 1),
            CHECK (length(request_digest) = 71 AND substr(request_digest, 1, 7) = 'sha256:'
                AND substr(request_digest, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(safe_metadata_json) BETWEEN 2 AND 4096),
            CHECK (evidence_status IN ({evidence_statuses})),
            CHECK ((audit_event_id IS NULL AND audit_event_hash IS NULL)
                OR (audit_event_id IS NOT NULL AND audit_event_hash IS NOT NULL)),
            CHECK (audit_event_id IS NULL OR (length(audit_event_id) = 36
                AND substr(audit_event_id, 1, 4) = 'evt_'
                AND substr(audit_event_id, 5) NOT GLOB '*[^0-9a-f]*')),
            CHECK (audit_event_hash IS NULL OR (length(audit_event_hash) = 71
                AND substr(audit_event_hash, 1, 7) = 'sha256:'
                AND substr(audit_event_hash, 8) NOT GLOB '*[^0-9a-f]*')),
            CHECK (
                (evidence_status = 'pending' AND audit_event_id IS NULL
                    AND failure_reason_code IS NULL AND finalized_at IS NULL) OR
                (evidence_status = 'complete' AND audit_event_id IS NOT NULL
                    AND failure_reason_code IS NULL AND finalized_at IS NOT NULL) OR
                (evidence_status = 'evidence_incomplete'
                    AND failure_reason_code IS NOT NULL AND finalized_at IS NOT NULL)
            )
        )
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX mission_transition_one_unresolved_idx
        ON mission_transition_attempts(mission_id)
        WHERE evidence_status IN ('pending', 'evidence_incomplete')
        """
    )
    connection.execute(
        """
        CREATE TABLE mission_claims (
            claim_id TEXT PRIMARY KEY,
            mission_id TEXT NOT NULL UNIQUE,
            transition_id TEXT NOT NULL UNIQUE,
            node_id TEXT NOT NULL,
            node_identity_key_id TEXT NOT NULL,
            envelope_digest TEXT NOT NULL,
            authority_snapshot_json TEXT NOT NULL,
            authority_snapshot_hash TEXT NOT NULL,
            lifecycle_revision INTEGER NOT NULL,
            claim_status TEXT NOT NULL,
            claimed_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            UNIQUE (mission_id, claim_id),
            UNIQUE (mission_id, claim_id, node_id, envelope_digest),
            FOREIGN KEY (mission_id) REFERENCES missions(mission_id),
            FOREIGN KEY (mission_id, transition_id)
                REFERENCES mission_transition_attempts(mission_id, transition_id),
            CHECK (length(claim_id) = 39 AND substr(claim_id, 1, 7) = 'mclaim_'
                AND substr(claim_id, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(node_id) = 37 AND substr(node_id, 1, 5) = 'node_'
                AND substr(node_id, 6) NOT GLOB '*[^0-9a-f]*'),
            CHECK (lifecycle_revision >= 1),
            CHECK (claim_status IN ('staged', 'delivered', 'evidence_incomplete',
                'expired_review_required')),
            CHECK (length(node_identity_key_id) = 71
                AND substr(node_identity_key_id, 1, 7) = 'sha256:'
                AND substr(node_identity_key_id, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(envelope_digest) = 71 AND substr(envelope_digest, 1, 7) = 'sha256:'
                AND substr(envelope_digest, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(authority_snapshot_hash) = 71
                AND substr(authority_snapshot_hash, 1, 7) = 'sha256:'
                AND substr(authority_snapshot_hash, 8) NOT GLOB '*[^0-9a-f]*')
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE mission_report_receipts (
            report_id TEXT PRIMARY KEY,
            mission_id TEXT NOT NULL,
            claim_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            verified_node_identity_key_id TEXT NOT NULL,
            envelope_digest TEXT NOT NULL,
            expected_lifecycle_revision INTEGER NOT NULL,
            report_kind TEXT NOT NULL,
            outcome_code TEXT NOT NULL,
            reason_code TEXT,
            artifact_digest TEXT,
            request_digest TEXT NOT NULL,
            receipt_posture_json TEXT NOT NULL,
            receipt_disposition TEXT NOT NULL,
            evidence_status TEXT NOT NULL,
            audit_event_id TEXT,
            audit_event_hash TEXT,
            failure_reason_code TEXT,
            received_at TEXT NOT NULL,
            finalized_at TEXT,
            FOREIGN KEY (mission_id) REFERENCES missions(mission_id),
            FOREIGN KEY (mission_id, claim_id, node_id, envelope_digest)
                REFERENCES mission_claims(mission_id, claim_id, node_id, envelope_digest),
            FOREIGN KEY (audit_event_id)
                REFERENCES mission_audit_evidence_bindings(audit_event_id),
            CHECK (length(report_id) = 40 AND substr(report_id, 1, 8) = 'mreport_'
                AND substr(report_id, 9) NOT GLOB '*[^0-9a-f]*'),
            CHECK (expected_lifecycle_revision >= 1),
            CHECK (report_kind IN ('runner_running', 'runner_succeeded', 'runner_failed',
                'cancel_observed', 'runner_canceled')),
            CHECK (outcome_code IN ('started', 'succeeded', 'failed', 'canceled',
                'cancellation_observed')),
            CHECK (
                (report_kind = 'runner_running' AND outcome_code = 'started') OR
                (report_kind = 'runner_succeeded' AND outcome_code = 'succeeded') OR
                (report_kind = 'runner_failed' AND outcome_code = 'failed') OR
                (report_kind = 'cancel_observed'
                    AND outcome_code = 'cancellation_observed') OR
                (report_kind = 'runner_canceled' AND outcome_code = 'canceled')
            ),
            CHECK (
                (report_kind = 'runner_failed' AND reason_code IS NOT NULL
                    AND artifact_digest IS NULL) OR
                (report_kind = 'runner_succeeded' AND reason_code IS NULL) OR
                (report_kind NOT IN ('runner_failed', 'runner_succeeded')
                    AND reason_code IS NULL AND artifact_digest IS NULL)
            ),
            CHECK (reason_code IS NULL OR (
                reason_code IN ('runner_error', 'runner_timeout', 'runner_output_invalid',
                    'runner_dependency_unavailable')
            )),
            CHECK (receipt_disposition IN ('pending', 'lifecycle_advancing', 'quarantined',
                'evidence_incomplete')),
            CHECK (evidence_status IN ({evidence_statuses})),
            CHECK ((audit_event_id IS NULL AND audit_event_hash IS NULL)
                OR (audit_event_id IS NOT NULL AND audit_event_hash IS NOT NULL)),
            CHECK (length(node_id) = 37 AND substr(node_id, 1, 5) = 'node_'
                AND substr(node_id, 6) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(verified_node_identity_key_id) = 71
                AND substr(verified_node_identity_key_id, 1, 7) = 'sha256:'
                AND substr(verified_node_identity_key_id, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(envelope_digest) = 71
                AND substr(envelope_digest, 1, 7) = 'sha256:'
                AND substr(envelope_digest, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (audit_event_id IS NULL OR (length(audit_event_id) = 36
                AND substr(audit_event_id, 1, 4) = 'evt_'
                AND substr(audit_event_id, 5) NOT GLOB '*[^0-9a-f]*')),
            CHECK (audit_event_hash IS NULL OR (length(audit_event_hash) = 71
                AND substr(audit_event_hash, 1, 7) = 'sha256:'
                AND substr(audit_event_hash, 8) NOT GLOB '*[^0-9a-f]*')),
            CHECK (artifact_digest IS NULL OR (length(artifact_digest) = 71
                AND substr(artifact_digest, 1, 7) = 'sha256:'
                AND substr(artifact_digest, 8) NOT GLOB '*[^0-9a-f]*')),
            CHECK (length(request_digest) = 71 AND substr(request_digest, 1, 7) = 'sha256:'
                AND substr(request_digest, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (
                (evidence_status = 'pending' AND receipt_disposition = 'pending'
                    AND audit_event_id IS NULL AND failure_reason_code IS NULL
                    AND finalized_at IS NULL) OR
                (evidence_status = 'complete'
                    AND receipt_disposition IN ('lifecycle_advancing', 'quarantined')
                    AND audit_event_id IS NOT NULL AND failure_reason_code IS NULL
                    AND finalized_at IS NOT NULL) OR
                (evidence_status = 'evidence_incomplete'
                    AND receipt_disposition = 'evidence_incomplete'
                    AND failure_reason_code IS NOT NULL AND finalized_at IS NOT NULL)
            ),
            UNIQUE (claim_id, report_id)
        )
        """
    )
    connection.execute(
        "CREATE INDEX mission_report_receipts_mission_idx "
        "ON mission_report_receipts(mission_id, received_at DESC)"
    )
    connection.execute(
        """
        CREATE TABLE mission_report_nonces (
            node_id TEXT NOT NULL,
            nonce TEXT NOT NULL,
            accepted_at TEXT NOT NULL,
            PRIMARY KEY (node_id, nonce),
            CHECK (length(node_id) = 37 AND substr(node_id, 1, 5) = 'node_'
                AND substr(node_id, 6) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(nonce) BETWEEN 32 AND 128
                AND nonce NOT GLOB '*[^0-9a-f]*')
        )
        """
    )
    connection.execute(
        "CREATE INDEX mission_report_nonces_accepted_idx "
        "ON mission_report_nonces(accepted_at)"
    )


def _create_pis004a_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE identity_organizations (
            organization_id TEXT PRIMARY KEY,
            enabled INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (length(organization_id) = 36 AND substr(organization_id, 1, 4) = 'org_'
                AND substr(organization_id, 5) NOT GLOB '*[^0-9a-f]*'),
            CHECK (enabled IN (0, 1)),
            CHECK (updated_at >= created_at)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE identity_provider_configurations (
            provider_configuration_id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            exact_issuer TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            generation INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id)
                REFERENCES identity_organizations(organization_id),
            CHECK (length(provider_configuration_id) = 37
                AND substr(provider_configuration_id, 1, 5) = 'idpc_'
                AND substr(provider_configuration_id, 6) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(exact_issuer) BETWEEN 9 AND 2048),
            CHECK (enabled IN (0, 1)),
            CHECK (generation >= 1),
            CHECK (updated_at >= created_at),
            UNIQUE (organization_id, provider_configuration_id),
            UNIQUE (organization_id, provider_configuration_id, exact_issuer)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE identity_principals (
            principal_id TEXT PRIMARY KEY,
            principal_type TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            identity_generation INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (length(principal_id) = 36 AND substr(principal_id, 1, 4) = 'prn_'
                AND substr(principal_id, 5) NOT GLOB '*[^0-9a-f]*'),
            CHECK (principal_type IN ('human', 'node', 'service')),
            CHECK (enabled IN (0, 1)),
            CHECK (identity_generation >= 1),
            CHECK (updated_at >= created_at)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE identity_bindings (
            organization_id TEXT NOT NULL,
            provider_configuration_id TEXT NOT NULL,
            exact_issuer TEXT NOT NULL,
            subject TEXT NOT NULL,
            principal_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            PRIMARY KEY (
                organization_id,
                provider_configuration_id,
                exact_issuer,
                subject
            ),
            FOREIGN KEY (organization_id, provider_configuration_id, exact_issuer)
                REFERENCES identity_provider_configurations(
                    organization_id,
                    provider_configuration_id,
                    exact_issuer
                ),
            FOREIGN KEY (principal_id) REFERENCES identity_principals(principal_id),
            CHECK (length(subject) BETWEEN 1 AND 512)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX identity_bindings_principal_idx
        ON identity_bindings(principal_id, organization_id)
        """
    )
    connection.execute(
        """
        CREATE TABLE identity_organization_memberships (
            organization_id TEXT NOT NULL,
            principal_id TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            membership_generation INTEGER NOT NULL,
            roles_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (organization_id, principal_id),
            FOREIGN KEY (organization_id)
                REFERENCES identity_organizations(organization_id),
            FOREIGN KEY (principal_id) REFERENCES identity_principals(principal_id),
            CHECK (enabled IN (0, 1)),
            CHECK (membership_generation >= 1),
            CHECK (json_valid(roles_json) AND json_type(roles_json) = 'array'
                AND json_array_length(roles_json) >= 1),
            CHECK (updated_at >= created_at)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX identity_organization_memberships_principal_idx
        ON identity_organization_memberships(principal_id, organization_id, enabled)
        """
    )
    connection.execute(
        """
        CREATE TABLE identity_workspaces (
            organization_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            generation INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (organization_id, workspace_id),
            FOREIGN KEY (organization_id)
                REFERENCES identity_organizations(organization_id),
            CHECK (length(workspace_id) BETWEEN 1 AND 128),
            CHECK (enabled IN (0, 1)),
            CHECK (generation >= 1),
            CHECK (updated_at >= created_at)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE identity_workspace_memberships (
            organization_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            principal_id TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            roles_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (organization_id, workspace_id, principal_id),
            FOREIGN KEY (organization_id, workspace_id)
                REFERENCES identity_workspaces(organization_id, workspace_id),
            FOREIGN KEY (organization_id, principal_id)
                REFERENCES identity_organization_memberships(organization_id, principal_id),
            CHECK (enabled IN (0, 1)),
            CHECK (json_valid(roles_json) AND json_type(roles_json) = 'array'
                AND json_array_length(roles_json) >= 1),
            CHECK (updated_at >= created_at)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX identity_workspace_memberships_principal_idx
        ON identity_workspace_memberships(
            principal_id,
            organization_id,
            enabled,
            workspace_id
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE identity_approval_requests (
            approval_request_id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            requester_principal_id TEXT NOT NULL,
            approval_class TEXT NOT NULL,
            request_generation INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (organization_id, workspace_id)
                REFERENCES identity_workspaces(organization_id, workspace_id),
            FOREIGN KEY (organization_id, requester_principal_id)
                REFERENCES identity_organization_memberships(
                    organization_id,
                    principal_id
                ),
            CHECK (length(approval_request_id) = 36
                AND substr(approval_request_id, 1, 4) = 'apr_'
                AND substr(approval_request_id, 5) NOT GLOB '*[^0-9a-f]*'),
            CHECK (approval_class IN (
                'standard',
                'trusted_host_placement',
                'high_risk'
            )),
            CHECK (request_generation >= 1),
            CHECK (status IN ('pending', 'approved', 'denied', 'cancelled')),
            CHECK (updated_at >= created_at)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX identity_approval_requests_scope_status_idx
        ON identity_approval_requests(
            organization_id,
            workspace_id,
            status,
            created_at
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE identity_session_families (
            family_id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            principal_id TEXT NOT NULL,
            identity_generation INTEGER NOT NULL,
            membership_generation INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            revoked_at TEXT,
            revocation_reason TEXT,
            FOREIGN KEY (organization_id, principal_id)
                REFERENCES identity_organization_memberships(organization_id, principal_id),
            CHECK (length(family_id) = 37 AND substr(family_id, 1, 5) = 'sfam_'
                AND substr(family_id, 6) NOT GLOB '*[^0-9a-f]*'),
            CHECK (identity_generation >= 1),
            CHECK (membership_generation >= 1),
            CHECK ((revoked_at IS NULL AND revocation_reason IS NULL)
                OR (revoked_at IS NOT NULL AND revocation_reason IS NOT NULL
                    AND length(revocation_reason) BETWEEN 1 AND 64))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE identity_sessions (
            session_id TEXT PRIMARY KEY,
            family_id TEXT NOT NULL,
            handle_digest TEXT NOT NULL UNIQUE,
            digest_key_generation INTEGER NOT NULL,
            session_audit_id TEXT NOT NULL UNIQUE,
            csrf_digest TEXT NOT NULL,
            authentication_method TEXT NOT NULL,
            recent_auth_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            idle_expires_at TEXT NOT NULL,
            absolute_expires_at TEXT NOT NULL,
            status TEXT NOT NULL,
            rotated_to_session_id TEXT,
            revoked_at TEXT,
            FOREIGN KEY (family_id) REFERENCES identity_session_families(family_id),
            FOREIGN KEY (rotated_to_session_id) REFERENCES identity_sessions(session_id),
            CHECK (length(session_id) = 37 AND substr(session_id, 1, 5) = 'sess_'
                AND substr(session_id, 6) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(handle_digest) = 76
                AND substr(handle_digest, 1, 12) = 'hmac-sha256:'
                AND substr(handle_digest, 13) NOT GLOB '*[^0-9a-f]*'),
            CHECK (digest_key_generation >= 1),
            CHECK (length(session_audit_id) = 37
                AND substr(session_audit_id, 1, 5) = 'saud_'
                AND substr(session_audit_id, 6) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(csrf_digest) = 76
                AND substr(csrf_digest, 1, 12) = 'hmac-sha256:'
                AND substr(csrf_digest, 13) NOT GLOB '*[^0-9a-f]*'),
            CHECK (authentication_method IN ('oidc_fixture', 'local_recovery')),
            CHECK (last_seen_at >= created_at),
            CHECK (idle_expires_at > created_at),
            CHECK (absolute_expires_at >= idle_expires_at),
            CHECK (status IN ('active', 'rotated', 'revoked', 'expired')),
            CHECK (
                (status = 'active' AND rotated_to_session_id IS NULL AND revoked_at IS NULL) OR
                (status = 'rotated' AND rotated_to_session_id IS NOT NULL
                    AND revoked_at IS NULL) OR
                (status IN ('revoked', 'expired') AND rotated_to_session_id IS NULL
                    AND revoked_at IS NOT NULL)
            )
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX identity_sessions_family_status_idx
        ON identity_sessions(family_id, status, created_at DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX identity_sessions_idle_expiry_idx
        ON identity_sessions(status, idle_expires_at)
        """
    )
    connection.execute(
        """
        CREATE TABLE identity_preauthentication_transactions (
            transaction_id TEXT PRIMARY KEY,
            handle_digest TEXT NOT NULL UNIQUE,
            digest_key_generation INTEGER NOT NULL,
            transaction_audit_id TEXT NOT NULL UNIQUE,
            organization_id TEXT NOT NULL,
            provider_configuration_id TEXT NOT NULL,
            exact_issuer TEXT NOT NULL,
            configured_redirect_uri TEXT NOT NULL,
            allowed_origin TEXT NOT NULL,
            state_digest TEXT NOT NULL,
            nonce_digest TEXT NOT NULL,
            pkce_verifier_envelope TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            status TEXT NOT NULL,
            consumed_at TEXT,
            FOREIGN KEY (organization_id, provider_configuration_id, exact_issuer)
                REFERENCES identity_provider_configurations(
                    organization_id,
                    provider_configuration_id,
                    exact_issuer
                ),
            CHECK (length(transaction_id) = 37
                AND substr(transaction_id, 1, 5) = 'patx_'
                AND substr(transaction_id, 6) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(handle_digest) = 76
                AND substr(handle_digest, 1, 12) = 'hmac-sha256:'
                AND substr(handle_digest, 13) NOT GLOB '*[^0-9a-f]*'),
            CHECK (digest_key_generation >= 1),
            CHECK (length(transaction_audit_id) = 37
                AND substr(transaction_audit_id, 1, 5) = 'paud_'
                AND substr(transaction_audit_id, 6) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(configured_redirect_uri) BETWEEN 12 AND 2048),
            CHECK (length(allowed_origin) BETWEEN 8 AND 2048),
            CHECK (length(state_digest) = 76
                AND substr(state_digest, 1, 12) = 'hmac-sha256:'
                AND substr(state_digest, 13) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(nonce_digest) = 76
                AND substr(nonce_digest, 1, 12) = 'hmac-sha256:'
                AND substr(nonce_digest, 13) NOT GLOB '*[^0-9a-f]*'),
            CHECK (expires_at > created_at),
            CHECK (status IN ('active', 'consumed', 'revoked')),
            CHECK ((status = 'active' AND consumed_at IS NULL)
                OR (status IN ('consumed', 'revoked') AND consumed_at IS NOT NULL)),
            CHECK (
                (status = 'active'
                    AND length(pkce_verifier_envelope) BETWEEN 80 AND 1024
                    AND substr(pkce_verifier_envelope, 1, 13) = 'aes256gcm:v1:')
                OR (status IN ('consumed', 'revoked')
                    AND length(pkce_verifier_envelope) = 73
                    AND substr(pkce_verifier_envelope, 1, 9) = 'redacted:')
            )
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX identity_preauthentication_expiry_idx
        ON identity_preauthentication_transactions(status, expires_at)
        """
    )
    connection.execute(
        """
        CREATE TABLE identity_oidc_replays (
            organization_id TEXT NOT NULL,
            provider_configuration_id TEXT NOT NULL,
            token_digest TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            PRIMARY KEY (organization_id, provider_configuration_id, token_digest),
            FOREIGN KEY (organization_id, provider_configuration_id)
                REFERENCES identity_provider_configurations(
                    organization_id,
                    provider_configuration_id
                ),
            CHECK (length(token_digest) = 71
                AND substr(token_digest, 1, 7) = 'sha256:'
                AND substr(token_digest, 8) NOT GLOB '*[^0-9a-f]*'),
            CHECK (expires_at > first_seen_at)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX identity_oidc_replays_expiry_idx
        ON identity_oidc_replays(expires_at)
        """
    )


def _verify_pis004a_schema(connection: sqlite3.Connection) -> None:
    expected_connection = sqlite3.connect(":memory:")
    try:
        expected_connection.execute("PRAGMA foreign_keys = ON")
        _create_pis004a_tables(expected_connection)
        for table, expected_columns in PIS004A_TABLE_COLUMNS.items():
            if not _table_exists(connection, table):
                raise DatabaseMigrationError(f"PIS-004A table is missing: {table}")
            columns = tuple(
                str(row[1])
                for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
            )
            if columns != expected_columns:
                raise DatabaseMigrationError(f"PIS-004A table is incomplete: {table}")
            if _schema_sql(connection, object_type="table", name=table) != _schema_sql(
                expected_connection,
                object_type="table",
                name=table,
            ):
                raise DatabaseMigrationError(f"PIS-004A table schema differs: {table}")
        for index_name in PIS004A_INDEX_NAMES:
            if _schema_sql(connection, object_type="index", name=index_name) != _schema_sql(
                expected_connection,
                object_type="index",
                name=index_name,
            ):
                raise DatabaseMigrationError(f"PIS-004A index differs: {index_name}")
        unexpected_objects = connection.execute(
            f"""
            SELECT type, name FROM sqlite_master
            WHERE tbl_name IN ({_sql_values(tuple(PIS004A_TABLE_COLUMNS))})
              AND sql IS NOT NULL
              AND NOT (
                  type = 'table'
                  AND name IN ({_sql_values(tuple(PIS004A_TABLE_COLUMNS))})
              )
              AND NOT (
                  type = 'index'
                  AND name IN ({_sql_values(PIS004A_INDEX_NAMES)})
              )
            ORDER BY type, name
            """
        ).fetchall()
        if unexpected_objects:
            raise DatabaseMigrationError("PIS-004A schema has unexpected objects")
    finally:
        expected_connection.close()
    foreign_key_failures = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_failures:
        raise DatabaseMigrationError("PIS-004A foreign-key verification failed")


def _verify_mission_schema(connection: sqlite3.Connection) -> None:
    expected_connection = sqlite3.connect(":memory:")
    try:
        _create_mission_tables(expected_connection)
        for table, expected_columns in MISSION_TABLE_COLUMNS.items():
            if not _table_exists(connection, table):
                raise DatabaseMigrationError(f"Mission Command table is missing: {table}")
            columns = tuple(
                str(row[1])
                for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
            )
            if columns != expected_columns:
                raise DatabaseMigrationError(f"Mission Command table is incomplete: {table}")
            if _schema_sql(connection, object_type="table", name=table) != _schema_sql(
                expected_connection,
                object_type="table",
                name=table,
            ):
                raise DatabaseMigrationError(f"Mission Command table schema differs: {table}")
        expected_index_names = (
            "missions_updated_idx",
            "mission_transition_one_unresolved_idx",
            "mission_report_receipts_mission_idx",
            "mission_report_nonces_accepted_idx",
        )
        for index_name in expected_index_names:
            if _schema_sql(connection, object_type="index", name=index_name) != _schema_sql(
                expected_connection,
                object_type="index",
                name=index_name,
            ):
                raise DatabaseMigrationError(f"Mission Command index differs: {index_name}")
        unexpected_objects = connection.execute(
            f"""
            SELECT type, name FROM sqlite_master
            WHERE tbl_name IN ({_sql_values(tuple(MISSION_TABLE_COLUMNS))})
              AND sql IS NOT NULL
              AND NOT (type = 'table' AND name IN ({_sql_values(tuple(MISSION_TABLE_COLUMNS))}))
              AND NOT (type = 'index' AND name IN ({_sql_values(expected_index_names)}))
            ORDER BY type, name
            """
        ).fetchall()
        if unexpected_objects:
            raise DatabaseMigrationError("Mission Command schema has unexpected objects")
    finally:
        expected_connection.close()
    foreign_key_failures = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_failures:
        raise DatabaseMigrationError("Mission Command foreign-key verification failed")


def _schema_sql(
    connection: sqlite3.Connection,
    *,
    object_type: str,
    name: str,
) -> str:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = ? AND name = ?",
        (object_type, name),
    ).fetchone()
    if row is None or row[0] is None:
        return ""
    return " ".join(str(row[0]).split())


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


def _has_user_tables(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' LIMIT 1"
    ).fetchone()
    return row is not None


def _sql_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)

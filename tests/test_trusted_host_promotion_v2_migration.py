from __future__ import annotations

import hashlib
import sqlite3
import subprocess
from datetime import timedelta
from pathlib import Path

import ithildin_api.trusted_host_promotion_v2_migration as migration
import pytest
from ithildin_api.approvals import ApprovalError, ApprovalService, ApprovalStore
from ithildin_api.database import initialize_database
from ithildin_api.promotion_authority import AdminPrincipalContext
from ithildin_api.trusted_host_promotion_v2_migration import DatabaseMigrationError
from ithildin_audit_core import AuditWriter
from ithildin_schemas import ApprovalStatus

BASELINE_COMMIT = "250e6d8947972de28de134b72e0561bf39c62f5f"
BASELINE_APPROVALS_SHA256 = (
    "214bd207ac5208ecbfd6fbd5ba5ec024485edc11f88e133a5e5e699821dfec48"
)
BASELINE_PROMOTIONS_SHA256 = (
    "5361ac1ec20098bff482def23cbd26e3d86e5201a6f64cc03a031853b1df5eeb"
)


def test_empty_database_is_created_at_v2_with_minimum_writer(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
        approval_sql = _table_sql(connection, "approvals")
        proposal_sql = _table_sql(connection, "trusted_host_promotion_proposals")
        attempt_sql = _table_sql(connection, "trusted_host_promotion_attempts")
    assert metadata["schema_version"] == "2"
    assert metadata["minimum_writer_version"] == "2"
    assert "v2_pending" in approval_sql
    assert "legacy_unbound" in approval_sql
    assert "authority_snapshot_hash" in proposal_sql
    assert "v2_executing" in proposal_sql
    assert "v2_placement_evidence_recovery_required" in proposal_sql
    assert "record_version TEXT NOT NULL" in attempt_sql


def test_legacy_rows_migrate_atomically_without_synthesized_authority(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _create_v1_fixture(db_path)

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        approval = connection.execute(
            """
            SELECT approval_id, status, approval_contract_version,
                   promotion_authority_hash, requester_principal_id,
                   legacy_decision_json
            FROM approvals
            """
        ).fetchone()
        proposal = connection.execute(
            """
            SELECT proposal_id, status, authority_schema_version,
                   authority_snapshot_json, authority_snapshot_hash
            FROM trusted_host_promotion_proposals
            """
        ).fetchone()
        attempt = connection.execute(
            """
            SELECT attempt_id, status, record_version, authority_snapshot_hash
            FROM trusted_host_promotion_attempts
            """
        ).fetchone()
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))

    assert approval is not None
    assert approval[:5] == ("appr_v1", "legacy_unbound", "1", None, None)
    assert "legacy-user" in str(approval[5])
    assert proposal == ("thp_v1", "legacy_unbound", None, None, None)
    assert attempt == ("thpa_v1", "legacy_prepared", "1", None)
    assert metadata["schema_version"] == "2"
    assert metadata["minimum_writer_version"] == "2"


def test_legacy_terminal_rows_remain_readable_with_closed_statuses(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _create_v1_fixture(
        db_path,
        approval_status="executed",
        proposal_status="completed",
        attempt_status="completed",
    )

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        approval_status = connection.execute("SELECT status FROM approvals").fetchone()
        proposal_status = connection.execute(
            "SELECT status FROM trusted_host_promotion_proposals"
        ).fetchone()
        attempt_status = connection.execute(
            "SELECT status FROM trusted_host_promotion_attempts"
        ).fetchone()
    assert approval_status == ("legacy_executed",)
    assert proposal_status == ("legacy_completed",)
    assert attempt_status == ("legacy_completed",)


def test_migrated_legacy_approval_is_readable_but_service_immutable(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _create_v1_fixture(db_path)
    initialize_database(db_path)
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    service = ApprovalService(ApprovalStore(db_path), audit_writer, timedelta(minutes=15))
    context = AdminPrincipalContext(
        principal_id="admin:local-ui",
        principal_type="admin",
        roles=("Admin",),
        authentication_method="local_admin_bearer",
        identity_source="principal_registry",
        identity_generation="sha256:" + ("7" * 64),
    )

    approval = service.get("appr_v1")

    assert approval.status is ApprovalStatus.LEGACY_UNBOUND
    with pytest.raises(ApprovalError, match="not pending: legacy_unbound"):
        service.approve(approval.approval_id, context=context)
    with pytest.raises(ApprovalError, match="legacy approval is immutable"):
        service.begin_execution(approval.approval_id, approval.request_hash)


def test_restart_is_idempotent_and_preserves_v2_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        _insert_v2_generic_approval(connection)
        connection.commit()

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT approval_id, status, approval_contract_version FROM approvals"
        ).fetchone()
    assert row == ("appr_v2", "v2_pending", "2")


@pytest.mark.parametrize(
    ("key", "value"),
    [("schema_version", "3"), ("minimum_writer_version", "3")],
)
def test_newer_database_or_minimum_writer_is_rejected(
    tmp_path: Path,
    key: str,
    value: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute("UPDATE app_metadata SET value = ? WHERE key = ?", (value, key))
        connection.commit()

    with pytest.raises(DatabaseMigrationError, match="newer than this writer"):
        initialize_database(db_path)


def test_corrupt_v2_schema_is_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.executemany(
            "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
            [("schema_version", "2"), ("minimum_writer_version", "2")],
        )
        connection.execute("CREATE TABLE approvals (approval_id TEXT PRIMARY KEY)")
        connection.commit()

    with pytest.raises(DatabaseMigrationError, match="incomplete|missing"):
        initialize_database(db_path)


def test_v2_schema_with_required_columns_but_weakened_constraints_is_rejected(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        original_sql = _table_sql(connection, "approvals")
        weakened_sql = original_sql.replace(
            "decision_authority_snapshot_hash = promotion_authority_hash",
            "decision_authority_snapshot_hash IS NOT NULL",
        ).replace("CREATE TABLE approvals", "CREATE TABLE approvals_weakened", 1)
        connection.execute(weakened_sql)
        connection.execute("DROP TABLE approvals")
        connection.execute("ALTER TABLE approvals_weakened RENAME TO approvals")
        connection.commit()

    with pytest.raises(DatabaseMigrationError, match="constraints are incomplete: approvals"):
        initialize_database(db_path)


def test_interrupted_migration_rolls_back_without_mixed_tables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _create_v1_fixture(db_path)

    def interrupt(_: sqlite3.Connection) -> None:
        raise sqlite3.OperationalError("simulated migration interruption")

    monkeypatch.setattr(migration, "_create_v2_tables", interrupt)
    with pytest.raises(sqlite3.OperationalError, match="interruption"):
        initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        schema_version = connection.execute(
            "SELECT value FROM app_metadata WHERE key = 'schema_version'"
        ).fetchone()
    assert "approvals" in tables
    assert "approvals_v1" not in tables
    assert "trusted_host_promotion_proposals_v1" not in tables
    assert schema_version == ("1",)


def test_previous_writer_contract_cannot_mutate_migrated_or_v2_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _create_v1_fixture(db_path)
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        _insert_v2_generic_approval(connection)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE approvals SET status = 'approved' WHERE approval_id = 'appr_v2'"
            )
        with pytest.raises(sqlite3.IntegrityError):
            _old_approval_insert(connection)
        with pytest.raises(sqlite3.IntegrityError):
            _old_proposal_insert(connection)
        with pytest.raises(sqlite3.IntegrityError):
            _old_attempt_insert(connection)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                UPDATE approvals
                SET decided_at = '2026-01-01T00:00:00+00:00',
                    deciding_principal_id = 'caller:spoofed',
                    deciding_principal_generation = ?,
                    decision_reason_hash = ?, decision_hash = ?
                WHERE approval_id = 'appr_v2'
                """,
                (
                    "sha256:" + ("1" * 64),
                    "sha256:" + ("2" * 64),
                    "sha256:" + ("3" * 64),
                ),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE approvals SET executor_principal_id = 'caller:partial' "
                "WHERE approval_id = 'appr_v2'"
            )
        statuses = dict(
            connection.execute(
                "SELECT proposal_id, status FROM trusted_host_promotion_proposals"
            )
        )
    assert statuses["thp_v1"] == "legacy_unbound"
    assert all(status != "approval_required" for status in statuses.values())


def test_frozen_v1_writer_fixture_hashes_match_authorized_baseline() -> None:
    approvals_source = subprocess.run(
        [
            "git",
            "show",
            f"{BASELINE_COMMIT}:apps/api/src/ithildin_api/approvals.py",
        ],
        check=True,
        capture_output=True,
    ).stdout
    promotions_source = subprocess.run(
        [
            "git",
            "show",
            f"{BASELINE_COMMIT}:apps/api/src/ithildin_api/trusted_host_promotions.py",
        ],
        check=True,
        capture_output=True,
    ).stdout
    assert hashlib.sha256(approvals_source).hexdigest() == BASELINE_APPROVALS_SHA256
    assert hashlib.sha256(promotions_source).hexdigest() == BASELINE_PROMOTIONS_SHA256


def _create_v1_fixture(
    db_path: Path,
    *,
    approval_status: str = "pending",
    proposal_status: str = "approval_required",
    attempt_status: str = "prepared",
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO app_metadata (key, value) VALUES ('schema_version', '1')"
        )
        connection.execute(
            """
            CREATE TABLE approvals (
                approval_id TEXT PRIMARY KEY, request_id TEXT NOT NULL,
                request_hash TEXT NOT NULL, principal_json TEXT NOT NULL,
                tool_name TEXT NOT NULL, resource_json TEXT NOT NULL,
                status TEXT NOT NULL, summary TEXT NOT NULL, expires_at TEXT NOT NULL,
                one_time_scope_json TEXT NOT NULL, metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                decided_by TEXT, decision_reason TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO approvals VALUES (
                'appr_v1', 'req_v1', ?, '{"id":"agent:v1"}',
                'trusted_host.promotion.stage', '{"type":"promotion"}', ?,
                'legacy approval', '2030-01-01T00:00:00+00:00', '{}', '{}',
                '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00',
                'legacy-user', 'legacy reason'
            )
            """,
            ("sha256:" + ("a" * 64), approval_status),
        )
        connection.execute(
            """
            CREATE TABLE trusted_host_promotion_proposals (
                proposal_id TEXT PRIMARY KEY, request_id TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                workspace_id TEXT NOT NULL, sandbox_descriptor_id TEXT NOT NULL,
                sandbox_descriptor_hash TEXT NOT NULL, sandbox_id TEXT NOT NULL,
                source_artifact_label TEXT NOT NULL, host_staging_label TEXT NOT NULL,
                artifact_sha256 TEXT NOT NULL, artifact_size_bytes INTEGER NOT NULL,
                artifact_media_label TEXT NOT NULL, proposal_hash TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO trusted_host_promotion_proposals VALUES (
                'thp_v1', 'req_v1', ?, '2026-01-01T00:00:00+00:00',
                '2026-01-01T00:00:00+00:00', 'default', 'sdesc_v1', ?,
                'sandbox-v1', 'sandbox://sandbox-v1/a.txt', 'host-staging://a',
                ?, 1, 'text/plain', ?, '{}'
            )
            """,
            (
                proposal_status,
                "sha256:" + ("b" * 64),
                "sha256:" + ("c" * 64),
                "sha256:" + ("d" * 64),
            ),
        )
        connection.execute(
            """
            CREATE TABLE trusted_host_promotion_attempts (
                attempt_id TEXT PRIMARY KEY, approval_id TEXT NOT NULL UNIQUE,
                proposal_id TEXT NOT NULL, request_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL, host_staging_label TEXT NOT NULL,
                artifact_sha256 TEXT NOT NULL, staged_sha256 TEXT, status TEXT NOT NULL,
                failure_reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO trusted_host_promotion_attempts VALUES (
                'thpa_v1', 'appr_v1', 'thp_v1', 'req_v1', 'default',
                'host-staging://a', ?, NULL, ?, NULL,
                '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', '{}'
            )
            """,
            ("sha256:" + ("c" * 64), attempt_status),
        )
        connection.commit()


def _insert_v2_generic_approval(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO approvals (
            approval_id, request_id, request_hash, principal_json, tool_name,
            resource_json, status, summary, expires_at, one_time_scope_json,
            metadata_json, created_at, updated_at, approval_contract_version,
            requester_principal_id, requester_principal_generation
        ) VALUES (
            'appr_v2', 'req_v2', ?, '{"id":"agent:v2"}', 'fs.patch.apply',
            '{}', 'v2_pending', 'v2 approval', '2030-01-01T00:00:00+00:00',
            '{}', '{}', '2026-01-01T00:00:00+00:00',
            '2026-01-01T00:00:00+00:00', '2', 'agent:v2', ?
        )
        """,
        ("sha256:" + ("e" * 64), "sha256:" + ("f" * 64)),
    )


def _old_approval_insert(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO approvals (
            approval_id, request_id, request_hash, principal_json, tool_name,
            resource_json, status, summary, expires_at, one_time_scope_json,
            metadata_json, created_at, updated_at
        ) VALUES ('old_appr', 'old_req', ?, '{}', 'fs.patch.apply', '{}',
            'pending', 'old', '2030-01-01T00:00:00+00:00', '{}', '{}',
            '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')
        """,
        ("sha256:" + ("1" * 64),),
    )


def _old_proposal_insert(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO trusted_host_promotion_proposals (
            proposal_id, request_id, status, created_at, updated_at, workspace_id,
            sandbox_descriptor_id, sandbox_descriptor_hash, sandbox_id,
            source_artifact_label, host_staging_label, artifact_sha256,
            artifact_size_bytes, artifact_media_label, proposal_hash, metadata_json
        ) VALUES ('old_thp', 'old_req', 'approval_required',
            '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00',
            'default', 'sdesc_old', ?, 'sandbox-old', 'sandbox://old/a.txt',
            'host-staging://old', ?, 1, 'text/plain', ?, '{}')
        """,
        (
            "sha256:" + ("2" * 64),
            "sha256:" + ("3" * 64),
            "sha256:" + ("4" * 64),
        ),
    )


def _old_attempt_insert(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO trusted_host_promotion_attempts (
            attempt_id, approval_id, proposal_id, request_id, workspace_id,
            host_staging_label, artifact_sha256, staged_sha256, status,
            failure_reason, created_at, updated_at, metadata_json
        ) VALUES ('old_thpa', 'old_appr', 'old_thp', 'old_req', 'default',
            'host-staging://old', ?, NULL, 'prepared', NULL,
            '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', '{}')
        """,
        ("sha256:" + ("3" * 64),),
    )


def _table_sql(connection: sqlite3.Connection, table: str) -> str:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    assert row is not None
    return str(row[0])

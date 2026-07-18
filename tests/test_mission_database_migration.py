from __future__ import annotations

import importlib.util
import json
import shutil
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import ithildin_api.trusted_host_promotion_v2_migration as migration
import pytest
from ithildin_api.database import initialize_database
from ithildin_api.database_migration_backup import (
    DatabaseBackupError,
    pre_v4_backup_paths,
)
from ithildin_api.trusted_host_promotion_v2_migration import DatabaseMigrationError

V3_BASELINE_COMMIT = "3967046333fcf70e9ad218284c232a162e1ec15f"
MISSION_TABLES = (
    "missions",
    "mission_audit_evidence_bindings",
    "mission_transition_attempts",
    "mission_claims",
    "mission_report_receipts",
    "mission_report_nonces",
)


def test_schema_four_creates_closed_mission_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        mission_sql = _table_sql(connection, "missions")
        transition_sql = _table_sql(connection, "mission_transition_attempts")
        evidence_sql = _table_sql(connection, "mission_audit_evidence_bindings")
        report_sql = _table_sql(connection, "mission_report_receipts")
    assert metadata["schema_version"] == "4"
    assert metadata["minimum_writer_version"] == "4"
    assert set(MISSION_TABLES) <= tables
    assert "requester_identity_generation" in mission_sql
    assert "synthetic_read_review_v1" in mission_sql
    assert "evidence_incomplete" in transition_sql
    assert "audit_event_hash" in transition_sql
    assert "audit_event_hash TEXT NOT NULL UNIQUE" in evidence_sql
    assert "owner_id TEXT NOT NULL UNIQUE" in evidence_sql
    assert "report_kind = 'runner_failed' AND outcome_code = 'failed'" in report_sql
    assert "failure_reason_code" in report_sql


def test_schema_four_rejects_semantically_invalid_report_receipts(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO mission_report_receipts (
                    report_id, mission_id, claim_id, node_id,
                    verified_node_identity_key_id, envelope_digest,
                    expected_lifecycle_revision, report_kind, outcome_code,
                    reason_code, artifact_digest, request_digest,
                    receipt_posture_json, receipt_disposition, evidence_status,
                    audit_event_id, audit_event_hash, failure_reason_code,
                    received_at, finalized_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, '{}',
                    'pending', 'pending', NULL, NULL, NULL, ?, NULL)
                """,
                (
                    "mreport_" + ("1" * 32),
                    "mission_" + ("2" * 32),
                    "mclaim_" + ("3" * 32),
                    "node_" + ("4" * 32),
                    "sha256:" + ("5" * 64),
                    "sha256:" + ("6" * 64),
                    2,
                    "runner_succeeded",
                    "failed",
                    "sha256:" + ("7" * 64),
                    "2026-07-18T12:00:00+00:00",
                ),
            )


def test_v3_upgrade_creates_private_backup_receipt_and_restore_only_copy(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _make_v3_database(db_path)

    initialize_database(db_path)

    backup_path, receipt_path = pre_v4_backup_paths(db_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert stat.S_IMODE(backup_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert receipt["source_schema_version"] == "3"
    assert receipt["migration_target_schema_version"] == "4"
    assert receipt["downgrade_posture"] == "restore_only"
    assert receipt["backup_filename"] == backup_path.name
    assert str(tmp_path) not in receipt_path.read_text(encoding="utf-8")
    with sqlite3.connect(backup_path) as connection:
        backup_metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
        backup_tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert backup_metadata["schema_version"] == "3"
    assert not (set(MISSION_TABLES) & backup_tables)


def test_interrupted_v3_upgrade_rolls_back_and_reuses_exact_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _make_v3_database(db_path)

    def interrupt(connection: sqlite3.Connection) -> None:
        original(connection)
        raise sqlite3.OperationalError("simulated mission migration interruption")

    original = migration._create_mission_tables
    monkeypatch.setattr(migration, "_create_mission_tables", interrupt)
    with pytest.raises(sqlite3.OperationalError, match="mission migration interruption"):
        initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert metadata["schema_version"] == "3"
    assert not (set(MISSION_TABLES) & tables)
    backup_path, receipt_path = pre_v4_backup_paths(db_path)
    original_backup = backup_path.read_bytes()
    original_receipt = receipt_path.read_bytes()

    monkeypatch.setattr(migration, "_create_mission_tables", original)
    initialize_database(db_path)

    assert backup_path.read_bytes() == original_backup
    assert receipt_path.read_bytes() == original_receipt


def test_v3_writer_refuses_v4_and_restore_only_copy_remains_v3(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _make_v3_database(db_path)
    initialize_database(db_path)
    backup_path, _ = pre_v4_backup_paths(db_path)
    v3_writer = _load_v3_migration(tmp_path)

    with pytest.raises(v3_writer.DatabaseMigrationError, match="newer than this writer"):
        v3_writer.initialize_or_migrate_database(db_path)

    restored = tmp_path / "restored-v3.sqlite3"
    shutil.copyfile(backup_path, restored)
    v3_writer.initialize_or_migrate_database(restored)
    with sqlite3.connect(restored) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
    assert metadata["schema_version"] == "3"
    assert metadata["minimum_writer_version"] == "3"


def test_backup_receipt_tamper_blocks_retry(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _make_v3_database(db_path)

    def interrupt(_: sqlite3.Connection) -> None:
        raise sqlite3.OperationalError("stop after backup")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(migration, "_create_mission_tables", interrupt)
        with pytest.raises(sqlite3.OperationalError):
            initialize_database(db_path)
    _, receipt_path = pre_v4_backup_paths(db_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["source_schema_version"] = "2"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    receipt_path.chmod(0o600)

    with pytest.raises(DatabaseBackupError, match="source_schema_version mismatch"):
        initialize_database(db_path)


def test_backup_artifact_symlink_blocks_retry(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _make_v3_database(db_path)

    def interrupt(_: sqlite3.Connection) -> None:
        raise sqlite3.OperationalError("stop after backup")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(migration, "_create_mission_tables", interrupt)
        with pytest.raises(sqlite3.OperationalError):
            initialize_database(db_path)
    backup_path, _ = pre_v4_backup_paths(db_path)
    moved_backup = tmp_path / "moved-backup.sqlite3"
    backup_path.rename(moved_backup)
    backup_path.symlink_to(moved_backup)

    with pytest.raises(DatabaseBackupError, match="regular file"):
        initialize_database(db_path)


def test_weakened_mission_schema_is_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        sql = _table_sql(connection, "missions")
        weakened = sql.replace(
            "mission_template_id = 'synthetic_read_review_v1'",
            "length(mission_template_id) > 0",
        ).replace("CREATE TABLE missions", "CREATE TABLE missions_weakened", 1)
        connection.execute("DROP INDEX missions_updated_idx")
        connection.execute(weakened)
        connection.execute("DROP TABLE missions")
        connection.execute("ALTER TABLE missions_weakened RENAME TO missions")
        connection.execute(
            "CREATE INDEX missions_updated_idx ON missions(updated_at DESC, mission_id)"
        )
        connection.commit()

    with pytest.raises(DatabaseMigrationError, match="table schema differs: missions"):
        initialize_database(db_path)


def test_missing_mission_index_is_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP INDEX mission_report_receipts_mission_idx")
        connection.commit()

    with pytest.raises(
        DatabaseMigrationError,
        match="Mission Command index differs: mission_report_receipts_mission_idx",
    ):
        initialize_database(db_path)


def test_unexpected_mission_trigger_is_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER mission_state_rewrite
            AFTER UPDATE ON missions
            BEGIN
                UPDATE missions SET workspace_id = 'tampered'
                WHERE mission_id = NEW.mission_id;
            END
            """
        )
        connection.commit()

    with pytest.raises(
        DatabaseMigrationError,
        match="Mission Command schema has unexpected objects",
    ):
        initialize_database(db_path)


def test_missing_mission_foreign_key_is_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        sql = _table_sql(connection, "mission_report_receipts")
        weakened = sql.replace(
            "FOREIGN KEY (mission_id, claim_id, node_id, envelope_digest)\n"
            "                REFERENCES mission_claims("
            "mission_id, claim_id, node_id, envelope_digest),",
            "",
        ).replace(
            "CREATE TABLE mission_report_receipts",
            "CREATE TABLE mission_report_receipts_weakened",
            1,
        )
        assert weakened != sql.replace(
            "CREATE TABLE mission_report_receipts",
            "CREATE TABLE mission_report_receipts_weakened",
            1,
        )
        connection.execute("DROP INDEX mission_report_receipts_mission_idx")
        connection.execute(weakened)
        connection.execute("DROP TABLE mission_report_receipts")
        connection.execute(
            "ALTER TABLE mission_report_receipts_weakened "
            "RENAME TO mission_report_receipts"
        )
        connection.execute(
            "CREATE INDEX mission_report_receipts_mission_idx "
            "ON mission_report_receipts(mission_id, received_at DESC)"
        )
        connection.commit()

    with pytest.raises(
        DatabaseMigrationError,
        match="Mission Command table schema differs: mission_report_receipts",
    ):
        initialize_database(db_path)


def _make_v3_database(db_path: Path) -> None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        for table in reversed(MISSION_TABLES):
            connection.execute(f"DROP TABLE {table}")
        connection.execute(
            "UPDATE app_metadata SET value = '3' "
            "WHERE key IN ('schema_version', 'minimum_writer_version')"
        )
        connection.commit()


def _load_v3_migration(tmp_path: Path) -> ModuleType:
    source = subprocess.run(
        [
            "git",
            "show",
            f"{V3_BASELINE_COMMIT}:apps/api/src/ithildin_api/"
            "trusted_host_promotion_v2_migration.py",
        ],
        check=True,
        capture_output=True,
    ).stdout
    module_path = tmp_path / "frozen_v3_migration.py"
    module_path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("ithildin_frozen_v3_migration", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _table_sql(connection: sqlite3.Connection, table: str) -> str:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    assert row is not None
    return str(row[0])

from __future__ import annotations

import importlib.util
import json
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import ithildin_api.trusted_host_promotion_v2_migration as migration
import pytest
from ithildin_api.database import initialize_database
from ithildin_api.database_migration_backup import pre_v7_backup_paths
from ithildin_api.node_configuration import NodeConfigurationStore
from ithildin_api.node_configuration_trust import (
    NodeConfigurationTrustTransitionStore,
)
from ithildin_api.nodes import NodeStore
from ithildin_api.trusted_host_promotion_v2_migration import DatabaseMigrationError
from ithildin_audit_core import AuditWriter

from scripts import (
    local_v1_lv1_003_o4_attempt008_node_identity_reconciliation as reconciliation,
)

SCHEMA_SIX_COMMIT = "83db1196213b0e4e7de5d97ab0fb37b934ca4ab7"
EXPECTED_PIS005A_SCHEMA_FINGERPRINT = (
    "sha256:5b804d92cd45385b5f21cd4a31b7c641ef35a6d5f4ea5ac0339ebdfebe67b9c5"
)


def test_schema_seven_has_exact_pis005a_objects_and_preserves_pis004a_digest(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)

    assert migration.expected_pis004a_schema_fingerprint() == (
        "sha256:ca52764e2c4544446f0a1379abc60ec6d74a9320222509974d1cb35c1c955114"
    )
    assert migration.expected_pis005a_schema_fingerprint() == EXPECTED_PIS005A_SCHEMA_FINGERPRINT
    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
        migration.verify_pis004a_schema(connection)
        migration.verify_pis005a_schema(connection)
        objects = connection.execute(
            """
            SELECT type, name FROM sqlite_master
            WHERE sql IS NOT NULL
              AND (
                  lower(name) GLOB 'node_workload_*'
                  OR lower(tbl_name) GLOB 'node_workload_*'
              )
            ORDER BY type, name
            """
        ).fetchall()
        columns = {
            table: {
                str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for table in migration.PIS005A_TABLE_COLUMNS
        }
    assert metadata == {
        "schema_version": "7",
        "minimum_writer_version": "7",
    }
    assert len(objects) == 13
    assert {name for object_type, name in objects if object_type == "table"} == set(
        migration.PIS005A_TABLE_COLUMNS
    )
    assert {name for object_type, name in objects if object_type == "index"} == set(
        migration.PIS005A_INDEX_NAMES
    )
    forbidden = {
        "enrollment_secret",
        "digest_key",
        "certificate_der",
        "certificate_private_key",
        "application_private_key",
        "signature",
        "request_body",
    }
    assert all(not (table_columns & forbidden) for table_columns in columns.values())


def test_schema_six_upgrade_creates_private_restore_only_backup_and_old_writer_refuses(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)

    initialize_database(db_path)

    backup_path, receipt_path = pre_v7_backup_paths(db_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert stat.S_IMODE(backup_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert receipt["source_schema_version"] == "6"
    assert receipt["source_minimum_writer_version"] == "6"
    assert receipt["migration_target_schema_version"] == "7"
    assert receipt["downgrade_posture"] == "restore_only"
    with sqlite3.connect(backup_path) as connection:
        backup_metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
        workload_objects = connection.execute(
            """
            SELECT count(*) FROM sqlite_master
            WHERE lower(name) GLOB 'node_workload_*'
               OR lower(tbl_name) GLOB 'node_workload_*'
            """
        ).fetchone()
    assert backup_metadata == {
        "schema_version": "6",
        "minimum_writer_version": "6",
    }
    assert workload_objects == (0,)
    frozen.verify_database_v2(backup_path)
    with pytest.raises(frozen.DatabaseMigrationError, match="newer than this writer"):
        frozen.initialize_or_migrate_database(db_path)
    with sqlite3.connect(db_path) as connection:
        assert dict(connection.execute("SELECT key, value FROM app_metadata")) == {
            "schema_version": "7",
            "minimum_writer_version": "7",
        }


def test_interrupted_v6_to_v7_upgrade_rolls_back_and_reuses_exact_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    original = migration._create_pis005a_tables

    def interrupt(connection: sqlite3.Connection) -> None:
        original(connection)
        raise sqlite3.OperationalError("simulated PIS-005A migration interruption")

    monkeypatch.setattr(migration, "_create_pis005a_tables", interrupt)
    with pytest.raises(sqlite3.OperationalError, match="PIS-005A migration interruption"):
        initialize_database(db_path)
    backup_path, receipt_path = pre_v7_backup_paths(db_path)
    backup_bytes = backup_path.read_bytes()
    receipt_bytes = receipt_path.read_bytes()
    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
        workload_objects = connection.execute(
            """
            SELECT count(*) FROM sqlite_master
            WHERE lower(name) GLOB 'node_workload_*'
               OR lower(tbl_name) GLOB 'node_workload_*'
            """
        ).fetchone()
    assert metadata == {
        "schema_version": "6",
        "minimum_writer_version": "6",
    }
    assert workload_objects == (0,)

    monkeypatch.setattr(migration, "_create_pis005a_tables", original)
    initialize_database(db_path)
    assert backup_path.read_bytes() == backup_bytes
    assert receipt_path.read_bytes() == receipt_bytes


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            "DROP INDEX node_workload_request_nonces_expiry_idx",
            "PIS-005A index differs",
        ),
        (
            "CREATE TABLE NODE_WORKLOAD_UNEXPECTED (value TEXT)",
            "PIS-005A schema has unexpected objects",
        ),
    ],
)
def test_pis005a_index_and_unexpected_object_drift_fail_closed(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(mutation)
        connection.commit()
    with pytest.raises(DatabaseMigrationError, match=message):
        initialize_database(db_path)


def test_pis005a_table_constraint_drift_fails_closed(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE type = 'table' AND name = 'node_workload_request_nonces'
            """
        ).fetchone()
        assert row is not None
        weakened = (
            str(row[0])
            .replace(
                "CREATE TABLE node_workload_request_nonces",
                "CREATE TABLE node_workload_request_nonces_weakened",
                1,
            )
            .replace(
                "CHECK (expires_at > accepted_at)",
                "CHECK (expires_at >= accepted_at)",
                1,
            )
        )
        connection.execute("DROP INDEX node_workload_request_nonces_expiry_idx")
        connection.execute(
            "ALTER TABLE node_workload_request_nonces "
            "RENAME TO node_workload_request_nonces_original"
        )
        connection.execute(weakened)
        connection.execute("DROP TABLE node_workload_request_nonces_original")
        connection.execute(
            """
            ALTER TABLE node_workload_request_nonces_weakened
            RENAME TO node_workload_request_nonces
            """
        )
        connection.execute(
            """
            CREATE INDEX node_workload_request_nonces_expiry_idx
            ON node_workload_request_nonces(expires_at, node_id)
            """
        )
        connection.commit()
    with pytest.raises(
        DatabaseMigrationError,
        match="PIS-005A table schema differs: node_workload_request_nonces",
    ):
        initialize_database(db_path)


def test_partial_pis005a_objects_block_schema_six_migration(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE node_workload_partial (value TEXT)")
        connection.commit()
    with pytest.raises(
        DatabaseMigrationError,
        match="database v6 contains unexpected PIS-005A objects",
    ):
        initialize_database(db_path)


def test_digest_key_active_uniqueness_is_enforced_by_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    now = "2026-07-29T18:00:00+00:00"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO node_workload_enrollment_digest_key_generations (
                digest_key_generation, status, first_seen_at, activated_at, retired_at
            ) VALUES (1, 'active', ?, ?, NULL)
            """,
            (now, now),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO node_workload_enrollment_digest_key_generations (
                    digest_key_generation, status, first_seen_at,
                    activated_at, retired_at
                ) VALUES (2, 'active', ?, ?, NULL)
                """,
                (now, now),
            )


def test_attempt008_rejects_nonempty_pis005a_state_and_future_schema(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    NodeStore(db_path).initialize()
    NodeConfigurationStore(db_path).initialize()
    NodeConfigurationTrustTransitionStore(db_path).initialize()
    AuditWriter(db_path, tmp_path / "audit.jsonl").initialize()
    with sqlite3.connect(db_path) as connection:
        assert reconciliation._validate_schema_shape(connection) == {  # noqa: SLF001
            "schema_version": "7",
            "minimum_writer_version": "7",
        }
        now = "2026-07-29T18:00:00+00:00"
        connection.execute(
            """
            INSERT INTO node_workload_enrollment_digest_key_generations (
                digest_key_generation, status, first_seen_at, activated_at, retired_at
            ) VALUES (1, 'active', ?, ?, NULL)
            """,
            (now, now),
        )
        with pytest.raises(
            reconciliation.ReconciliationError,
            match="identity_unresolved_reconciliation_required",
        ):
            reconciliation._validate_schema_shape(connection)  # noqa: SLF001
        connection.execute("DELETE FROM node_workload_enrollment_digest_key_generations")
        connection.execute(
            """
            UPDATE app_metadata SET value = '8'
            WHERE key IN ('schema_version', 'minimum_writer_version')
            """
        )
        with pytest.raises(
            reconciliation.ReconciliationError,
            match="identity_unresolved_reconciliation_required",
        ):
            reconciliation._validate_schema_shape(connection)  # noqa: SLF001


def _load_schema_six_migration(tmp_path: Path) -> ModuleType:
    source = subprocess.run(
        [
            "git",
            "show",
            f"{SCHEMA_SIX_COMMIT}:apps/api/src/ithildin_api/trusted_host_promotion_v2_migration.py",
        ],
        check=True,
        capture_output=True,
    ).stdout
    module_path = tmp_path / "frozen_schema_six_migration.py"
    module_path.write_bytes(source)
    spec = importlib.util.spec_from_file_location(
        "ithildin_frozen_schema_six_migration",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module

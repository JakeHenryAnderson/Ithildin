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
from ithildin_api.database_migration_backup import (
    DatabaseBackupError,
    pre_v5_backup_paths,
)
from ithildin_api.node_configuration import NodeConfigurationStore
from ithildin_api.node_configuration_trust import (
    NodeConfigurationTrustTransitionStore,
)
from ithildin_api.nodes import NodeStore
from ithildin_api.trusted_host_promotion_v2_migration import DatabaseMigrationError
from ithildin_audit_core import AuditWriter

from scripts import (
    local_v1_lv1_003_o4_attempt008_node_identity_reconciliation as node_reconciliation,
)

V4_SOURCE_COMMIT = "e86f5a19e4e067d73141246f78304597e6cc28a0"
PIS004A_TABLES = tuple(migration.PIS004A_TABLE_COLUMNS)


def test_schema_five_creates_exact_pis004a_tables_without_token_columns(
    tmp_path: Path,
) -> None:
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
        all_columns = {
            table: {
                str(row[1])
                for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for table in PIS004A_TABLES
        }
    assert metadata["schema_version"] == "5"
    assert metadata["minimum_writer_version"] == "5"
    assert set(PIS004A_TABLES) <= tables
    forbidden = {
        "authorization_code",
        "access_token",
        "id_token",
        "refresh_token",
        "claims",
        "session_handle",
        "csrf_token",
    }
    assert all(not (columns & forbidden) for columns in all_columns.values())
    assert "handle_digest" in all_columns["identity_sessions"]
    assert "session_audit_id" in all_columns["identity_sessions"]
    assert "subject" in all_columns["identity_bindings"]


def test_v4_upgrade_creates_private_restore_only_pre_v5_backup(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _make_v4_database(db_path)

    initialize_database(db_path)

    backup_path, receipt_path = pre_v5_backup_paths(db_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert stat.S_IMODE(backup_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert receipt["source_schema_version"] == "4"
    assert receipt["source_minimum_writer_version"] == "4"
    assert receipt["migration_target_schema_version"] == "5"
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
    assert backup_metadata["schema_version"] == "4"
    assert backup_metadata["minimum_writer_version"] == "4"
    assert not (set(PIS004A_TABLES) & backup_tables)


def test_interrupted_v4_upgrade_rolls_back_and_reuses_exact_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _make_v4_database(db_path)
    original = migration._create_pis004a_tables

    def interrupt(connection: sqlite3.Connection) -> None:
        original(connection)
        raise sqlite3.OperationalError("simulated PIS-004A migration interruption")

    monkeypatch.setattr(migration, "_create_pis004a_tables", interrupt)
    with pytest.raises(sqlite3.OperationalError, match="PIS-004A migration interruption"):
        initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert metadata["schema_version"] == "4"
    assert not (set(PIS004A_TABLES) & tables)
    backup_path, receipt_path = pre_v5_backup_paths(db_path)
    original_backup = backup_path.read_bytes()
    original_receipt = receipt_path.read_bytes()

    monkeypatch.setattr(migration, "_create_pis004a_tables", original)
    initialize_database(db_path)

    assert backup_path.read_bytes() == original_backup
    assert receipt_path.read_bytes() == original_receipt


def test_v4_writer_refuses_schema_five_and_backup_remains_v4(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _make_v4_database(db_path)
    initialize_database(db_path)
    backup_path, _ = pre_v5_backup_paths(db_path)
    frozen_v4 = _load_v4_migration(tmp_path)

    with pytest.raises(frozen_v4.DatabaseMigrationError, match="newer than this writer"):
        frozen_v4.initialize_or_migrate_database(db_path)

    with sqlite3.connect(backup_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
    assert metadata["schema_version"] == "4"
    assert metadata["minimum_writer_version"] == "4"


def test_tampered_pis004a_table_or_index_fails_closed(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP INDEX identity_sessions_idle_expiry_idx")
        connection.commit()

    with pytest.raises(
        DatabaseMigrationError,
        match="PIS-004A index differs: identity_sessions_idle_expiry_idx",
    ):
        initialize_database(db_path)


def test_attempt008_projection_binds_exact_schema_five_fingerprint(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    _initialize_attempt008_projection_schema(db_path, tmp_path / "audit.jsonl")

    assert (
        migration.expected_pis004a_schema_fingerprint()
        == node_reconciliation.EXPECTED_PIS004A_SCHEMA_FINGERPRINT
    )
    with sqlite3.connect(db_path) as connection:
        assert node_reconciliation._validate_schema_shape(connection) == {  # noqa: SLF001
            "schema_version": "5",
            "minimum_writer_version": "5",
        }


@pytest.mark.parametrize(
    "mutation",
    [
        "DROP INDEX identity_sessions_idle_expiry_idx",
        "CREATE TABLE identity_unexpected (value TEXT)",
        "CREATE TABLE IDENTITY_UNEXPECTED (value TEXT)",
        "ALTER TABLE identity_sessions ADD COLUMN unexpected TEXT",
        (
            "DROP INDEX identity_oidc_replays_expiry_idx; "
            "CREATE INDEX identity_oidc_replays_expiry_idx "
            "ON identity_oidc_replays(first_seen_at)"
        ),
    ],
)
def test_attempt008_projection_rejects_schema_five_object_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    _initialize_attempt008_projection_schema(db_path, tmp_path / "audit.jsonl")

    with sqlite3.connect(db_path) as connection:
        connection.executescript(mutation)
        _assert_attempt008_schema_rejected(connection)


@pytest.mark.parametrize(
    "weakened_schema",
    [
        """
        DROP TABLE identity_organizations;
        CREATE TABLE identity_organizations (
            organization_id TEXT PRIMARY KEY,
            enabled INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
        """
        DROP TABLE identity_provider_configurations;
        CREATE TABLE identity_provider_configurations (
            provider_configuration_id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            exact_issuer TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            generation INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (length(provider_configuration_id) = 37
                AND substr(provider_configuration_id, 1, 5) = 'idpc_'
                AND substr(provider_configuration_id, 6) NOT GLOB '*[^0-9a-f]*'),
            CHECK (length(exact_issuer) BETWEEN 9 AND 2048),
            CHECK (enabled IN (0, 1)),
            CHECK (generation >= 1),
            CHECK (updated_at >= created_at),
            UNIQUE (organization_id, provider_configuration_id),
            UNIQUE (organization_id, provider_configuration_id, exact_issuer)
        );
        """,
        """
        DROP TABLE identity_provider_configurations;
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
            CHECK (updated_at >= created_at)
        );
        """,
    ],
    ids=["check_removed", "foreign_key_removed", "unique_removed"],
)
def test_attempt008_projection_rejects_same_column_constraint_drift(
    tmp_path: Path,
    weakened_schema: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    _initialize_attempt008_projection_schema(db_path, tmp_path / "audit.jsonl")

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.executescript(weakened_schema)
        _assert_attempt008_schema_rejected(connection)


def test_pre_v5_receipt_tamper_blocks_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    _make_v4_database(db_path)

    def interrupt(_: sqlite3.Connection) -> None:
        raise sqlite3.OperationalError("stop after pre-v5 backup")

    monkeypatch.setattr(migration, "_create_pis004a_tables", interrupt)
    with pytest.raises(sqlite3.OperationalError, match="stop after pre-v5 backup"):
        initialize_database(db_path)
    _, receipt_path = pre_v5_backup_paths(db_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["migration_target_schema_version"] = "6"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    receipt_path.chmod(0o600)

    with pytest.raises(DatabaseBackupError, match="migration_target_schema_version mismatch"):
        initialize_database(db_path)


def _make_v4_database(db_path: Path) -> None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        for table in reversed(PIS004A_TABLES):
            connection.execute(f"DROP TABLE {table}")
        connection.execute(
            "UPDATE app_metadata SET value = '4' "
            "WHERE key IN ('schema_version', 'minimum_writer_version')"
        )
        connection.commit()


def _initialize_attempt008_projection_schema(
    db_path: Path,
    audit_path: Path,
) -> None:
    NodeStore(db_path).initialize()
    NodeConfigurationStore(db_path).initialize()
    NodeConfigurationTrustTransitionStore(db_path).initialize()
    AuditWriter(db_path, audit_path).initialize()


def _assert_attempt008_schema_rejected(connection: sqlite3.Connection) -> None:
    with pytest.raises(
        node_reconciliation.ReconciliationError,
        match="identity_unresolved_reconciliation_required",
    ):
        node_reconciliation._validate_schema_shape(connection)  # noqa: SLF001


def _load_v4_migration(tmp_path: Path) -> ModuleType:
    source = subprocess.run(
        [
            "git",
            "show",
            f"{V4_SOURCE_COMMIT}:apps/api/src/ithildin_api/"
            "trusted_host_promotion_v2_migration.py",
        ],
        check=True,
        capture_output=True,
    ).stdout
    module_path = tmp_path / "frozen_v4_migration.py"
    module_path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("ithildin_frozen_v4_migration", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module

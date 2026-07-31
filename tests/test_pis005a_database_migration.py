from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import ithildin_api.database_migration_backup as migration_backup
import ithildin_api.trusted_host_promotion_v2_migration as migration
import pytest
from ithildin_api.database import initialize_database
from ithildin_api.database_migration_backup import (
    PRE_V7_MARKER_KEY,
    BackupGuard,
    DatabaseBackupError,
    DatabaseBackupRecoveryRequired,
    DatabaseMigrationOutcomeUnknown,
    content_addressed_anchor_path,
    pre_v7_backup_paths,
)
from ithildin_api.node_configuration import NodeConfigurationStore
from ithildin_api.node_configuration_trust import (
    NodeConfigurationTrustTransitionStore,
)
from ithildin_api.nodes import NodeStore
from ithildin_api.trusted_host_promotion_v2_migration import DatabaseMigrationError
from ithildin_audit_core import AuditWriter
from ithildin_schemas import canonical_json

from scripts import (
    local_v1_lv1_003_o4_attempt008_node_identity_reconciliation as reconciliation,
)

SCHEMA_SIX_COMMIT = "83db1196213b0e4e7de5d97ab0fb37b934ca4ab7"
REPAIR3_COMMIT = "afd13f98440d4cd9c032b6a996db133bdf78055d"
EXPECTED_PIS005A_SCHEMA_FINGERPRINT = (
    "sha256:d42147d48ab2cf7f193c340a7c60302dd61ec1fdd2112d072ebcd50bd5cccd82"
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
    initialize_database(db_path)


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
    assert receipt["backup_device"] == backup_path.stat().st_dev
    assert receipt["backup_inode"] == backup_path.stat().st_ino
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
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
    assert metadata["schema_version"] == "7"
    assert metadata["minimum_writer_version"] == "7"
    assert metadata[PRE_V7_MARKER_KEY] == receipt_path.read_text(encoding="utf-8").rstrip("\n")


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


def test_substituted_integrity_valid_backup_is_never_blessed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    substituted_path = tmp_path / "substituted.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    frozen.initialize_or_migrate_database(substituted_path)
    with sqlite3.connect(substituted_path) as connection:
        connection.execute(
            """
            INSERT INTO identity_organizations (
                organization_id, enabled, created_at, updated_at
            ) VALUES (?, 1, ?, ?)
            """,
            (
                "org_00000000000000000000000000000001",
                "2026-07-30T12:00:00+00:00",
                "2026-07-30T12:00:00+00:00",
            ),
        )
        connection.commit()
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)

    def substitute_after_guard_preparation(stage: str, guard: BackupGuard) -> None:
        if stage == "prepared_before_return":
            assert guard.db_path == db_path
            substituted_path.replace(db_path)

    monkeypatch.setattr(
        migration_backup,
        "_run_protocol_hook",
        substitute_after_guard_preparation,
    )

    with pytest.raises(
        DatabaseBackupError,
        match="database pathname identity changed",
    ):
        initialize_database(db_path)

    backup_path, receipt_path = pre_v7_backup_paths(db_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    backup_anchor = content_addressed_anchor_path(backup_path, receipt["backup_sha256"])
    assert backup_path.stat().st_ino == backup_anchor.stat().st_ino
    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
        assert metadata["schema_version"] == "6"
        assert metadata["minimum_writer_version"] == "6"
        assert PRE_V7_MARKER_KEY not in metadata
        assert connection.execute(
            """
            SELECT count(*) FROM sqlite_master
            WHERE lower(name) GLOB 'node_workload_*'
               OR lower(tbl_name) GLOB 'node_workload_*'
            """
        ).fetchone() == (0,)
        assert connection.execute(
            """
            SELECT count(*) FROM identity_organizations
            WHERE organization_id = 'org_00000000000000000000000000000001'
            """
        ).fetchone() == (1,)


def test_repair3_post_helper_integrity_valid_backup_substitution_cannot_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    substituted_path = tmp_path / "substituted.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    _create_distinct_schema_six_database(substituted_path, frozen)
    backup_path, _ = pre_v7_backup_paths(db_path)
    replacement_path = tmp_path / "integrity-valid-logical-substitution.sqlite3"
    attacked = False

    def substitute_after_helper(stage: str, _: BackupGuard) -> None:
        nonlocal attacked
        if stage == "prepared_before_return":
            shutil.copyfile(substituted_path, replacement_path)
            replacement_path.chmod(0o600)
            replacement_path.replace(backup_path)
            attacked = True

    monkeypatch.setattr(migration_backup, "_run_protocol_hook", substitute_after_helper)

    with pytest.raises(DatabaseBackupError, match="hardlink count|alias was substituted"):
        initialize_database(db_path)

    assert attacked is True
    _assert_schema_six_without_commit_marker(db_path)


def test_canonical_substitution_during_dual_publication_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    substituted_path = tmp_path / "substituted.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    _create_distinct_schema_six_database(substituted_path, frozen)
    substitution_observed = False

    def substitute_published_canonical(stage: str, artifact_name: str) -> None:
        nonlocal substitution_observed
        backup_path, _ = pre_v7_backup_paths(db_path)
        if stage == "canonical_published" and artifact_name == backup_path.name:
            substituted_path.replace(backup_path)
            substitution_observed = True

    monkeypatch.setattr(
        migration_backup,
        "_run_raw_protocol_hook",
        substitute_published_canonical,
    )

    with pytest.raises(
        DatabaseBackupError,
        match="hardlink count|alias was substituted",
    ):
        initialize_database(db_path)

    assert substitution_observed is True
    _assert_schema_six_without_commit_marker(db_path)


@pytest.mark.parametrize("failure_boundary", ["anchor_link", "temporary_unlink"])
def test_transient_partial_publication_failure_is_retryable_without_manual_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_boundary: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    backup_path, _ = pre_v7_backup_paths(db_path)
    failure_observed = False

    if failure_boundary == "anchor_link":
        original_link = migration_backup._link_no_clobber  # noqa: SLF001

        def fail_anchor_link_once(
            directory_fd: int,
            source_name: str,
            destination_name: str,
        ) -> None:
            nonlocal failure_observed
            if (
                not failure_observed
                and destination_name.startswith(f".{backup_path.name}.sha256-")
            ):
                failure_observed = True
                raise DatabaseBackupError("simulated transient alias link failure")
            original_link(directory_fd, source_name, destination_name)

        monkeypatch.setattr(
            migration_backup,
            "_link_no_clobber",
            fail_anchor_link_once,
        )
        expected_message = "simulated transient alias link failure"
    else:
        original_unlink_temporary = (
            migration_backup._unlink_publication_temporary  # noqa: SLF001
        )

        def fail_temporary_unlink_once(
            directory_fd: int,
            temporary_name: str,
            descriptor: int,
        ) -> None:
            nonlocal failure_observed
            if (
                not failure_observed
                and temporary_name.startswith(f".{backup_path.name}.")
                and temporary_name.endswith(".tmp")
            ):
                failure_observed = True
                raise DatabaseBackupError(
                    "migration backup publication temporary alias could not be removed"
                )
            original_unlink_temporary(directory_fd, temporary_name, descriptor)

        monkeypatch.setattr(
            migration_backup,
            "_unlink_publication_temporary",
            fail_temporary_unlink_once,
        )
        expected_message = "temporary alias could not be removed"

    with pytest.raises(DatabaseBackupError, match=expected_message):
        initialize_database(db_path)

    assert failure_observed is True
    _assert_schema_six_without_commit_marker(db_path)
    temporary_names = _publication_temporary_paths(backup_path)
    assert len(temporary_names) == 1
    if failure_boundary == "anchor_link":
        monkeypatch.setattr(migration_backup, "_link_no_clobber", original_link)
    else:
        monkeypatch.setattr(
            migration_backup,
            "_unlink_publication_temporary",
            original_unlink_temporary,
        )

    initialize_database(db_path)

    backup_path, receipt_path, backup_anchor, _ = _pre_v7_artifacts(db_path)
    assert backup_path.stat().st_ino == backup_anchor.stat().st_ino
    assert _publication_temporary_paths(backup_path) == []
    _assert_schema_seven_with_exact_marker(db_path, receipt_path)


def test_interrupted_receipt_publication_reuses_validated_payload_on_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    _, receipt_path = pre_v7_backup_paths(db_path)
    original_hook = migration_backup._run_raw_protocol_hook  # noqa: SLF001

    def interrupt_receipt(stage: str, artifact_name: str) -> None:
        if stage == "canonical_published" and artifact_name == receipt_path.name:
            raise DatabaseBackupError("leave interrupted receipt publication")

    monkeypatch.setattr(
        migration_backup,
        "_run_raw_protocol_hook",
        interrupt_receipt,
    )
    with pytest.raises(DatabaseBackupError, match="interrupted receipt publication"):
        initialize_database(db_path)

    _assert_schema_six_without_commit_marker(db_path)
    temporary_paths = _publication_temporary_paths(receipt_path)
    assert len(temporary_paths) == 1
    assert receipt_path.stat().st_ino == temporary_paths[0].stat().st_ino
    monkeypatch.setattr(
        migration_backup,
        "_run_raw_protocol_hook",
        original_hook,
    )
    initialize_database(db_path)

    _, receipt_path, _, receipt_anchor = _pre_v7_artifacts(db_path)
    assert receipt_path.stat().st_ino == receipt_anchor.stat().st_ino
    assert _publication_temporary_paths(receipt_path) == []
    _assert_schema_seven_with_exact_marker(db_path, receipt_path)


@pytest.mark.parametrize("substituted_alias", ["canonical", "anchor"])
def test_interrupted_publication_rejects_and_preserves_substituted_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    substituted_alias: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    backup_path, temporary_path, anchor_path = _leave_partial_backup_publication(
        db_path,
        monkeypatch,
    )
    competitor_payload = f"{substituted_alias} competitor".encode()
    competitor = tmp_path / f"{substituted_alias}-competitor"
    competitor.write_bytes(competitor_payload)
    competitor.chmod(0o600)
    if substituted_alias == "canonical":
        competitor.replace(backup_path)
        substituted_path = backup_path
    else:
        competitor.replace(anchor_path)
        substituted_path = anchor_path

    with pytest.raises(DatabaseBackupError, match="alias was substituted"):
        initialize_database(db_path)

    assert substituted_path.read_bytes() == competitor_payload
    assert temporary_path.is_file()
    _assert_schema_six_without_commit_marker(db_path)


def test_interrupted_publication_rejects_and_preserves_genuine_competitor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    backup_path, temporary_path, _ = _leave_partial_backup_publication(
        db_path,
        monkeypatch,
    )
    competitor = tmp_path / f".{backup_path.name}.sha256-{'0' * 64}"
    competitor.write_bytes(b"genuine competitor")
    competitor.chmod(0o600)

    with pytest.raises(DatabaseBackupError, match="unexpected competing anchor"):
        initialize_database(db_path)

    assert competitor.read_bytes() == b"genuine competitor"
    assert temporary_path.is_file()
    assert backup_path.is_file()
    _assert_schema_six_without_commit_marker(db_path)


def test_same_content_different_inode_during_ddl_fails_before_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    backup_path, _ = pre_v7_backup_paths(db_path)
    replacement_path = tmp_path / "same-content-different-inode.sqlite3"
    original_create_tables = migration._create_pis005a_tables

    def substitute_during_ddl(connection: sqlite3.Connection) -> None:
        original_create_tables(connection)
        shutil.copyfile(backup_path, replacement_path)
        replacement_path.chmod(0o600)
        replacement_path.replace(backup_path)

    monkeypatch.setattr(
        migration,
        "_create_pis005a_tables",
        substitute_during_ddl,
    )

    with pytest.raises(
        DatabaseBackupError,
        match="hardlink count|alias was substituted",
    ):
        initialize_database(db_path)

    _assert_schema_six_without_commit_marker(db_path)


def test_pre_v7_dual_aliases_exact_marker_and_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)

    initialize_database(db_path)

    backup_path, receipt_path, backup_anchor, receipt_anchor = _pre_v7_artifacts(db_path)
    assert backup_path.stat().st_ino == backup_anchor.stat().st_ino
    assert receipt_path.stat().st_ino == receipt_anchor.stat().st_ino
    assert backup_path.stat().st_nlink == 2
    assert receipt_path.stat().st_nlink == 2
    receipt_json = receipt_path.read_text(encoding="utf-8").rstrip("\n")
    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
    assert metadata[PRE_V7_MARKER_KEY] == receipt_json

    initialize_database(db_path)


@pytest.mark.parametrize(
    "stage",
    ["marker_bound", "after_precommit_check_before_commit"],
)
def test_post_schema_precommit_substitution_rolls_back_without_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    backup_path, _ = pre_v7_backup_paths(db_path)
    replacement_path = tmp_path / f"{stage}.sqlite3"
    attacked = False

    def substitute_at_stage(observed_stage: str, _: BackupGuard) -> None:
        nonlocal attacked
        if observed_stage == stage:
            shutil.copyfile(backup_path, replacement_path)
            replacement_path.chmod(0o600)
            replacement_path.replace(backup_path)
            attacked = True

    monkeypatch.setattr(migration_backup, "_run_protocol_hook", substitute_at_stage)
    with pytest.raises(DatabaseBackupError, match="hardlink count|alias was substituted"):
        initialize_database(db_path)

    assert attacked is True
    _assert_schema_six_without_commit_marker(db_path)


def test_commit_failure_classifies_old_schema_without_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)

    def fail_before_commit(_: sqlite3.Connection) -> None:
        raise sqlite3.OperationalError("simulated COMMIT failure")

    monkeypatch.setattr(migration_backup, "_commit_connection", fail_before_commit)
    with pytest.raises(DatabaseBackupError, match="did not commit"):
        initialize_database(db_path)

    _assert_schema_six_without_commit_marker(db_path)


def test_commit_then_error_classifies_exact_marker_and_requires_one_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    original_commit = migration_backup._commit_connection  # noqa: SLF001

    def commit_then_error(connection: sqlite3.Connection) -> None:
        original_commit(connection)
        raise sqlite3.OperationalError("simulated error after SQLite committed")

    monkeypatch.setattr(migration_backup, "_commit_connection", commit_then_error)
    with pytest.raises(DatabaseBackupRecoveryRequired, match="commit error"):
        initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
    assert metadata["schema_version"] == "7"
    assert PRE_V7_MARKER_KEY in metadata
    monkeypatch.setattr(migration_backup, "_commit_connection", original_commit)
    initialize_database(db_path)


def test_commit_outcome_outside_two_exact_states_is_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    original_commit = migration_backup._commit_connection  # noqa: SLF001

    def commit_then_remove_marker(connection: sqlite3.Connection) -> None:
        original_commit(connection)
        connection.execute(
            "DELETE FROM app_metadata WHERE key = ?",
            (PRE_V7_MARKER_KEY,),
        )
        raise sqlite3.OperationalError("simulated unclassifiable commit result")

    monkeypatch.setattr(
        migration_backup,
        "_commit_connection",
        commit_then_remove_marker,
    )
    with pytest.raises(DatabaseMigrationOutcomeUnknown, match="outcome is unknown"):
        initialize_database(db_path)


def test_postcommit_alias_substitution_repairs_then_fails_startup_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    backup_path, _ = pre_v7_backup_paths(db_path)
    original_hook = migration_backup._run_protocol_hook  # noqa: SLF001

    def remove_canonical_postcommit(stage: str, _: BackupGuard) -> None:
        if stage == "postcommit_pre_finalize":
            backup_path.unlink()

    monkeypatch.setattr(
        migration_backup,
        "_run_protocol_hook",
        remove_canonical_postcommit,
    )
    with pytest.raises(DatabaseBackupRecoveryRequired, match="interference was repaired"):
        initialize_database(db_path)

    _, _, backup_anchor, _ = _pre_v7_artifacts(db_path)
    assert backup_path.stat().st_ino == backup_anchor.stat().st_ino
    monkeypatch.setattr(migration_backup, "_run_protocol_hook", original_hook)
    initialize_database(db_path)


@pytest.mark.parametrize("removed_alias", ["canonical", "anchor"])
def test_committed_backup_one_alias_repair_requires_one_restart(
    tmp_path: Path,
    removed_alias: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    initialize_database(db_path)
    backup_path, _, backup_anchor, _ = _pre_v7_artifacts(db_path)

    (backup_path if removed_alias == "canonical" else backup_anchor).unlink()

    with pytest.raises(DatabaseBackupRecoveryRequired, match="aliases were repaired"):
        initialize_database(db_path)
    assert backup_path.stat().st_ino == backup_anchor.stat().st_ino
    initialize_database(db_path)


def test_committed_backup_distinct_canonical_is_repaired_from_exact_anchor(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    substituted_path = tmp_path / "distinct-schema-six.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    _create_distinct_schema_six_database(substituted_path, frozen)
    initialize_database(db_path)
    backup_path, _, backup_anchor, _ = _pre_v7_artifacts(db_path)

    substituted_path.replace(backup_path)

    with pytest.raises(DatabaseBackupRecoveryRequired, match="aliases were repaired"):
        initialize_database(db_path)
    assert backup_path.stat().st_ino == backup_anchor.stat().st_ino
    initialize_database(db_path)


def test_committed_backup_same_bytes_different_canonical_repairs_from_exact_anchor(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    initialize_database(db_path)
    backup_path, _, backup_anchor, _ = _pre_v7_artifacts(db_path)
    replacement = tmp_path / "same-backup-bytes-different-inode.sqlite3"
    shutil.copyfile(backup_path, replacement)
    replacement.chmod(0o600)
    replacement.replace(backup_path)
    assert backup_path.stat().st_ino != backup_anchor.stat().st_ino

    with pytest.raises(DatabaseBackupRecoveryRequired, match="aliases were repaired"):
        initialize_database(db_path)
    assert backup_path.stat().st_ino == backup_anchor.stat().st_ino
    initialize_database(db_path)


def test_committed_backup_same_bytes_new_inode_pair_cannot_claim_exact_continuity(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    initialize_database(db_path)
    backup_path, receipt_path, backup_anchor, _ = _pre_v7_artifacts(db_path)
    original_payload = backup_path.read_bytes()
    original_inode = backup_path.stat().st_ino
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    backup_path.unlink()
    backup_anchor.unlink()
    backup_path.write_bytes(original_payload)
    backup_path.chmod(0o600)
    os.link(backup_path, backup_anchor)
    assert backup_path.stat().st_ino != original_inode
    assert backup_path.stat().st_ino != receipt["backup_inode"]

    with pytest.raises(DatabaseBackupRecoveryRequired, match="no valid exact backup alias"):
        initialize_database(db_path)


def test_committed_receipt_anchor_symlink_is_repaired_once(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    initialize_database(db_path)
    _, receipt_path, _, receipt_anchor = _pre_v7_artifacts(db_path)
    receipt_anchor.unlink()
    receipt_anchor.symlink_to(receipt_path)

    with pytest.raises(DatabaseBackupRecoveryRequired, match="aliases were repaired"):
        initialize_database(db_path)
    assert not receipt_anchor.is_symlink()
    assert receipt_path.stat().st_ino == receipt_anchor.stat().st_ino
    initialize_database(db_path)


def test_marker_restores_invalid_receipt_projection_then_restart_succeeds(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    initialize_database(db_path)
    _, receipt_path, _, receipt_anchor = _pre_v7_artifacts(db_path)
    with sqlite3.connect(db_path) as connection:
        marker = str(
            connection.execute(
                "SELECT value FROM app_metadata WHERE key = ?",
                (PRE_V7_MARKER_KEY,),
            ).fetchone()[0]
        )

    receipt_path.write_bytes(b"{}\n")

    with pytest.raises(DatabaseBackupRecoveryRequired, match="aliases were repaired"):
        initialize_database(db_path)
    assert receipt_path.read_text(encoding="utf-8") == marker + "\n"
    assert receipt_path.stat().st_ino == receipt_anchor.stat().st_ino
    initialize_database(db_path)


def test_receipt_same_bytes_different_inode_is_reprojected_from_marker(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    initialize_database(db_path)
    _, receipt_path, _, receipt_anchor = _pre_v7_artifacts(db_path)
    replacement = tmp_path / "receipt-same-bytes-different-inode.json"
    shutil.copyfile(receipt_path, replacement)
    replacement.chmod(0o600)
    replacement.replace(receipt_anchor)
    assert receipt_path.stat().st_ino != receipt_anchor.stat().st_ino

    with pytest.raises(DatabaseBackupRecoveryRequired, match="aliases were repaired"):
        initialize_database(db_path)
    assert receipt_path.stat().st_ino == receipt_anchor.stat().st_ino
    initialize_database(db_path)


@pytest.mark.parametrize("attack", ["missing", "in_place_mutation"])
def test_committed_backup_without_valid_exact_alias_requires_recovery(
    tmp_path: Path,
    attack: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    initialize_database(db_path)
    backup_path, _, backup_anchor, _ = _pre_v7_artifacts(db_path)
    if attack == "missing":
        backup_path.unlink()
        backup_anchor.unlink()
    else:
        backup_path.write_bytes(b"not a SQLite backup")

    with pytest.raises(DatabaseBackupRecoveryRequired, match="no valid exact backup alias"):
        initialize_database(db_path)


def test_marker_receipt_mismatch_requires_recovery(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        marker = json.loads(
            str(
                connection.execute(
                    "SELECT value FROM app_metadata WHERE key = ?",
                    (PRE_V7_MARKER_KEY,),
                ).fetchone()[0]
            )
        )
        marker["source_schema_version"] = "5"
        connection.execute(
            "UPDATE app_metadata SET value = ? WHERE key = ?",
            (canonical_json(marker), PRE_V7_MARKER_KEY),
        )
        connection.commit()

    with pytest.raises(DatabaseBackupRecoveryRequired, match="marker does not match"):
        initialize_database(db_path)


def test_target_schema_without_marker_rejects_legacy_repair3_artifacts(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    repair3 = _load_migration_at_commit(
        tmp_path,
        commit=REPAIR3_COMMIT,
        module_name="ithildin_frozen_repair3_target_migration",
    )
    repair3.initialize_or_migrate_database(db_path)
    backup_path, receipt_path = pre_v7_backup_paths(db_path)
    assert backup_path.is_file()
    assert receipt_path.is_file()
    assert backup_path.stat().st_nlink == 1
    assert receipt_path.stat().st_nlink == 1
    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
    assert metadata["schema_version"] == "7"
    assert PRE_V7_MARKER_KEY not in metadata

    with pytest.raises(DatabaseMigrationOutcomeUnknown, match="legacy migration backup artifacts"):
        initialize_database(db_path)


def test_old_schema_with_marker_fails_closed(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "INSERT INTO app_metadata (key, value) VALUES (?, '{}')",
            (PRE_V7_MARKER_KEY,),
        )
        connection.commit()

    with pytest.raises(DatabaseBackupError, match="old database schema contains"):
        initialize_database(db_path)


@pytest.mark.parametrize("legacy_state", ["pair", "backup_only"])
def test_schema_six_repair3_prepared_artifacts_are_adopted_after_fd_verification(
    tmp_path: Path,
    legacy_state: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    repair3 = _load_migration_at_commit(
        tmp_path,
        commit=REPAIR3_COMMIT,
        module_name="ithildin_frozen_repair3_migration",
    )

    def stop_after_prepare(_: sqlite3.Connection) -> None:
        raise sqlite3.OperationalError("prepared repair-3 fixture")

    repair3_impl: Any = repair3
    repair3_impl._create_pis005a_tables = stop_after_prepare
    with pytest.raises(sqlite3.OperationalError, match="repair-3 fixture"):
        repair3_impl.initialize_or_migrate_database(db_path)
    backup_path, receipt_path = pre_v7_backup_paths(db_path)
    legacy_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert legacy_receipt["receipt_version"] == "1"
    assert "backup_device" not in legacy_receipt
    assert "backup_inode" not in legacy_receipt
    if legacy_state == "backup_only":
        receipt_path.unlink()
    assert backup_path.stat().st_nlink == 1

    initialize_database(db_path)
    backup_path, receipt_path, backup_anchor, receipt_anchor = _pre_v7_artifacts(db_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["receipt_version"] == "2"
    assert receipt["backup_device"] == backup_path.stat().st_dev
    assert receipt["backup_inode"] == backup_path.stat().st_ino
    assert backup_path.stat().st_ino == backup_anchor.stat().st_ino
    assert receipt_path.stat().st_ino == receipt_anchor.stat().st_ino


def test_prepared_backup_and_receipt_from_different_snapshots_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_directory = tmp_path / "first"
    second_directory = tmp_path / "second"
    first_directory.mkdir()
    second_directory.mkdir()
    first_db = first_directory / "ithildin.sqlite3"
    second_db = second_directory / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(first_db)
    _create_distinct_schema_six_database(second_db, frozen)
    original_create_tables = migration._create_pis005a_tables

    def stop_after_prepare(_: sqlite3.Connection) -> None:
        raise sqlite3.OperationalError("prepared snapshot fixture")

    monkeypatch.setattr(migration, "_create_pis005a_tables", stop_after_prepare)
    for db_path in (first_db, second_db):
        with pytest.raises(sqlite3.OperationalError, match="prepared snapshot fixture"):
            initialize_database(db_path)

    _, first_receipt, _, first_receipt_anchor = _pre_v7_artifacts(first_db)
    _, second_receipt, _, _ = _pre_v7_artifacts(second_db)
    second_receipt_bytes = second_receipt.read_bytes()
    second_receipt_sha256 = migration_backup._bytes_digest(  # noqa: SLF001
        second_receipt_bytes
    )
    replacement_anchor = content_addressed_anchor_path(
        first_receipt,
        second_receipt_sha256,
    )
    first_receipt.unlink()
    first_receipt_anchor.unlink()
    shutil.copyfile(second_receipt, first_receipt)
    first_receipt.chmod(0o600)
    os.link(first_receipt, replacement_anchor)

    monkeypatch.setattr(migration, "_create_pis005a_tables", original_create_tables)
    with pytest.raises(
        DatabaseBackupError,
        match="(source_logical_sha256|backup_sha256) mismatch",
    ):
        initialize_database(first_db)
    _assert_schema_six_without_commit_marker(first_db)


@pytest.mark.parametrize("hidden_kind", ["temporary", "competing_anchor"])
def test_precreated_hidden_backup_names_fail_closed(
    tmp_path: Path,
    hidden_kind: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    backup_path, _ = pre_v7_backup_paths(db_path)
    suffix = "attacker.tmp" if hidden_kind == "temporary" else f"sha256-{'0' * 64}"
    hidden_path = tmp_path / f".{backup_path.name}.{suffix}"
    hidden_path.write_bytes(b"attacker")
    hidden_path.chmod(0o600)

    with pytest.raises(DatabaseBackupError, match="unexpected temporary or anchor"):
        initialize_database(db_path)


def test_committed_competing_anchor_fails_recovery_closed(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    initialize_database(db_path)
    backup_path, _ = pre_v7_backup_paths(db_path)
    competing = tmp_path / f".{backup_path.name}.sha256-{'0' * 64}"
    competing.write_bytes(b"competing")
    competing.chmod(0o600)

    with pytest.raises(DatabaseBackupRecoveryRequired, match="competing anchor"):
        initialize_database(db_path)


@pytest.mark.parametrize("failure", ["permissions", "link_count"])
def test_committed_backup_permission_and_link_count_failures_require_recovery(
    tmp_path: Path,
    failure: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    initialize_database(db_path)
    backup_path, _, _, _ = _pre_v7_artifacts(db_path)
    if failure == "permissions":
        backup_path.chmod(0o640)
    else:
        os.link(backup_path, tmp_path / "unexpected-extra-backup-link.sqlite3")

    with pytest.raises(DatabaseBackupRecoveryRequired):
        initialize_database(db_path)


def test_group_writable_database_directory_fails_closed(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    original_mode = stat.S_IMODE(tmp_path.stat().st_mode)
    tmp_path.chmod(original_mode | 0o020)
    try:
        with pytest.raises(DatabaseBackupError, match="group or world writable"):
            initialize_database(db_path)
    finally:
        tmp_path.chmod(original_mode)


def test_database_directory_symlink_fails_no_follow_validation(tmp_path: Path) -> None:
    real_directory = tmp_path / "real"
    real_directory.mkdir(mode=0o700)
    linked_directory = tmp_path / "linked"
    linked_directory.symlink_to(real_directory, target_is_directory=True)
    real_db_path = real_directory / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(real_db_path)

    with pytest.raises(DatabaseBackupError, match="opened safely"):
        initialize_database(linked_directory / real_db_path.name)


def test_artifact_owner_mismatch_validation_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    initialize_database(db_path)
    backup_path, _, _, _ = _pre_v7_artifacts(db_path)
    descriptor = os.open(backup_path, os.O_RDONLY)
    try:
        monkeypatch.setattr(
            os,
            "geteuid",
            lambda: os.fstat(descriptor).st_uid + 1,
        )
        with pytest.raises(DatabaseBackupError, match="owner is invalid"):
            migration_backup._require_private_regular_descriptor(  # noqa: SLF001
                descriptor,
                exact_link_count=2,
            )
    finally:
        os.close(descriptor)


def test_unsupported_no_follow_semantics_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)

    def unsupported() -> None:
        raise DatabaseBackupError("required no-follow descriptor semantics are unsupported")

    monkeypatch.setattr(migration_backup, "_require_platform_support", unsupported)
    with pytest.raises(DatabaseBackupError, match="no-follow"):
        initialize_database(db_path)


@pytest.mark.parametrize(
    ("crash_stage", "expected_exit", "expected_schema"),
    [
        ("prepared_before_return", 73, "6"),
        ("postcommit_pre_finalize", 74, "7"),
    ],
)
def test_child_process_crash_schedules_restart_into_exact_state(
    tmp_path: Path,
    crash_stage: str,
    expected_exit: int,
    expected_schema: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    script = """
import os
import sys
from pathlib import Path
import ithildin_api.database_migration_backup as backup
from ithildin_api.database import initialize_database

stage = sys.argv[2]
exit_code = int(sys.argv[3])

def crash(observed_stage, guard):
    del guard
    if observed_stage == stage:
        os._exit(exit_code)

backup._run_protocol_hook = crash
initialize_database(Path(sys.argv[1]))
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            crash_stage,
            str(expected_exit),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == expected_exit, result.stderr
    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
    assert metadata["schema_version"] == expected_schema
    assert (PRE_V7_MARKER_KEY in metadata) is (expected_schema == "7")

    initialize_database(db_path)


@pytest.mark.parametrize(
    ("crash_stage", "partial_state"),
    [
        ("temporary_fsynced", "temporary_only"),
        ("canonical_published", "canonical_and_temporary"),
        ("anchor_published", "canonical_anchor_and_temporary"),
        ("anchor_published", "anchor_and_temporary"),
    ],
)
def test_child_process_partial_publication_crash_is_recoverable(
    tmp_path: Path,
    crash_stage: str,
    partial_state: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    backup_path, _ = pre_v7_backup_paths(db_path)
    script = """
import os
import sys
from pathlib import Path
import ithildin_api.database_migration_backup as backup
from ithildin_api.database import initialize_database

stage = sys.argv[2]
artifact_name = sys.argv[3]

def crash(observed_stage, observed_artifact):
    if observed_stage == stage and observed_artifact == artifact_name:
        os._exit(75)

backup._run_raw_protocol_hook = crash
initialize_database(Path(sys.argv[1]))
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db_path),
            crash_stage,
            backup_path.name,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 75, result.stderr
    _assert_schema_six_without_commit_marker(db_path)
    temporary_paths = _publication_temporary_paths(backup_path)
    assert len(temporary_paths) == 1
    temporary_path = temporary_paths[0]
    anchor_path = content_addressed_anchor_path(
        backup_path,
        migration_backup._bytes_digest(temporary_path.read_bytes()),  # noqa: SLF001
    )
    if partial_state == "anchor_and_temporary":
        backup_path.unlink()
    expected_aliases = {
        "temporary_only": (False, False),
        "canonical_and_temporary": (True, False),
        "canonical_anchor_and_temporary": (True, True),
        "anchor_and_temporary": (False, True),
    }
    canonical_expected, anchor_expected = expected_aliases[partial_state]
    assert backup_path.exists() is canonical_expected
    assert anchor_path.exists() is anchor_expected
    for alias in (backup_path, anchor_path):
        if alias.exists():
            assert alias.stat().st_ino == temporary_path.stat().st_ino

    initialize_database(db_path)

    backup_path, receipt_path, backup_anchor, _ = _pre_v7_artifacts(db_path)
    assert backup_path.stat().st_ino == backup_anchor.stat().st_ino
    assert _publication_temporary_paths(backup_path) == []
    _assert_schema_seven_with_exact_marker(db_path, receipt_path)


def test_committed_exact_marker_repairs_partial_receipt_publication_then_restarts(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    initialize_database(db_path)
    _, receipt_path, _, receipt_anchor = _pre_v7_artifacts(db_path)
    receipt_payload = receipt_path.read_bytes()
    exact_marker = receipt_payload.decode().rstrip("\n")
    receipt_path.unlink()
    receipt_anchor.unlink()
    temporary_path = tmp_path / f".{receipt_path.name}.{'a' * 32}.tmp"
    temporary_path.write_bytes(receipt_payload)
    temporary_path.chmod(0o600)
    os.link(temporary_path, receipt_path)

    with pytest.raises(DatabaseBackupRecoveryRequired, match="aliases were repaired"):
        initialize_database(db_path)

    assert receipt_path.stat().st_ino == receipt_anchor.stat().st_ino
    assert not temporary_path.exists()
    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
    assert metadata["schema_version"] == "7"
    assert metadata[PRE_V7_MARKER_KEY] == exact_marker
    initialize_database(db_path)


def test_post_finalization_same_uid_mutation_is_detected_on_next_restart(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    frozen = _load_schema_six_migration(tmp_path)
    frozen.initialize_or_migrate_database(db_path)
    initialize_database(db_path)
    backup_path, _, _, _ = _pre_v7_artifacts(db_path)

    backup_path.write_bytes(b"post-finalization same-UID mutation")

    with pytest.raises(DatabaseBackupRecoveryRequired):
        initialize_database(db_path)


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
    return _load_migration_at_commit(
        tmp_path,
        commit=SCHEMA_SIX_COMMIT,
        module_name="ithildin_frozen_schema_six_migration",
    )


def _load_migration_at_commit(
    tmp_path: Path,
    *,
    commit: str,
    module_name: str,
) -> ModuleType:
    source = subprocess.run(
        [
            "git",
            "show",
            f"{commit}:apps/api/src/ithildin_api/trusted_host_promotion_v2_migration.py",
        ],
        check=True,
        capture_output=True,
    ).stdout
    backup_source = subprocess.run(
        [
            "git",
            "show",
            f"{commit}:apps/api/src/ithildin_api/database_migration_backup.py",
        ],
        check=True,
        capture_output=True,
    ).stdout
    backup_module_path = tmp_path / f"{module_name}_database_migration_backup.py"
    backup_module_path.write_bytes(backup_source)
    backup_spec = importlib.util.spec_from_file_location(
        f"{module_name}_database_migration_backup",
        backup_module_path,
    )
    assert backup_spec is not None and backup_spec.loader is not None
    backup_module = importlib.util.module_from_spec(backup_spec)
    sys.modules[backup_spec.name] = backup_module
    try:
        backup_spec.loader.exec_module(backup_module)
    finally:
        sys.modules.pop(backup_spec.name, None)

    module_path = tmp_path / f"{module_name}.py"
    module_path.write_bytes(source)
    spec = importlib.util.spec_from_file_location(
        module_name,
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    current_backup_module = sys.modules["ithildin_api.database_migration_backup"]
    sys.modules["ithildin_api.database_migration_backup"] = backup_module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules["ithildin_api.database_migration_backup"] = current_backup_module
        sys.modules.pop(spec.name, None)
    return module


def _pre_v7_artifacts(db_path: Path) -> tuple[Path, Path, Path, Path]:
    backup_path, receipt_path = pre_v7_backup_paths(db_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    backup_anchor = content_addressed_anchor_path(
        backup_path,
        str(receipt["backup_sha256"]),
    )
    receipt_anchor = content_addressed_anchor_path(
        receipt_path,
        migration_backup._bytes_digest(receipt_path.read_bytes()),  # noqa: SLF001
    )
    return backup_path, receipt_path, backup_anchor, receipt_anchor


def _leave_partial_backup_publication(
    db_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path]:
    backup_path, _ = pre_v7_backup_paths(db_path)
    original_hook = migration_backup._run_raw_protocol_hook  # noqa: SLF001

    def interrupt_after_canonical(stage: str, artifact_name: str) -> None:
        if stage == "canonical_published" and artifact_name == backup_path.name:
            raise DatabaseBackupError("leave exact interrupted publication")

    monkeypatch.setattr(
        migration_backup,
        "_run_raw_protocol_hook",
        interrupt_after_canonical,
    )
    with pytest.raises(DatabaseBackupError, match="leave exact interrupted publication"):
        initialize_database(db_path)
    monkeypatch.setattr(
        migration_backup,
        "_run_raw_protocol_hook",
        original_hook,
    )
    temporary_paths = _publication_temporary_paths(backup_path)
    assert len(temporary_paths) == 1
    temporary_path = temporary_paths[0]
    anchor_path = content_addressed_anchor_path(
        backup_path,
        migration_backup._bytes_digest(temporary_path.read_bytes()),  # noqa: SLF001
    )
    assert backup_path.stat().st_ino == temporary_path.stat().st_ino
    assert not anchor_path.exists()
    _assert_schema_six_without_commit_marker(db_path)
    return backup_path, temporary_path, anchor_path


def _publication_temporary_paths(canonical_path: Path) -> list[Path]:
    prefix = f".{canonical_path.name}."
    suffix = ".tmp"
    return sorted(
        candidate
        for candidate in canonical_path.parent.iterdir()
        if candidate.name.startswith(prefix)
        and candidate.name.endswith(suffix)
        and len(candidate.name[len(prefix) : -len(suffix)]) == 32
    )


def _assert_schema_seven_with_exact_marker(
    db_path: Path,
    receipt_path: Path,
) -> None:
    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
    assert metadata["schema_version"] == "7"
    assert metadata["minimum_writer_version"] == "7"
    assert metadata[PRE_V7_MARKER_KEY] == receipt_path.read_text(encoding="utf-8").rstrip("\n")


def _create_distinct_schema_six_database(path: Path, frozen: ModuleType) -> None:
    frozen.initialize_or_migrate_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO identity_organizations (
                organization_id, enabled, created_at, updated_at
            ) VALUES (?, 1, ?, ?)
            """,
            (
                "org_00000000000000000000000000000001",
                "2026-07-30T12:00:00+00:00",
                "2026-07-30T12:00:00+00:00",
            ),
        )
        connection.commit()
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def _assert_schema_six_without_commit_marker(db_path: Path) -> None:
    with sqlite3.connect(db_path) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))
        assert metadata["schema_version"] == "6"
        assert metadata["minimum_writer_version"] == "6"
        assert PRE_V7_MARKER_KEY not in metadata
        assert connection.execute(
            """
            SELECT count(*) FROM sqlite_master
            WHERE lower(name) GLOB 'node_workload_*'
               OR lower(tbl_name) GLOB 'node_workload_*'
            """
        ).fetchone() == (0,)

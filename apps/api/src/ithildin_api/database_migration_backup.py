"""Descriptor-bound SQLite migration backup preparation and commit finalization."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from ithildin_schemas import JsonObject, canonical_json

BACKUP_RECEIPT_VERSION = "2"
_LEGACY_BACKUP_RECEIPT_VERSION = "1"
TARGET_SCHEMA_VERSION = "4"
PIS005A_TARGET_SCHEMA_VERSION = "7"
PRE_V4_MARKER_KEY = "migration_backup_receipt_pre_v4_v1"
PRE_V7_MARKER_KEY = "migration_backup_receipt_pre_v7_v1"
_MARKER_KEYS = (PRE_V4_MARKER_KEY, PRE_V7_MARKER_KEY)
_SHA256_PREFIX = "sha256:"


class DatabaseBackupError(RuntimeError):
    """Raised when migration has not committed and its backup protocol fails."""


class DatabaseMigrationOutcomeUnknown(RuntimeError):
    """Raised when SQLite commit outcome cannot be classified exactly."""


class DatabaseBackupRecoveryRequired(RuntimeError):
    """Raised after commit when backup publication could not finalize normally."""


@dataclass(frozen=True)
class _BackupFamily:
    marker_key: str
    target_schema_version: str
    supported_source_versions: frozenset[str]
    backup_path: Path
    receipt_path: Path


@dataclass
class BackupGuard:
    """Own stable backup evidence until commit and namespace finalization finish."""

    db_path: Path
    directory_path: Path
    directory_fd: int
    directory_device: int
    directory_inode: int
    database_device: int
    database_inode: int
    backup_fd: int
    receipt_fd: int
    backup_name: str
    backup_anchor_name: str
    receipt_name: str
    receipt_anchor_name: str
    backup_physical_sha256: str
    backup_logical_sha256: str
    receipt_physical_sha256: str
    backup_device: int
    backup_inode: int
    receipt_device: int
    receipt_inode: int
    receipt: JsonObject
    receipt_json: str
    marker_key: str
    source_schema_version: str
    protocol_state: str = "prepared"
    commit_outcome: str = "not_attempted"
    _closed: bool = False

    def mark_migrating(self) -> None:
        """Record the point after preparation and before schema mutation."""

        if self.protocol_state != "prepared":
            raise DatabaseBackupError("migration backup guard state is invalid before migration")
        self._verify_precommit(None)
        self.protocol_state = "migrating"
        _run_protocol_hook("guard_marked_migrating", self)

    def bind_commit_marker(self, connection: sqlite3.Connection) -> None:
        """Bind the exact receipt JSON inside the caller-owned migration transaction."""

        if self.protocol_state != "migrating" or not connection.in_transaction:
            raise DatabaseBackupError("migration backup marker binding is out of protocol order")
        try:
            connection.execute(
                "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
                (self.marker_key, self.receipt_json),
            )
        except sqlite3.DatabaseError as exc:
            raise DatabaseBackupError(
                "migration backup commit marker could not be bound without overwrite"
            ) from exc
        if _metadata_value(connection, self.marker_key) != self.receipt_json:
            raise DatabaseBackupError("migration backup commit marker does not match the receipt")
        self.protocol_state = "marker_bound"
        _run_protocol_hook("marker_bound", self)

    def commit_transaction(self, connection: sqlite3.Connection) -> None:
        """Verify, commit, classify, repair bounded aliases, and finalize durability."""

        if self.protocol_state != "marker_bound" or not connection.in_transaction:
            raise DatabaseBackupError("migration backup guard cannot commit out of protocol order")
        self._verify_precommit(connection)
        _run_protocol_hook("after_precommit_check_before_commit", self)
        self._verify_precommit(connection)
        self.protocol_state = "committing"
        commit_error: sqlite3.DatabaseError | None = None
        try:
            _commit_connection(connection)
        except sqlite3.DatabaseError as exc:
            outcome = self._classify_failed_commit(connection)
            if outcome == "not_committed":
                self.commit_outcome = outcome
                self.protocol_state = "prepared"
                raise DatabaseBackupError(
                    "migration transaction did not commit; prepared backup artifacts were retained"
                ) from exc
            if outcome != "committed":
                self.commit_outcome = "unknown"
                self.protocol_state = "outcome_unknown"
                raise DatabaseMigrationOutcomeUnknown(
                    "migration transaction outcome is unknown"
                ) from exc
            commit_error = exc
        else:
            if not self._connection_has_exact_committed_marker(connection):
                self.commit_outcome = "unknown"
                self.protocol_state = "outcome_unknown"
                raise DatabaseMigrationOutcomeUnknown(
                    "migration commit returned without the exact committed backup marker"
                )

        self.commit_outcome = "committed"
        self.protocol_state = "committed"
        try:
            _run_protocol_hook("postcommit_pre_finalize", self)
            repaired = self._finalize_committed_namespace()
        except DatabaseBackupRecoveryRequired:
            self.commit_outcome = "committed_recovery_required"
            self.protocol_state = "recovery_required"
            raise
        except Exception as exc:
            self.commit_outcome = "committed_recovery_required"
            self.protocol_state = "recovery_required"
            raise DatabaseBackupRecoveryRequired(
                "migration committed but backup finalization requires recovery"
            ) from exc
        if repaired or commit_error is not None:
            self.commit_outcome = "committed_recovery_required"
            self.protocol_state = "recovery_required"
            detail = (
                "migration committed and backup alias interference was repaired; "
                "restart verification is required"
                if repaired
                else "migration committed despite a commit error; restart verification is required"
            )
            raise DatabaseBackupRecoveryRequired(detail) from commit_error
        self.protocol_state = "finalized"

    def verify_committed_restart(self, connection: sqlite3.Connection) -> None:
        """Hold descriptors through target-schema verification and end the read transaction."""

        if self.protocol_state != "committed_restart" or not connection.in_transaction:
            raise DatabaseBackupRecoveryRequired(
                "committed migration backup restart verification is out of protocol order"
            )
        try:
            self._verify_precommit(connection)
        except DatabaseBackupError as exc:
            self.commit_outcome = "committed_recovery_required"
            self.protocol_state = "recovery_required"
            raise DatabaseBackupRecoveryRequired(
                "committed migration backup restart verification requires recovery"
            ) from exc
        connection.execute("ROLLBACK")
        try:
            repaired = self._finalize_committed_namespace()
        except (DatabaseBackupRecoveryRequired, DatabaseBackupError) as exc:
            self.commit_outcome = "committed_recovery_required"
            self.protocol_state = "recovery_required"
            if isinstance(exc, DatabaseBackupRecoveryRequired):
                raise
            raise DatabaseBackupRecoveryRequired(
                "committed migration backup finalization requires recovery"
            ) from exc
        if repaired:
            self.commit_outcome = "committed_recovery_required"
            self.protocol_state = "recovery_required"
            raise DatabaseBackupRecoveryRequired(
                "committed migration backup aliases were repaired; restart verification is required"
            )
        self.commit_outcome = "committed"
        self.protocol_state = "finalized"

    def close(self) -> None:
        """Close all descriptors after commit finalization or error classification."""

        if self._closed:
            return
        self._closed = True
        for descriptor in (self.receipt_fd, self.backup_fd, self.directory_fd):
            if descriptor < 0:
                continue
            try:
                os.close(descriptor)
            except OSError:
                pass

    def _verify_precommit(self, connection: sqlite3.Connection | None) -> None:
        _require_directory_identity(
            self.directory_path,
            self.directory_fd,
            self.directory_device,
            self.directory_inode,
        )
        _require_database_path_identity(
            self.directory_fd,
            self.db_path.name,
            self.database_device,
            self.database_inode,
        )
        backup_payload = _verify_descriptor(
            self.backup_fd,
            expected_device=self.backup_device,
            expected_inode=self.backup_inode,
            expected_sha256=self.backup_physical_sha256,
            expected_logical_sha256=self.backup_logical_sha256,
            label="backup",
            exact_link_count=2,
        )
        _require_backup_version_metadata(
            backup_payload,
            source_schema_version=str(self.receipt["source_schema_version"]),
            source_minimum_writer_version=cast(
                str | None, self.receipt["source_minimum_writer_version"]
            ),
        )
        _require_alias_pair(
            self.directory_fd,
            self.backup_name,
            self.backup_anchor_name,
            self.backup_device,
            self.backup_inode,
        )
        receipt_payload = _verify_descriptor(
            self.receipt_fd,
            expected_device=self.receipt_device,
            expected_inode=self.receipt_inode,
            expected_sha256=self.receipt_physical_sha256,
            expected_logical_sha256=None,
            label="receipt",
            exact_link_count=2,
        )
        if receipt_payload != _receipt_payload(self.receipt):
            raise DatabaseBackupError("migration backup receipt descriptor bytes changed")
        parsed = _parse_receipt_payload(receipt_payload)
        _validate_receipt(
            parsed,
            backup_name=self.backup_name,
            backup_sha256=self.backup_physical_sha256,
            backup_device=self.backup_device,
            backup_inode=self.backup_inode,
            source_schema_version=str(self.receipt["source_schema_version"]),
            source_minimum_writer_version=cast(
                str | None, self.receipt["source_minimum_writer_version"]
            ),
            source_logical_digest=self.backup_logical_sha256,
            target_schema_version=str(self.receipt["migration_target_schema_version"]),
        )
        if canonical_json(parsed) != self.receipt_json:
            raise DatabaseBackupError("migration backup receipt canonical JSON changed")
        _require_alias_pair(
            self.directory_fd,
            self.receipt_name,
            self.receipt_anchor_name,
            self.receipt_device,
            self.receipt_inode,
        )
        _require_no_competing_names(
            self.directory_fd,
            self.backup_name,
            self.backup_anchor_name,
        )
        _require_no_competing_names(
            self.directory_fd,
            self.receipt_name,
            self.receipt_anchor_name,
        )
        if (
            connection is not None
            and _metadata_value(connection, self.marker_key) != self.receipt_json
        ):
            raise DatabaseBackupError("migration backup commit marker differs from the receipt")

    def _classify_failed_commit(self, connection: sqlite3.Connection) -> str:
        if connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.DatabaseError:
                return "unknown"
        try:
            current = _metadata_value(connection, "schema_version")
            marker = _metadata_value(connection, self.marker_key)
            other_markers = [
                _metadata_value(connection, key) for key in _MARKER_KEYS if key != self.marker_key
            ]
        except sqlite3.DatabaseError:
            return "unknown"
        if (
            current == self.source_schema_version
            and marker is None
            and all(value is None for value in other_markers)
        ):
            return "not_committed"
        if current == PIS005A_TARGET_SCHEMA_VERSION and marker == self.receipt_json:
            return "committed"
        return "unknown"

    def _connection_has_exact_committed_marker(self, connection: sqlite3.Connection) -> bool:
        try:
            return (
                not connection.in_transaction
                and _metadata_value(connection, "schema_version") == PIS005A_TARGET_SCHEMA_VERSION
                and _metadata_value(connection, self.marker_key) == self.receipt_json
            )
        except sqlite3.DatabaseError:
            return False

    def _finalize_committed_namespace(self) -> bool:
        _require_directory_identity(
            self.directory_path,
            self.directory_fd,
            self.directory_device,
            self.directory_inode,
        )
        try:
            _require_database_path_identity(
                self.directory_fd,
                self.db_path.name,
                self.database_device,
                self.database_inode,
            )
        except DatabaseBackupError as exc:
            raise DatabaseBackupRecoveryRequired(
                "committed database pathname no longer names the migrated database object"
            ) from exc
        try:
            _verify_descriptor(
                self.backup_fd,
                expected_device=self.backup_device,
                expected_inode=self.backup_inode,
                expected_sha256=self.backup_physical_sha256,
                expected_logical_sha256=self.backup_logical_sha256,
                label="backup",
                exact_link_count=None,
            )
        except DatabaseBackupError as exc:
            raise DatabaseBackupRecoveryRequired(
                "committed migration backup object changed in place"
            ) from exc
        _require_no_competing_names(
            self.directory_fd,
            self.backup_name,
            self.backup_anchor_name,
            committed=True,
        )
        repaired = _repair_held_alias_pair(
            self.directory_fd,
            self.backup_fd,
            self.backup_name,
            self.backup_anchor_name,
            self.backup_device,
            self.backup_inode,
            label="backup",
        )

        receipt_payload_valid = True
        try:
            payload = _verify_descriptor(
                self.receipt_fd,
                expected_device=self.receipt_device,
                expected_inode=self.receipt_inode,
                expected_sha256=self.receipt_physical_sha256,
                expected_logical_sha256=None,
                label="receipt",
                exact_link_count=None,
            )
            receipt_payload_valid = payload == _receipt_payload(self.receipt)
        except DatabaseBackupError:
            receipt_payload_valid = False
        _require_no_competing_names(
            self.directory_fd,
            self.receipt_name,
            self.receipt_anchor_name,
            committed=True,
        )
        if receipt_payload_valid:
            repaired = (
                _repair_held_alias_pair(
                    self.directory_fd,
                    self.receipt_fd,
                    self.receipt_name,
                    self.receipt_anchor_name,
                    self.receipt_device,
                    self.receipt_inode,
                    label="receipt",
                )
                or repaired
            )
        else:
            self._replace_receipt_projection()
            repaired = True

        _fsync_directory_fd(self.directory_fd)
        _run_protocol_hook("postcommit_namespace_fsynced", self)
        self._verify_final_aliases()
        return repaired

    def _replace_receipt_projection(self) -> None:
        old_status = os.fstat(self.receipt_fd)
        if old_status.st_nlink > 2:
            raise DatabaseBackupRecoveryRequired(
                "committed migration receipt has an unexpected hardlink count"
            )
        for name in (self.receipt_name, self.receipt_anchor_name):
            _unlink_alias_for_repair(self.directory_fd, name)
        os.close(self.receipt_fd)
        self.receipt_fd = -1
        descriptor, status, _ = _publish_new_payload(
            self.directory_fd,
            self.receipt_name,
            _receipt_payload(self.receipt),
            logical_sha256=None,
        )
        self.receipt_fd = descriptor
        self.receipt_device = status.st_dev
        self.receipt_inode = status.st_ino
        self.receipt_physical_sha256 = _bytes_digest(_receipt_payload(self.receipt))
        self.receipt_anchor_name = _anchor_name(self.receipt_name, self.receipt_physical_sha256)

    def _verify_final_aliases(self) -> None:
        try:
            self._verify_final_aliases_unclassified()
        except DatabaseBackupRecoveryRequired:
            raise
        except DatabaseBackupError as exc:
            raise DatabaseBackupRecoveryRequired(
                "committed migration backup final verification requires recovery"
            ) from exc

    def _verify_final_aliases_unclassified(self) -> None:
        try:
            _require_database_path_identity(
                self.directory_fd,
                self.db_path.name,
                self.database_device,
                self.database_inode,
            )
        except DatabaseBackupError as exc:
            raise DatabaseBackupRecoveryRequired(
                "committed database pathname identity changed during finalization"
            ) from exc
        _verify_descriptor(
            self.backup_fd,
            expected_device=self.backup_device,
            expected_inode=self.backup_inode,
            expected_sha256=self.backup_physical_sha256,
            expected_logical_sha256=self.backup_logical_sha256,
            label="backup",
            exact_link_count=2,
        )
        _require_alias_pair(
            self.directory_fd,
            self.backup_name,
            self.backup_anchor_name,
            self.backup_device,
            self.backup_inode,
        )
        payload = _verify_descriptor(
            self.receipt_fd,
            expected_device=self.receipt_device,
            expected_inode=self.receipt_inode,
            expected_sha256=self.receipt_physical_sha256,
            expected_logical_sha256=None,
            label="receipt",
            exact_link_count=2,
        )
        if payload != _receipt_payload(self.receipt):
            raise DatabaseBackupRecoveryRequired(
                "committed migration receipt projection is not exact"
            )
        _require_alias_pair(
            self.directory_fd,
            self.receipt_name,
            self.receipt_anchor_name,
            self.receipt_device,
            self.receipt_inode,
        )


def prepare_pre_v4_backup_guard(
    *,
    locked_source: sqlite3.Connection,
    db_path: Path,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    now: datetime | None = None,
) -> BackupGuard:
    """Prepare a caller-owned guard for the shared pre-v4 migration backup."""

    return _prepare_guard(
        locked_source=locked_source,
        db_path=db_path,
        source_schema_version=source_schema_version,
        source_minimum_writer_version=source_minimum_writer_version,
        family=_family_pre_v4(db_path),
        now=now,
    )


def prepare_pre_v7_backup_guard(
    *,
    locked_source: sqlite3.Connection,
    db_path: Path,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    now: datetime | None = None,
) -> BackupGuard:
    """Prepare a caller-owned guard for the PIS-005A pre-v7 migration backup."""

    return _prepare_guard(
        locked_source=locked_source,
        db_path=db_path,
        source_schema_version=source_schema_version,
        source_minimum_writer_version=source_minimum_writer_version,
        family=_family_pre_v7(db_path),
        now=now,
    )


def prepare_committed_backup_guard(
    *,
    locked_source: sqlite3.Connection,
    db_path: Path,
) -> BackupGuard | None:
    """Classify and verify native or migrated schema-7 restart state."""

    if not locked_source.in_transaction:
        raise DatabaseBackupRecoveryRequired(
            "committed migration backup verification requires a locked transaction"
        )
    markers: dict[str, str] = {}
    for key in _MARKER_KEYS:
        value = _metadata_value(locked_source, key)
        if value is not None:
            markers[key] = value
    try:
        directory_fd, directory_status = _open_trusted_directory(db_path.parent)
    except DatabaseBackupError as exc:
        if markers:
            raise DatabaseBackupRecoveryRequired(
                "committed migration database directory is not trusted"
            ) from exc
        raise
    try:
        if not markers:
            if _any_backup_artifacts(directory_fd, db_path):
                raise DatabaseMigrationOutcomeUnknown(
                    "target schema has legacy migration backup artifacts but no commit marker"
                )
            os.close(directory_fd)
            return None
        if len(markers) != 1:
            raise DatabaseBackupRecoveryRequired(
                "target schema has conflicting migration backup commit markers"
            )
        marker_key, marker_json_value = next(iter(markers.items()))
        assert marker_json_value is not None
        family = (
            _family_pre_v4(db_path) if marker_key == PRE_V4_MARKER_KEY else _family_pre_v7(db_path)
        )
        receipt = _parse_marker_json(marker_json_value)
        guard, repaired = _guard_from_committed_marker(
            db_path=db_path,
            directory_fd=directory_fd,
            directory_status=directory_status,
            family=family,
            receipt=receipt,
            receipt_json=marker_json_value,
        )
        if repaired:
            guard.close()
            directory_fd = -1
            raise DatabaseBackupRecoveryRequired(
                "committed migration backup aliases were repaired; restart verification is required"
            )
        guard.protocol_state = "committed_restart"
        return guard
    except DatabaseBackupError as exc:
        if directory_fd >= 0:
            try:
                os.close(directory_fd)
            except OSError:
                pass
        raise DatabaseBackupRecoveryRequired(
            "committed migration backup marker does not match verified backup state"
        ) from exc
    except Exception:
        if directory_fd >= 0:
            try:
                os.close(directory_fd)
            except OSError:
                pass
        raise


def require_no_migration_marker(connection: sqlite3.Connection) -> None:
    """Reject a pre-target schema that already carries a commit marker."""

    if any(_metadata_value(connection, key) is not None for key in _MARKER_KEYS):
        raise DatabaseBackupError("old database schema contains a migration backup commit marker")


def pre_v4_backup_paths(db_path: Path) -> tuple[Path, Path]:
    backup_path = db_path.with_name(f"{db_path.name}.pre-v4.sqlite3")
    receipt_path = db_path.with_name(f"{db_path.name}.pre-v4-receipt.json")
    return backup_path, receipt_path


def pre_v7_backup_paths(db_path: Path) -> tuple[Path, Path]:
    backup_path = db_path.with_name(f"{db_path.name}.pre-v7.sqlite3")
    receipt_path = db_path.with_name(f"{db_path.name}.pre-v7-receipt.json")
    return backup_path, receipt_path


def content_addressed_anchor_path(path: Path, physical_sha256: str) -> Path:
    """Return the hidden exact-digest alias path for one artifact."""

    return path.with_name(_anchor_name(path.name, physical_sha256))


def _family_pre_v4(db_path: Path) -> _BackupFamily:
    backup_path, receipt_path = pre_v4_backup_paths(db_path)
    return _BackupFamily(
        marker_key=PRE_V4_MARKER_KEY,
        target_schema_version=TARGET_SCHEMA_VERSION,
        supported_source_versions=frozenset({"unversioned", "0", "1", "2", "3"}),
        backup_path=backup_path,
        receipt_path=receipt_path,
    )


def _family_pre_v7(db_path: Path) -> _BackupFamily:
    backup_path, receipt_path = pre_v7_backup_paths(db_path)
    return _BackupFamily(
        marker_key=PRE_V7_MARKER_KEY,
        target_schema_version=PIS005A_TARGET_SCHEMA_VERSION,
        supported_source_versions=frozenset({"4", "5", "6"}),
        backup_path=backup_path,
        receipt_path=receipt_path,
    )


def _prepare_guard(
    *,
    locked_source: sqlite3.Connection,
    db_path: Path,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    family: _BackupFamily,
    now: datetime | None,
) -> BackupGuard:
    if not locked_source.in_transaction:
        raise DatabaseBackupError("pre-migration backup requires a locked source transaction")
    if source_schema_version not in family.supported_source_versions:
        raise DatabaseBackupError("pre-migration backup source version is unsupported")
    require_no_migration_marker(locked_source)
    directory_fd, directory_status = _open_trusted_directory(db_path.parent)
    backup_fd: int | None = None
    receipt_fd: int | None = None
    try:
        source_logical_digest = _logical_digest_connection(locked_source)
        database_status = _database_path_status(directory_fd, db_path.name)
        backup_fd, backup_status, backup_payload = _prepare_backup_artifact(
            directory_fd=directory_fd,
            canonical_name=family.backup_path.name,
            locked_source=locked_source,
            source_logical_digest=source_logical_digest,
        )
        backup_sha256 = _bytes_digest(backup_payload)
        receipt = _build_receipt(
            backup_name=family.backup_path.name,
            backup_sha256=backup_sha256,
            backup_device=backup_status.st_dev,
            backup_inode=backup_status.st_ino,
            source_schema_version=source_schema_version,
            source_minimum_writer_version=source_minimum_writer_version,
            source_logical_digest=source_logical_digest,
            target_schema_version=family.target_schema_version,
            now=now,
        )
        receipt_fd, receipt_status, receipt_payload, receipt = _prepare_receipt_artifact(
            directory_fd=directory_fd,
            canonical_name=family.receipt_path.name,
            receipt=receipt,
            backup_name=family.backup_path.name,
            backup_sha256=backup_sha256,
            backup_device=backup_status.st_dev,
            backup_inode=backup_status.st_ino,
            source_schema_version=source_schema_version,
            source_minimum_writer_version=source_minimum_writer_version,
            source_logical_digest=source_logical_digest,
            target_schema_version=family.target_schema_version,
        )
        assert backup_fd is not None and receipt_fd is not None
        _fsync_directory_fd(directory_fd)
        guard = BackupGuard(
            db_path=db_path,
            directory_path=db_path.parent,
            directory_fd=directory_fd,
            directory_device=directory_status.st_dev,
            directory_inode=directory_status.st_ino,
            database_device=database_status.st_dev,
            database_inode=database_status.st_ino,
            backup_fd=backup_fd,
            receipt_fd=receipt_fd,
            backup_name=family.backup_path.name,
            backup_anchor_name=_anchor_name(family.backup_path.name, backup_sha256),
            receipt_name=family.receipt_path.name,
            receipt_anchor_name=_anchor_name(
                family.receipt_path.name, _bytes_digest(receipt_payload)
            ),
            backup_physical_sha256=backup_sha256,
            backup_logical_sha256=source_logical_digest,
            receipt_physical_sha256=_bytes_digest(receipt_payload),
            backup_device=backup_status.st_dev,
            backup_inode=backup_status.st_ino,
            receipt_device=receipt_status.st_dev,
            receipt_inode=receipt_status.st_ino,
            receipt=receipt,
            receipt_json=canonical_json(receipt),
            marker_key=family.marker_key,
            source_schema_version=source_schema_version,
        )
        _run_protocol_hook("prepared_before_return", guard)
        return guard
    except Exception as exc:
        for descriptor in (receipt_fd, backup_fd, directory_fd):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if isinstance(
            exc,
            (DatabaseBackupError, DatabaseMigrationOutcomeUnknown, DatabaseBackupRecoveryRequired),
        ):
            raise
        if isinstance(exc, (OSError, sqlite3.DatabaseError, ValueError)):
            raise DatabaseBackupError("pre-migration backup preparation failed") from exc
        raise


def _prepare_backup_artifact(
    *,
    directory_fd: int,
    canonical_name: str,
    locked_source: sqlite3.Connection,
    source_logical_digest: str,
) -> tuple[int, os.stat_result, bytes]:
    related = _related_hidden_names(directory_fd, canonical_name)
    if not _alias_exists(directory_fd, canonical_name):
        if related:
            raise DatabaseBackupError(
                "pre-migration backup has unexpected temporary or anchor names"
            )
        payload = _serialize_locked_source(locked_source)
        if _logical_digest_bytes(payload) != source_logical_digest:
            raise DatabaseBackupError(
                "temporary pre-migration backup does not match the locked source database"
            )
        return _publish_new_payload(
            directory_fd,
            canonical_name,
            payload,
            logical_sha256=source_logical_digest,
        )

    descriptor = _open_alias(directory_fd, canonical_name)
    try:
        payload = _verify_existing_payload(
            descriptor,
            expected_logical_sha256=source_logical_digest,
            label="backup",
        )
        physical_sha256 = _bytes_digest(payload)
        anchor_name = _anchor_name(canonical_name, physical_sha256)
        _require_no_competing_names(directory_fd, canonical_name, anchor_name)
        _adopt_or_verify_anchor(
            directory_fd,
            descriptor,
            canonical_name,
            anchor_name,
            label="backup",
        )
        status = os.fstat(descriptor)
        return descriptor, status, payload
    except Exception:
        os.close(descriptor)
        raise


def _prepare_receipt_artifact(
    *,
    directory_fd: int,
    canonical_name: str,
    receipt: JsonObject,
    backup_name: str,
    backup_sha256: str,
    backup_device: int,
    backup_inode: int,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    source_logical_digest: str,
    target_schema_version: str,
) -> tuple[int, os.stat_result, bytes, JsonObject]:
    expected_payload = _receipt_payload(receipt)
    related = _related_hidden_names(directory_fd, canonical_name)
    if not _alias_exists(directory_fd, canonical_name):
        if related:
            raise DatabaseBackupError(
                "pre-migration receipt has unexpected temporary or anchor names"
            )
        descriptor, status, payload = _publish_new_payload(
            directory_fd,
            canonical_name,
            expected_payload,
            logical_sha256=None,
        )
        return descriptor, status, payload, receipt

    descriptor = _open_alias(directory_fd, canonical_name)
    try:
        payload = _verify_existing_payload(
            descriptor,
            expected_logical_sha256=None,
            label="receipt",
        )
        parsed = _parse_receipt_payload(payload)
        try:
            _validate_receipt(
                parsed,
                backup_name=backup_name,
                backup_sha256=backup_sha256,
                backup_device=backup_device,
                backup_inode=backup_inode,
                source_schema_version=source_schema_version,
                source_minimum_writer_version=source_minimum_writer_version,
                source_logical_digest=source_logical_digest,
                target_schema_version=target_schema_version,
            )
        except DatabaseBackupError as current_error:
            try:
                _validate_legacy_receipt(
                    parsed,
                    backup_name=backup_name,
                    backup_sha256=backup_sha256,
                    source_schema_version=source_schema_version,
                    source_minimum_writer_version=source_minimum_writer_version,
                    source_logical_digest=source_logical_digest,
                    target_schema_version=target_schema_version,
                )
            except DatabaseBackupError:
                raise current_error from None
            related = _related_hidden_names(directory_fd, canonical_name)
            if related:
                raise DatabaseBackupError(
                    "legacy pre-migration receipt has unexpected anchor or temporary names"
                ) from current_error
            status = os.fstat(descriptor)
            _require_path_matches_descriptor(
                directory_fd,
                canonical_name,
                status,
            )
            _require_exact_link_count(descriptor, 1, "receipt")
            try:
                os.unlink(canonical_name, dir_fd=directory_fd)
                _fsync_directory_fd(directory_fd)
            except OSError as exc:
                raise DatabaseBackupError(
                    "legacy pre-migration receipt could not be upgraded safely"
                ) from exc
            os.close(descriptor)
            descriptor = -1
            return (
                *_publish_new_payload(
                    directory_fd,
                    canonical_name,
                    expected_payload,
                    logical_sha256=None,
                ),
                receipt,
            )
        physical_sha256 = _bytes_digest(payload)
        anchor_name = _anchor_name(canonical_name, physical_sha256)
        _require_no_competing_names(directory_fd, canonical_name, anchor_name)
        _adopt_or_verify_anchor(
            directory_fd,
            descriptor,
            canonical_name,
            anchor_name,
            label="receipt",
        )
        status = os.fstat(descriptor)
        return descriptor, status, payload, parsed
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _guard_from_committed_marker(
    *,
    db_path: Path,
    directory_fd: int,
    directory_status: os.stat_result,
    family: _BackupFamily,
    receipt: JsonObject,
    receipt_json: str,
) -> tuple[BackupGuard, bool]:
    source_schema_version = receipt.get("source_schema_version")
    source_minimum_writer_version = receipt.get("source_minimum_writer_version")
    source_logical_digest = receipt.get("source_logical_sha256")
    backup_sha256 = receipt.get("backup_sha256")
    backup_device = receipt.get("backup_device")
    backup_inode = receipt.get("backup_inode")
    if (
        not isinstance(source_schema_version, str)
        or source_schema_version not in family.supported_source_versions
        or (
            source_minimum_writer_version is not None
            and not isinstance(source_minimum_writer_version, str)
        )
        or not isinstance(source_logical_digest, str)
        or not isinstance(backup_sha256, str)
        or type(backup_device) is not int
        or backup_device < 0
        or type(backup_inode) is not int
        or backup_inode < 0
    ):
        raise DatabaseBackupRecoveryRequired("committed migration backup marker is invalid")
    try:
        _validate_receipt(
            receipt,
            backup_name=family.backup_path.name,
            backup_sha256=backup_sha256,
            backup_device=backup_device,
            backup_inode=backup_inode,
            source_schema_version=source_schema_version,
            source_minimum_writer_version=source_minimum_writer_version,
            source_logical_digest=source_logical_digest,
            target_schema_version=family.target_schema_version,
        )
    except DatabaseBackupError as exc:
        raise DatabaseBackupRecoveryRequired(
            "committed migration backup marker receipt is invalid"
        ) from exc

    backup_anchor_name = _anchor_name(family.backup_path.name, backup_sha256)
    _require_no_competing_names(
        directory_fd,
        family.backup_path.name,
        backup_anchor_name,
        committed=True,
    )
    backup_fd, backup_status, backup_repaired = _open_or_repair_committed_backup(
        directory_fd=directory_fd,
        canonical_name=family.backup_path.name,
        anchor_name=backup_anchor_name,
        backup_sha256=backup_sha256,
        source_logical_digest=source_logical_digest,
        expected_device=backup_device,
        expected_inode=backup_inode,
    )
    receipt_fd: int | None = None
    release_descriptors = True
    try:
        _require_backup_version_metadata(
            _read_descriptor(backup_fd),
            source_schema_version=source_schema_version,
            source_minimum_writer_version=source_minimum_writer_version,
        )
        expected_receipt_payload = (receipt_json + "\n").encode("utf-8")
        receipt_sha256 = _bytes_digest(expected_receipt_payload)
        receipt_anchor_name = _anchor_name(family.receipt_path.name, receipt_sha256)
        _require_no_competing_names(
            directory_fd,
            family.receipt_path.name,
            receipt_anchor_name,
            committed=True,
        )
        receipt_fd, receipt_status, receipt_repaired = _open_or_restore_receipt_projection(
            directory_fd=directory_fd,
            canonical_name=family.receipt_path.name,
            anchor_name=receipt_anchor_name,
            expected_payload=expected_receipt_payload,
        )
        database_status = _database_path_status(directory_fd, db_path.name)
        guard = BackupGuard(
            db_path=db_path,
            directory_path=db_path.parent,
            directory_fd=directory_fd,
            directory_device=directory_status.st_dev,
            directory_inode=directory_status.st_ino,
            database_device=database_status.st_dev,
            database_inode=database_status.st_ino,
            backup_fd=backup_fd,
            receipt_fd=receipt_fd,
            backup_name=family.backup_path.name,
            backup_anchor_name=backup_anchor_name,
            receipt_name=family.receipt_path.name,
            receipt_anchor_name=receipt_anchor_name,
            backup_physical_sha256=backup_sha256,
            backup_logical_sha256=source_logical_digest,
            receipt_physical_sha256=receipt_sha256,
            backup_device=backup_status.st_dev,
            backup_inode=backup_status.st_ino,
            receipt_device=receipt_status.st_dev,
            receipt_inode=receipt_status.st_ino,
            receipt=receipt,
            receipt_json=receipt_json,
            marker_key=family.marker_key,
            source_schema_version=source_schema_version,
        )
        if backup_repaired or receipt_repaired:
            _fsync_directory_fd(directory_fd)
            guard._verify_final_aliases()
        release_descriptors = False
        return guard, backup_repaired or receipt_repaired
    finally:
        if release_descriptors:
            if receipt_fd is not None:
                os.close(receipt_fd)
            os.close(backup_fd)


def _open_or_repair_committed_backup(
    *,
    directory_fd: int,
    canonical_name: str,
    anchor_name: str,
    backup_sha256: str,
    source_logical_digest: str,
    expected_device: int,
    expected_inode: int,
) -> tuple[int, os.stat_result, bool]:
    canonical = _open_valid_content_alias(
        directory_fd,
        canonical_name,
        expected_sha256=backup_sha256,
        expected_logical_sha256=source_logical_digest,
        expected_device=expected_device,
        expected_inode=expected_inode,
        label="backup",
    )
    if canonical is not None:
        canonical_fd, canonical_status = canonical
        anchor_status = _alias_status(directory_fd, anchor_name)
        if _status_matches(anchor_status, canonical_status):
            _require_exact_link_count(canonical_fd, 2, "backup", committed=True)
            return canonical_fd, canonical_status, False
        anchor = _open_valid_content_alias(
            directory_fd,
            anchor_name,
            expected_sha256=backup_sha256,
            expected_logical_sha256=source_logical_digest,
            expected_device=expected_device,
            expected_inode=expected_inode,
            label="backup",
        )
        if anchor is not None:
            os.close(anchor[0])
            os.close(canonical_fd)
            raise DatabaseBackupRecoveryRequired(
                "committed migration backup aliases name different valid inodes"
            )
        try:
            _repair_alias_from_survivor(
                directory_fd,
                canonical_fd,
                canonical_name,
                anchor_name,
                canonical_status.st_dev,
                canonical_status.st_ino,
                label="backup",
            )
        except Exception:
            os.close(canonical_fd)
            raise
        return canonical_fd, os.fstat(canonical_fd), True

    anchor = _open_valid_content_alias(
        directory_fd,
        anchor_name,
        expected_sha256=backup_sha256,
        expected_logical_sha256=source_logical_digest,
        expected_device=expected_device,
        expected_inode=expected_inode,
        label="backup",
    )
    if anchor is None:
        raise DatabaseBackupRecoveryRequired("committed migration has no valid exact backup alias")
    anchor_fd, anchor_status = anchor
    try:
        _repair_alias_from_survivor(
            directory_fd,
            anchor_fd,
            anchor_name,
            canonical_name,
            anchor_status.st_dev,
            anchor_status.st_ino,
            label="backup",
        )
    except Exception:
        os.close(anchor_fd)
        raise
    return anchor_fd, os.fstat(anchor_fd), True


def _open_or_restore_receipt_projection(
    *,
    directory_fd: int,
    canonical_name: str,
    anchor_name: str,
    expected_payload: bytes,
) -> tuple[int, os.stat_result, bool]:
    expected_sha256 = _bytes_digest(expected_payload)
    canonical = _open_valid_content_alias(
        directory_fd,
        canonical_name,
        expected_sha256=expected_sha256,
        expected_logical_sha256=None,
        expected_device=None,
        expected_inode=None,
        label="receipt",
    )
    if canonical is not None:
        canonical_fd, canonical_status = canonical
        anchor_status = _alias_status(directory_fd, anchor_name)
        if _status_matches(anchor_status, canonical_status):
            _require_exact_link_count(canonical_fd, 2, "receipt", committed=True)
            return canonical_fd, canonical_status, False
        anchor = _open_valid_content_alias(
            directory_fd,
            anchor_name,
            expected_sha256=expected_sha256,
            expected_logical_sha256=None,
            expected_device=None,
            expected_inode=None,
            label="receipt",
        )
        if anchor is None:
            try:
                _repair_alias_from_survivor(
                    directory_fd,
                    canonical_fd,
                    canonical_name,
                    anchor_name,
                    canonical_status.st_dev,
                    canonical_status.st_ino,
                    label="receipt",
                )
            except Exception:
                os.close(canonical_fd)
                raise
            return canonical_fd, os.fstat(canonical_fd), True
        os.close(anchor[0])
        os.close(canonical_fd)
        _remove_receipt_projection_aliases(directory_fd, canonical_name, anchor_name)
        descriptor, status, _ = _publish_new_payload(
            directory_fd,
            canonical_name,
            expected_payload,
            logical_sha256=None,
        )
        return descriptor, status, True

    anchor = _open_valid_content_alias(
        directory_fd,
        anchor_name,
        expected_sha256=expected_sha256,
        expected_logical_sha256=None,
        expected_device=None,
        expected_inode=None,
        label="receipt",
    )
    if anchor is not None:
        anchor_fd, anchor_status = anchor
        try:
            _repair_alias_from_survivor(
                directory_fd,
                anchor_fd,
                anchor_name,
                canonical_name,
                anchor_status.st_dev,
                anchor_status.st_ino,
                label="receipt",
            )
        except Exception:
            os.close(anchor_fd)
            raise
        return anchor_fd, os.fstat(anchor_fd), True

    _remove_receipt_projection_aliases(directory_fd, canonical_name, anchor_name)
    descriptor, status, _ = _publish_new_payload(
        directory_fd,
        canonical_name,
        expected_payload,
        logical_sha256=None,
    )
    return descriptor, status, True


def _remove_receipt_projection_aliases(
    directory_fd: int,
    canonical_name: str,
    anchor_name: str,
) -> None:
    seen: set[tuple[int, int]] = set()
    for name in (canonical_name, anchor_name):
        status = _alias_status(directory_fd, name)
        if status is None:
            continue
        identity = (status.st_dev, status.st_ino)
        if stat.S_ISREG(status.st_mode) and identity not in seen and status.st_nlink > 2:
            raise DatabaseBackupRecoveryRequired(
                "committed migration receipt has an unexpected hardlink count"
            )
        seen.add(identity)
        _unlink_alias_for_repair(directory_fd, name)


def _publish_new_payload(
    directory_fd: int,
    canonical_name: str,
    payload: bytes,
    *,
    logical_sha256: str | None,
) -> tuple[int, os.stat_result, bytes]:
    temporary_name = f".{canonical_name}.{uuid4().hex}.tmp"
    descriptor = _open_unique_temporary(directory_fd, temporary_name)
    canonical_published = False
    anchor_published = False
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
        verified_payload = _read_descriptor(descriptor)
        if verified_payload != payload:
            raise DatabaseBackupError("temporary migration backup artifact bytes changed")
        if logical_sha256 is not None and _logical_digest_bytes(payload) != logical_sha256:
            raise DatabaseBackupError(
                "temporary pre-migration backup does not match the locked source database"
            )
        _require_private_regular_descriptor(descriptor, exact_link_count=1)
        physical_sha256 = _bytes_digest(payload)
        anchor_name = _anchor_name(canonical_name, physical_sha256)
        _require_no_competing_names(
            directory_fd,
            canonical_name,
            anchor_name,
            additional_allowed={temporary_name},
        )
        _link_no_clobber(directory_fd, temporary_name, canonical_name)
        canonical_published = True
        _require_path_matches_descriptor(directory_fd, canonical_name, os.fstat(descriptor))
        _run_raw_protocol_hook("canonical_published", canonical_name)
        _link_no_clobber(directory_fd, temporary_name, anchor_name)
        anchor_published = True
        _require_path_matches_descriptor(directory_fd, anchor_name, os.fstat(descriptor))
        os.unlink(temporary_name, dir_fd=directory_fd)
        _require_private_regular_descriptor(descriptor, exact_link_count=2)
        status = os.fstat(descriptor)
        _require_alias_pair(
            directory_fd,
            canonical_name,
            anchor_name,
            status.st_dev,
            status.st_ino,
        )
        _fsync_directory_fd(directory_fd)
        return descriptor, status, payload
    except Exception:
        if not canonical_published and not anchor_published:
            _unlink_if_matches(directory_fd, temporary_name, descriptor)
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _adopt_or_verify_anchor(
    directory_fd: int,
    descriptor: int,
    canonical_name: str,
    anchor_name: str,
    *,
    label: str,
) -> None:
    status = os.fstat(descriptor)
    _require_path_matches_descriptor(directory_fd, canonical_name, status)
    anchor_status = _alias_status(directory_fd, anchor_name)
    if anchor_status is None:
        _require_exact_link_count(descriptor, 1, label)
        _link_no_clobber(directory_fd, canonical_name, anchor_name)
        _fsync_directory_fd(directory_fd)
    elif not _status_matches(anchor_status, status):
        raise DatabaseBackupError(f"pre-migration {label} anchor names a different object")
    _require_alias_pair(
        directory_fd,
        canonical_name,
        anchor_name,
        status.st_dev,
        status.st_ino,
    )
    _require_exact_link_count(descriptor, 2, label)


def _repair_held_alias_pair(
    directory_fd: int,
    descriptor: int,
    canonical_name: str,
    anchor_name: str,
    expected_device: int,
    expected_inode: int,
    *,
    label: str,
) -> bool:
    canonical_valid = _alias_matches_identity(
        directory_fd, canonical_name, expected_device, expected_inode
    )
    anchor_valid = _alias_matches_identity(
        directory_fd, anchor_name, expected_device, expected_inode
    )
    if canonical_valid and anchor_valid:
        _require_exact_link_count(descriptor, 2, label, committed=True)
        return False
    if not canonical_valid and not anchor_valid:
        raise DatabaseBackupRecoveryRequired(
            f"committed migration has no surviving exact {label} alias"
        )
    survivor = canonical_name if canonical_valid else anchor_name
    target = anchor_name if canonical_valid else canonical_name
    _repair_alias_from_survivor(
        directory_fd,
        descriptor,
        survivor,
        target,
        expected_device,
        expected_inode,
        label=label,
    )
    return True


def _repair_alias_from_survivor(
    directory_fd: int,
    descriptor: int,
    survivor_name: str,
    target_name: str,
    expected_device: int,
    expected_inode: int,
    *,
    label: str,
) -> None:
    if not _alias_matches_identity(directory_fd, survivor_name, expected_device, expected_inode):
        raise DatabaseBackupRecoveryRequired(f"committed migration {label} survivor alias changed")
    current_links = os.fstat(descriptor).st_nlink
    if current_links not in {1, 2}:
        raise DatabaseBackupRecoveryRequired(
            f"committed migration {label} has an unexpected hardlink count"
        )
    _unlink_alias_for_repair(directory_fd, target_name)
    if not _alias_matches_identity(directory_fd, survivor_name, expected_device, expected_inode):
        raise DatabaseBackupRecoveryRequired(
            f"committed migration {label} survivor alias changed during repair"
        )
    try:
        _link_no_clobber(directory_fd, survivor_name, target_name)
    except (DatabaseBackupError, OSError) as exc:
        raise DatabaseBackupRecoveryRequired(
            f"committed migration {label} alias repair failed"
        ) from exc
    _fsync_directory_fd(directory_fd)
    _require_alias_pair(
        directory_fd,
        survivor_name,
        target_name,
        expected_device,
        expected_inode,
        committed=True,
    )
    _require_exact_link_count(descriptor, 2, label, committed=True)


def _unlink_alias_for_repair(directory_fd: int, name: str) -> None:
    status = _alias_status(directory_fd, name)
    if status is None:
        return
    if stat.S_ISDIR(status.st_mode):
        raise DatabaseBackupRecoveryRequired(
            "committed migration artifact alias is an unexpected directory"
        )
    try:
        os.unlink(name, dir_fd=directory_fd)
    except OSError as exc:
        raise DatabaseBackupRecoveryRequired(
            "committed migration artifact alias could not be removed for repair"
        ) from exc


def _build_receipt(
    *,
    backup_name: str,
    backup_sha256: str,
    backup_device: int,
    backup_inode: int,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    source_logical_digest: str,
    target_schema_version: str,
    now: datetime | None,
) -> JsonObject:
    return {
        "receipt_version": BACKUP_RECEIPT_VERSION,
        "migration_target_schema_version": target_schema_version,
        "source_schema_version": source_schema_version,
        "source_minimum_writer_version": source_minimum_writer_version,
        "source_logical_sha256": source_logical_digest,
        "backup_filename": backup_name,
        "backup_sha256": backup_sha256,
        "backup_device": backup_device,
        "backup_inode": backup_inode,
        "created_at": (now or datetime.now(UTC)).isoformat(),
        "downgrade_posture": "restore_only",
    }


def _validate_receipt(
    receipt: JsonObject,
    *,
    backup_name: str,
    backup_sha256: str,
    backup_device: int,
    backup_inode: int,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    source_logical_digest: str,
    target_schema_version: str,
) -> None:
    expected: JsonObject = {
        "receipt_version": BACKUP_RECEIPT_VERSION,
        "migration_target_schema_version": target_schema_version,
        "source_schema_version": source_schema_version,
        "source_minimum_writer_version": source_minimum_writer_version,
        "source_logical_sha256": source_logical_digest,
        "backup_filename": backup_name,
        "backup_sha256": backup_sha256,
        "backup_device": backup_device,
        "backup_inode": backup_inode,
        "downgrade_posture": "restore_only",
    }
    _validate_receipt_fields(receipt, expected)


def _validate_legacy_receipt(
    receipt: JsonObject,
    *,
    backup_name: str,
    backup_sha256: str,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    source_logical_digest: str,
    target_schema_version: str,
) -> None:
    expected: JsonObject = {
        "receipt_version": _LEGACY_BACKUP_RECEIPT_VERSION,
        "migration_target_schema_version": target_schema_version,
        "source_schema_version": source_schema_version,
        "source_minimum_writer_version": source_minimum_writer_version,
        "source_logical_sha256": source_logical_digest,
        "backup_filename": backup_name,
        "backup_sha256": backup_sha256,
        "downgrade_posture": "restore_only",
    }
    _validate_receipt_fields(receipt, expected)


def _validate_receipt_fields(receipt: JsonObject, expected: JsonObject) -> None:
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise DatabaseBackupError(f"pre-migration backup receipt {key} mismatch")
    for key in ("backup_device", "backup_inode"):
        if key in expected and (
            type(receipt.get(key)) is not int or cast(int, receipt[key]) < 0
        ):
            raise DatabaseBackupError(f"pre-migration backup receipt {key} is invalid")
    created_at = receipt.get("created_at")
    if not isinstance(created_at, str):
        raise DatabaseBackupError("pre-migration backup receipt timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(created_at)
    except ValueError as exc:
        raise DatabaseBackupError("pre-migration backup receipt timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise DatabaseBackupError("pre-migration backup receipt timestamp is invalid")
    if set(receipt) != {*expected, "created_at"}:
        raise DatabaseBackupError("pre-migration backup receipt fields are not closed")
    for key in ("backup_sha256", "source_logical_sha256"):
        value = receipt.get(key)
        if not isinstance(value, str) or not _valid_sha256(value):
            raise DatabaseBackupError(f"pre-migration backup receipt {key} is invalid")


def _parse_receipt_payload(payload: bytes) -> JsonObject:
    if not payload.endswith(b"\n"):
        raise DatabaseBackupError("pre-migration backup receipt is not newline terminated")
    try:
        text = payload.decode("utf-8")
        document = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise DatabaseBackupError("pre-migration backup receipt is invalid") from exc
    if not isinstance(document, dict):
        raise DatabaseBackupError("pre-migration backup receipt is invalid")
    receipt = cast(JsonObject, document)
    if _receipt_payload(receipt) != payload:
        raise DatabaseBackupError("pre-migration backup receipt bytes are not canonical")
    return receipt


def _parse_marker_json(value: str) -> JsonObject:
    try:
        document = json.loads(value, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        raise DatabaseBackupRecoveryRequired(
            "committed migration backup marker is invalid"
        ) from exc
    if not isinstance(document, dict):
        raise DatabaseBackupRecoveryRequired("committed migration backup marker is invalid")
    receipt = cast(JsonObject, document)
    if canonical_json(receipt) != value:
        raise DatabaseBackupRecoveryRequired(
            "committed migration backup marker JSON is not canonical"
        )
    return receipt


def _receipt_payload(receipt: JsonObject) -> bytes:
    return (canonical_json(receipt) + "\n").encode("utf-8")


def _serialize_locked_source(connection: sqlite3.Connection) -> bytes:
    try:
        return connection.serialize()
    except sqlite3.DatabaseError as exc:
        raise DatabaseBackupError("locked migration source could not be serialized") from exc


def _logical_digest_bytes(payload: bytes) -> str:
    connection = sqlite3.connect(":memory:")
    try:
        connection.deserialize(payload)
        return _logical_digest_connection(connection)
    except sqlite3.DatabaseError as exc:
        raise DatabaseBackupError("database backup source is invalid") from exc
    finally:
        connection.close()


def _logical_digest_connection(connection: sqlite3.Connection) -> str:
    """Digest one SQLite connection's locked logical snapshot."""

    try:
        row = connection.execute("PRAGMA integrity_check").fetchone()
        if row != ("ok",):
            raise DatabaseBackupError("database integrity check failed")
        dump = "\n".join(connection.iterdump()).encode("utf-8")
    except sqlite3.DatabaseError as exc:
        raise DatabaseBackupError("database backup source is invalid") from exc
    return f"{_SHA256_PREFIX}{hashlib.sha256(dump).hexdigest()}"


def _require_backup_version_metadata(
    payload: bytes,
    *,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
) -> None:
    connection = sqlite3.connect(":memory:")
    try:
        connection.deserialize(payload)
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'app_metadata'"
        ).fetchone()
        if table is None:
            actual_schema = "unversioned"
            actual_minimum_writer: str | None = None
        else:
            actual_schema = _metadata_value(connection, "schema_version") or "unversioned"
            actual_minimum_writer = _metadata_value(connection, "minimum_writer_version")
    except sqlite3.DatabaseError as exc:
        raise DatabaseBackupError("migration backup metadata cannot be verified") from exc
    finally:
        connection.close()
    if (
        actual_schema != source_schema_version
        or actual_minimum_writer != source_minimum_writer_version
    ):
        raise DatabaseBackupError("migration backup source metadata differs from the receipt")


def _open_trusted_directory(path: Path) -> tuple[int, os.stat_result]:
    _require_platform_support()
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise DatabaseBackupError("database directory cannot be opened safely") from exc
    try:
        status = os.fstat(descriptor)
        _require_trusted_directory_status(status)
        _require_directory_identity(path, descriptor, status.st_dev, status.st_ino)
        return descriptor, status
    except Exception:
        os.close(descriptor)
        raise


def _require_platform_support() -> None:
    required_flags = ("O_CLOEXEC", "O_DIRECTORY", "O_NOFOLLOW")
    if any(not hasattr(os, flag) for flag in required_flags):
        raise DatabaseBackupError("required no-follow descriptor semantics are unsupported")
    if (
        os.listdir not in os.supports_fd
        or any(
            function not in os.supports_dir_fd
            for function in (os.open, os.stat, os.unlink, os.link)
        )
        or os.link not in os.supports_follow_symlinks
    ):
        raise DatabaseBackupError("required hardlink directory-fd semantics are unsupported")


def _require_trusted_directory_status(status: os.stat_result) -> None:
    if not stat.S_ISDIR(status.st_mode):
        raise DatabaseBackupError("database directory must be a real directory")
    if status.st_uid != os.geteuid():
        raise DatabaseBackupError("database directory must be owned by the current user")
    if stat.S_IMODE(status.st_mode) & 0o022:
        raise DatabaseBackupError("database directory must not be group or world writable")


def _require_directory_identity(
    path: Path,
    descriptor: int,
    expected_device: int,
    expected_inode: int,
) -> None:
    descriptor_status = os.fstat(descriptor)
    try:
        path_status = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise DatabaseBackupError("database directory identity cannot be verified") from exc
    if (
        not stat.S_ISDIR(path_status.st_mode)
        or descriptor_status.st_dev != expected_device
        or descriptor_status.st_ino != expected_inode
        or path_status.st_dev != expected_device
        or path_status.st_ino != expected_inode
    ):
        raise DatabaseBackupError("database directory identity changed")
    _require_trusted_directory_status(descriptor_status)


def _database_path_status(directory_fd: int, name: str) -> os.stat_result:
    status = _alias_status(directory_fd, name)
    if status is None or not stat.S_ISREG(status.st_mode) or status.st_uid != os.geteuid():
        raise DatabaseBackupError("database pathname must name a current-user-owned regular file")
    return status


def _require_database_path_identity(
    directory_fd: int,
    name: str,
    expected_device: int,
    expected_inode: int,
) -> None:
    status = _database_path_status(directory_fd, name)
    if status.st_dev != expected_device or status.st_ino != expected_inode:
        raise DatabaseBackupError("database pathname identity changed during migration")


def _open_unique_temporary(directory_fd: int, name: str) -> int:
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
    except OSError as exc:
        raise DatabaseBackupError("unique migration backup temporary file creation failed") from exc
    os.fchmod(descriptor, 0o600)
    return descriptor


def _open_alias(directory_fd: int, name: str) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except OSError as exc:
        raise DatabaseBackupError(
            "migration backup artifact must be a safely opened regular file"
        ) from exc
    try:
        _require_private_regular_descriptor(descriptor, exact_link_count=None)
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _open_valid_content_alias(
    directory_fd: int,
    name: str,
    *,
    expected_sha256: str,
    expected_logical_sha256: str | None,
    expected_device: int | None,
    expected_inode: int | None,
    label: str,
) -> tuple[int, os.stat_result] | None:
    try:
        descriptor = _open_alias(directory_fd, name)
    except DatabaseBackupError:
        return None
    try:
        status = os.fstat(descriptor)
        if (
            expected_device is not None
            and expected_inode is not None
            and (
                status.st_dev != expected_device
                or status.st_ino != expected_inode
            )
        ):
            os.close(descriptor)
            return None
        payload = _verify_existing_payload(
            descriptor,
            expected_logical_sha256=expected_logical_sha256,
            label=label,
        )
        if _bytes_digest(payload) != expected_sha256:
            os.close(descriptor)
            return None
        return descriptor, status
    except DatabaseBackupError:
        os.close(descriptor)
        return None


def _verify_existing_payload(
    descriptor: int,
    *,
    expected_logical_sha256: str | None,
    label: str,
) -> bytes:
    _require_private_regular_descriptor(descriptor, exact_link_count=None)
    payload = _read_descriptor(descriptor)
    if expected_logical_sha256 is not None:
        if _logical_digest_bytes(payload) != expected_logical_sha256:
            raise DatabaseBackupError(
                f"pre-migration {label} no longer matches the locked source database"
            )
    return payload


def _verify_descriptor(
    descriptor: int,
    *,
    expected_device: int,
    expected_inode: int,
    expected_sha256: str,
    expected_logical_sha256: str | None,
    label: str,
    exact_link_count: int | None,
) -> bytes:
    status = os.fstat(descriptor)
    _require_private_regular_descriptor(descriptor, exact_link_count=exact_link_count)
    if status.st_dev != expected_device or status.st_ino != expected_inode:
        raise DatabaseBackupError(f"verified migration {label} descriptor identity changed")
    payload = _read_descriptor(descriptor)
    if _bytes_digest(payload) != expected_sha256:
        raise DatabaseBackupError(f"verified migration {label} bytes changed")
    if (
        expected_logical_sha256 is not None
        and _logical_digest_bytes(payload) != expected_logical_sha256
    ):
        raise DatabaseBackupError(f"verified migration {label} logical snapshot changed")
    return payload


def _require_private_regular_descriptor(
    descriptor: int,
    *,
    exact_link_count: int | None,
) -> None:
    status = os.fstat(descriptor)
    if not stat.S_ISREG(status.st_mode):
        raise DatabaseBackupError("migration backup artifact must be a regular file")
    if stat.S_IMODE(status.st_mode) != 0o600:
        raise DatabaseBackupError("migration backup artifact permissions must be exactly 0600")
    if status.st_uid != os.geteuid():
        raise DatabaseBackupError("migration backup artifact owner is invalid")
    if exact_link_count is not None and status.st_nlink != exact_link_count:
        raise DatabaseBackupError("migration backup artifact hardlink count is invalid")


def _require_exact_link_count(
    descriptor: int,
    expected: int,
    label: str,
    *,
    committed: bool = False,
) -> None:
    if os.fstat(descriptor).st_nlink == expected:
        return
    message = f"migration {label} artifact hardlink count is invalid"
    if committed:
        raise DatabaseBackupRecoveryRequired(message)
    raise DatabaseBackupError(message)


def _link_no_clobber(directory_fd: int, source_name: str, destination_name: str) -> None:
    try:
        os.link(
            source_name,
            destination_name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise DatabaseBackupError(
            "migration backup alias publication did not remain no-clobber"
        ) from exc


def _require_alias_pair(
    directory_fd: int,
    canonical_name: str,
    anchor_name: str,
    expected_device: int,
    expected_inode: int,
    *,
    committed: bool = False,
) -> None:
    for name in (canonical_name, anchor_name):
        if not _alias_matches_identity(directory_fd, name, expected_device, expected_inode):
            if committed:
                raise DatabaseBackupRecoveryRequired(
                    "committed migration backup alias was substituted"
                )
            raise DatabaseBackupError("verified pre-migration backup alias was substituted")


def _require_path_matches_descriptor(
    directory_fd: int,
    name: str,
    descriptor_status: os.stat_result,
) -> None:
    if not _alias_matches_identity(
        directory_fd,
        name,
        descriptor_status.st_dev,
        descriptor_status.st_ino,
    ):
        raise DatabaseBackupError("verified pre-migration backup object was substituted")


def _alias_matches_identity(
    directory_fd: int,
    name: str,
    expected_device: int,
    expected_inode: int,
) -> bool:
    status = _alias_status(directory_fd, name)
    return (
        status is not None
        and stat.S_ISREG(status.st_mode)
        and status.st_dev == expected_device
        and status.st_ino == expected_inode
        and status.st_uid == os.geteuid()
        and stat.S_IMODE(status.st_mode) == 0o600
    )


def _alias_status(directory_fd: int, name: str) -> os.stat_result | None:
    try:
        return os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise DatabaseBackupError("migration backup alias identity cannot be inspected") from exc


def _status_matches(
    candidate: os.stat_result | None,
    expected: os.stat_result,
) -> bool:
    return (
        candidate is not None
        and stat.S_ISREG(candidate.st_mode)
        and candidate.st_dev == expected.st_dev
        and candidate.st_ino == expected.st_ino
        and candidate.st_uid == os.geteuid()
        and stat.S_IMODE(candidate.st_mode) == 0o600
    )


def _alias_exists(directory_fd: int, name: str) -> bool:
    return _alias_status(directory_fd, name) is not None


def _anchor_name(canonical_name: str, physical_sha256: str) -> str:
    if not _valid_sha256(physical_sha256):
        raise DatabaseBackupError("migration backup physical digest is invalid")
    return f".{canonical_name}.sha256-{physical_sha256.removeprefix(_SHA256_PREFIX)}"


def _valid_sha256(value: str) -> bool:
    digest = value.removeprefix(_SHA256_PREFIX)
    return (
        value.startswith(_SHA256_PREFIX)
        and len(digest) == 64
        and all(character in "0123456789abcdef" for character in digest)
    )


def _related_hidden_names(directory_fd: int, canonical_name: str) -> set[str]:
    prefix = f".{canonical_name}."
    return {name for name in os.listdir(directory_fd) if name.startswith(prefix)}


def _require_no_competing_names(
    directory_fd: int,
    canonical_name: str,
    expected_anchor_name: str,
    *,
    committed: bool = False,
    additional_allowed: set[str] | None = None,
) -> None:
    allowed = {expected_anchor_name}
    if additional_allowed is not None:
        allowed.update(additional_allowed)
    unexpected = _related_hidden_names(directory_fd, canonical_name) - allowed
    if not unexpected:
        return
    message = "migration backup has unexpected competing anchor or temporary names"
    if committed:
        raise DatabaseBackupRecoveryRequired(message)
    raise DatabaseBackupError(message)


def _any_backup_artifacts(directory_fd: int, db_path: Path) -> bool:
    for family in (_family_pre_v4(db_path), _family_pre_v7(db_path)):
        for canonical_name in (family.backup_path.name, family.receipt_path.name):
            if _alias_exists(directory_fd, canonical_name):
                return True
            if _related_hidden_names(directory_fd, canonical_name):
                return True
    return False


def _write_all(descriptor: int, payload: bytes) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    os.ftruncate(descriptor, 0)
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise DatabaseBackupError("migration backup artifact write did not complete")
        view = view[written:]
    os.lseek(descriptor, 0, os.SEEK_SET)


def _read_descriptor(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while chunk := os.read(descriptor, 1024 * 1024):
        chunks.append(chunk)
    return b"".join(chunks)


def _bytes_digest(payload: bytes) -> str:
    return f"{_SHA256_PREFIX}{hashlib.sha256(payload).hexdigest()}"


def _unlink_if_matches(directory_fd: int, name: str, descriptor: int) -> None:
    status = _alias_status(directory_fd, name)
    descriptor_status = os.fstat(descriptor)
    if _status_matches(status, descriptor_status):
        try:
            os.unlink(name, dir_fd=directory_fd)
        except OSError:
            pass


def _fsync_directory_fd(descriptor: int) -> None:
    os.fsync(descriptor)


def _metadata_value(connection: sqlite3.Connection, key: str) -> str | None:
    table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'app_metadata'"
    ).fetchone()
    if table is None:
        return None
    row = connection.execute(
        "SELECT value FROM app_metadata WHERE key = ?",
        (key,),
    ).fetchone()
    return str(row[0]) if row is not None else None


def _commit_connection(connection: sqlite3.Connection) -> None:
    """Single test seam around the guard-owned SQLite commit."""

    connection.execute("COMMIT")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate JSON member: {key}")
        document[key] = value
    return document


def _run_protocol_hook(stage: str, guard: BackupGuard) -> None:
    """No-op production hook used by deterministic race-window tests."""

    del stage, guard


def _run_raw_protocol_hook(stage: str, artifact_name: str) -> None:
    """No-op publication hook used before a full guard exists."""

    del stage, artifact_name

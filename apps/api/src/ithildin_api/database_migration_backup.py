"""Fail-closed coordinated SQLite backup receipt creation and verification."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from ithildin_schemas import JsonObject, canonical_json

BACKUP_RECEIPT_VERSION = "1"
TARGET_SCHEMA_VERSION = "4"
PIS004A_TARGET_SCHEMA_VERSION = "5"
PIS004A_REPAIR_TARGET_SCHEMA_VERSION = "6"
PIS005A_TARGET_SCHEMA_VERSION = "7"


class DatabaseBackupError(RuntimeError):
    """Raised when a safe pre-migration backup cannot be established."""


def ensure_pre_v4_backup(
    *,
    locked_source: sqlite3.Connection,
    db_path: Path,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    now: datetime | None = None,
) -> JsonObject:
    """Create or verify one consistent backup while another connection holds a write lock."""

    return _ensure_pre_migration_backup(
        locked_source=locked_source,
        db_path=db_path,
        source_schema_version=source_schema_version,
        source_minimum_writer_version=source_minimum_writer_version,
        supported_source_versions={"unversioned", "0", "1", "2", "3"},
        target_schema_version=TARGET_SCHEMA_VERSION,
        paths=pre_v4_backup_paths(db_path),
        now=now,
    )


def ensure_pre_v5_backup(
    *,
    locked_source: sqlite3.Connection,
    db_path: Path,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    now: datetime | None = None,
) -> JsonObject:
    """Create or verify the restore-only backup for the local PIS-004A migration."""

    return _ensure_pre_migration_backup(
        locked_source=locked_source,
        db_path=db_path,
        source_schema_version=source_schema_version,
        source_minimum_writer_version=source_minimum_writer_version,
        supported_source_versions={"4"},
        target_schema_version=PIS004A_TARGET_SCHEMA_VERSION,
        paths=pre_v5_backup_paths(db_path),
        now=now,
    )


def ensure_pre_v6_backup(
    *,
    locked_source: sqlite3.Connection,
    db_path: Path,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    now: datetime | None = None,
) -> JsonObject:
    """Create or verify the restore-only backup for the PIS-004A repair migration."""

    return _ensure_pre_migration_backup(
        locked_source=locked_source,
        db_path=db_path,
        source_schema_version=source_schema_version,
        source_minimum_writer_version=source_minimum_writer_version,
        supported_source_versions={"4", "5"},
        target_schema_version=PIS004A_REPAIR_TARGET_SCHEMA_VERSION,
        paths=pre_v6_backup_paths(db_path),
        now=now,
    )


def ensure_pre_v7_backup(
    *,
    locked_source: sqlite3.Connection,
    db_path: Path,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    now: datetime | None = None,
) -> JsonObject:
    """Create or verify the restore-only backup for the PIS-005A migration."""

    return _ensure_pre_migration_backup(
        locked_source=locked_source,
        db_path=db_path,
        source_schema_version=source_schema_version,
        source_minimum_writer_version=source_minimum_writer_version,
        supported_source_versions={"4", "5", "6"},
        target_schema_version=PIS005A_TARGET_SCHEMA_VERSION,
        paths=pre_v7_backup_paths(db_path),
        now=now,
    )


def _ensure_pre_migration_backup(
    *,
    locked_source: sqlite3.Connection,
    db_path: Path,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    supported_source_versions: set[str],
    target_schema_version: str,
    paths: tuple[Path, Path],
    now: datetime | None,
) -> JsonObject:
    if not locked_source.in_transaction:
        raise DatabaseBackupError("pre-migration backup requires a locked source transaction")
    if source_schema_version not in supported_source_versions:
        raise DatabaseBackupError("pre-migration backup source version is unsupported")
    backup_path, receipt_path = paths
    source_logical_digest = _logical_digest_connection(locked_source)
    if receipt_path.exists() or backup_path.exists():
        return _verify_existing_backup(
            backup_path=backup_path,
            receipt_path=receipt_path,
            source_schema_version=source_schema_version,
            source_minimum_writer_version=source_minimum_writer_version,
            source_logical_digest=source_logical_digest,
            target_schema_version=target_schema_version,
            now=now,
        )

    temporary = backup_path.with_name(f".{backup_path.name}.{uuid4().hex}.tmp")
    descriptor: int | None = None
    backup_created = False
    try:
        _create_backup(db_path, temporary)
        descriptor = _open_stable_backup_descriptor(temporary)
        os.fchmod(descriptor, 0o600)
        temporary_payload = _read_descriptor(descriptor)
        if _logical_digest_bytes(temporary_payload) != source_logical_digest:
            raise DatabaseBackupError(
                "temporary pre-migration backup does not match the locked source database"
            )
        _require_private_regular_descriptor(descriptor)
        os.fsync(descriptor)
        verified_status = os.fstat(descriptor)
        os.replace(temporary, backup_path)
        backup_created = True
        _require_path_matches_descriptor(backup_path, verified_status)
        _fsync_directory(backup_path.parent)
        promoted_payload = _read_descriptor(descriptor)
        if promoted_payload != temporary_payload:
            raise DatabaseBackupError(
                "verified pre-migration backup object changed during promotion"
            )
        receipt = _build_receipt(
            backup_path=backup_path,
            backup_sha256=_bytes_digest(promoted_payload),
            source_schema_version=source_schema_version,
            source_minimum_writer_version=source_minimum_writer_version,
            source_logical_digest=source_logical_digest,
            target_schema_version=target_schema_version,
            now=now,
        )
        _write_receipt(receipt_path, receipt)
        _require_path_matches_descriptor(backup_path, verified_status)
        if _read_descriptor(descriptor) != promoted_payload:
            raise DatabaseBackupError(
                "verified pre-migration backup object changed after promotion"
            )
        return receipt
    except DatabaseBackupError:
        if backup_created:
            receipt_path.unlink(missing_ok=True)
            backup_path.unlink(missing_ok=True)
            _fsync_directory(backup_path.parent)
        raise
    except (OSError, sqlite3.DatabaseError, ValueError) as exc:
        if backup_created:
            receipt_path.unlink(missing_ok=True)
            backup_path.unlink(missing_ok=True)
            _fsync_directory(backup_path.parent)
        raise DatabaseBackupError("pre-migration backup creation failed") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def pre_v4_backup_paths(db_path: Path) -> tuple[Path, Path]:
    backup_path = db_path.with_name(f"{db_path.name}.pre-v4.sqlite3")
    receipt_path = db_path.with_name(f"{db_path.name}.pre-v4-receipt.json")
    return backup_path, receipt_path


def pre_v5_backup_paths(db_path: Path) -> tuple[Path, Path]:
    backup_path = db_path.with_name(f"{db_path.name}.pre-v5.sqlite3")
    receipt_path = db_path.with_name(f"{db_path.name}.pre-v5-receipt.json")
    return backup_path, receipt_path


def pre_v6_backup_paths(db_path: Path) -> tuple[Path, Path]:
    backup_path = db_path.with_name(f"{db_path.name}.pre-v6.sqlite3")
    receipt_path = db_path.with_name(f"{db_path.name}.pre-v6-receipt.json")
    return backup_path, receipt_path


def pre_v7_backup_paths(db_path: Path) -> tuple[Path, Path]:
    backup_path = db_path.with_name(f"{db_path.name}.pre-v7.sqlite3")
    receipt_path = db_path.with_name(f"{db_path.name}.pre-v7-receipt.json")
    return backup_path, receipt_path


def _verify_existing_backup(
    *,
    backup_path: Path,
    receipt_path: Path,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    source_logical_digest: str,
    target_schema_version: str,
    now: datetime | None,
) -> JsonObject:
    if not backup_path.is_file():
        raise DatabaseBackupError("pre-migration backup receipt has no backup database")
    _require_private_regular_file(backup_path)
    if _logical_digest(backup_path) != source_logical_digest:
        raise DatabaseBackupError("pre-migration backup no longer matches the source database")
    if receipt_path.exists():
        receipt = _read_receipt(receipt_path)
        _validate_receipt(
            receipt,
            backup_path=backup_path,
            source_schema_version=source_schema_version,
            source_minimum_writer_version=source_minimum_writer_version,
            source_logical_digest=source_logical_digest,
            target_schema_version=target_schema_version,
        )
        return receipt
    receipt = _build_receipt(
        backup_path=backup_path,
        source_schema_version=source_schema_version,
        source_minimum_writer_version=source_minimum_writer_version,
        source_logical_digest=source_logical_digest,
        target_schema_version=target_schema_version,
        now=now,
    )
    _write_receipt(receipt_path, receipt)
    return receipt


def _create_backup(source_path: Path, destination_path: Path) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(destination_path, flags, 0o600)
    os.close(descriptor)
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    destination = sqlite3.connect(destination_path)
    try:
        source.backup(destination)
        row = destination.execute("PRAGMA integrity_check").fetchone()
        if row != ("ok",):
            raise DatabaseBackupError("pre-migration backup integrity check failed")
    finally:
        destination.close()
        source.close()


def _build_receipt(
    *,
    backup_path: Path,
    backup_sha256: str | None = None,
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
        "backup_filename": backup_path.name,
        "backup_sha256": backup_sha256 or _file_digest(backup_path),
        "created_at": (now or datetime.now(UTC)).isoformat(),
        "downgrade_posture": "restore_only",
    }


def _validate_receipt(
    receipt: JsonObject,
    *,
    backup_path: Path,
    source_schema_version: str,
    source_minimum_writer_version: str | None,
    source_logical_digest: str,
    target_schema_version: str,
) -> None:
    expected = {
        "receipt_version": BACKUP_RECEIPT_VERSION,
        "migration_target_schema_version": target_schema_version,
        "source_schema_version": source_schema_version,
        "source_minimum_writer_version": source_minimum_writer_version,
        "source_logical_sha256": source_logical_digest,
        "backup_filename": backup_path.name,
        "backup_sha256": _file_digest(backup_path),
        "downgrade_posture": "restore_only",
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise DatabaseBackupError(f"pre-migration backup receipt {key} mismatch")
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


def _read_receipt(path: Path) -> JsonObject:
    _require_private_regular_file(path)
    try:
        document = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise DatabaseBackupError("pre-migration backup receipt is invalid") from exc
    if not isinstance(document, dict):
        raise DatabaseBackupError("pre-migration backup receipt is invalid")
    return document


def _write_receipt(path: Path, receipt: JsonObject) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        payload = (canonical_json(receipt) + "\n").encode("utf-8")
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise DatabaseBackupError("pre-migration backup receipt already exists")
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _logical_digest(path: Path) -> str:
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            return _logical_digest_connection(connection)
        finally:
            connection.close()
    except sqlite3.DatabaseError as exc:
        raise DatabaseBackupError("database backup source is invalid") from exc


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
    return f"sha256:{hashlib.sha256(dump).hexdigest()}"


def _bytes_digest(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _open_stable_backup_descriptor(path: Path) -> int:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags)


def _read_descriptor(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while chunk := os.read(descriptor, 1024 * 1024):
        chunks.append(chunk)
    return b"".join(chunks)


def _require_private_regular_descriptor(descriptor: int) -> None:
    file_status = os.fstat(descriptor)
    if not stat.S_ISREG(file_status.st_mode):
        raise DatabaseBackupError("pre-migration backup artifact must be a regular file")
    if stat.S_IMODE(file_status.st_mode) & 0o077:
        raise DatabaseBackupError("pre-migration backup artifact permissions must be 0600")


def _require_path_matches_descriptor(path: Path, descriptor_status: os.stat_result) -> None:
    path_status = path.stat(follow_symlinks=False)
    if (
        not stat.S_ISREG(path_status.st_mode)
        or path_status.st_dev != descriptor_status.st_dev
        or path_status.st_ino != descriptor_status.st_ino
    ):
        raise DatabaseBackupError("verified pre-migration backup object was substituted")


def _require_private_regular_file(path: Path) -> None:
    file_status = path.lstat()
    if not stat.S_ISREG(file_status.st_mode):
        raise DatabaseBackupError("pre-migration backup artifact must be a regular file")
    if stat.S_IMODE(file_status.st_mode) & 0o077:
        raise DatabaseBackupError("pre-migration backup artifact permissions must be 0600")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate JSON member: {key}")
        document[key] = value
    return document

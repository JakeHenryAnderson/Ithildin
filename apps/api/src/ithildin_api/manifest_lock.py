"""Deterministic lockfile support for trusted tool manifests."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ithildin_schemas import JsonObject, JsonValue

LOCKFILE_VERSION = 1
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ManifestLockError(RuntimeError):
    """Raised when manifest lock verification fails closed."""


@dataclass(frozen=True)
class ManifestLockRecord:
    path: Path
    name: str
    version: str
    manifest_hash: str


def write_manifest_lock(
    *,
    manifest_dir: Path,
    lock_path: Path,
    records: list[ManifestLockRecord],
) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    payload = manifest_lock_payload(
        manifest_dir=manifest_dir,
        lock_path=lock_path,
        records=records,
    )
    lock_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def manifest_lock_payload(
    *,
    manifest_dir: Path,
    lock_path: Path,
    records: list[ManifestLockRecord],
) -> JsonObject:
    lock_root = lock_path.parent.resolve(strict=False)
    entries: list[JsonValue] = []
    for record in sorted(records, key=lambda item: _relative_lock_path(lock_root, item.path)):
        entries.append(
            {
                "path": _relative_lock_path(lock_root, record.path),
                "name": record.name,
                "version": record.version,
                "manifest_hash": record.manifest_hash,
            }
        )
    return {
        "lockfile_version": LOCKFILE_VERSION,
        "manifest_dir": _relative_lock_path(lock_root, manifest_dir),
        "manifests": entries,
    }


def verify_manifest_lock(
    *,
    manifest_dir: Path,
    lock_path: Path,
    records: list[ManifestLockRecord],
) -> None:
    lock = _read_lock(lock_path)
    lock_root = lock_path.parent.resolve(strict=False)
    expected_manifest_dir = _safe_relative_path(
        raw_path=_string(lock, "manifest_dir"),
        lock_root=lock_root,
    )
    if expected_manifest_dir.resolve(strict=False) != manifest_dir.resolve(strict=False):
        raise ManifestLockError("manifest lock targets a different manifest directory")

    manifest_entries = lock.get("manifests")
    if not isinstance(manifest_entries, list):
        raise ManifestLockError("manifest lock must contain a manifests list")

    locked_by_path: dict[Path, JsonObject] = {}
    locked_names: set[str] = set()
    for item in manifest_entries:
        if not isinstance(item, dict):
            raise ManifestLockError("manifest lock entry must be an object")
        entry = _json_object(item)
        entry_path = _safe_relative_path(raw_path=_string(entry, "path"), lock_root=lock_root)
        if entry_path in locked_by_path:
            raise ManifestLockError(f"duplicate manifest lock path: {_string(entry, 'path')}")
        entry_name = _string(entry, "name")
        if entry_name in locked_names:
            raise ManifestLockError(f"duplicate manifest lock name: {entry_name}")
        locked_by_path[entry_path] = entry
        locked_names.add(entry_name)

    records_by_path = {record.path.resolve(strict=True): record for record in records}
    missing_entries = sorted(
        _relative_lock_path(lock_root, record.path)
        for record in records
        if record.path.resolve(strict=True) not in locked_by_path
    )
    if missing_entries:
        raise ManifestLockError(f"manifest missing from lock: {missing_entries[0]}")

    stale_entries = sorted(
        _relative_lock_path(lock_root, locked_path)
        for locked_path in locked_by_path
        if locked_path.resolve(strict=False) not in records_by_path
    )
    if stale_entries:
        raise ManifestLockError(f"stale manifest lock entry: {stale_entries[0]}")

    for record_path, record in records_by_path.items():
        entry = locked_by_path[record_path]
        if _string(entry, "name") != record.name:
            raise ManifestLockError(f"manifest lock name mismatch: {record.name}")
        if _string(entry, "version") != record.version:
            raise ManifestLockError(f"manifest lock version mismatch: {record.name}")
        locked_hash = _string(entry, "manifest_hash")
        if not SHA256_RE.match(locked_hash):
            raise ManifestLockError(f"invalid manifest hash in lock: {record.name}")
        if locked_hash != record.manifest_hash:
            raise ManifestLockError(f"manifest hash mismatch: {record.name}")


def _read_lock(lock_path: Path) -> JsonObject:
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestLockError(f"manifest lock not found: {lock_path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestLockError(f"manifest lock is invalid JSON: {lock_path}") from exc
    if not isinstance(payload, dict):
        raise ManifestLockError("manifest lock must be a JSON object")
    lock = _json_object(payload)
    if lock.get("lockfile_version") != LOCKFILE_VERSION:
        raise ManifestLockError("unsupported manifest lock version")
    return lock


def _json_object(value: dict[Any, Any]) -> JsonObject:
    result: JsonObject = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ManifestLockError("manifest lock keys must be strings")
        result[key] = item
    return result


def _string(value: JsonObject, key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ManifestLockError(f"manifest lock missing {key}")
    return item


def _safe_relative_path(*, raw_path: str, lock_root: Path) -> Path:
    requested = Path(raw_path)
    if requested.is_absolute() or ".." in requested.parts:
        raise ManifestLockError("manifest lock paths must stay under the lock root")
    return lock_root.joinpath(requested).resolve(strict=False)


def _relative_lock_path(lock_root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(lock_root).as_posix()
    except ValueError as exc:
        raise ManifestLockError("manifest lock paths must stay under the lock root") from exc

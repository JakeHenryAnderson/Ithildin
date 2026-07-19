"""Stdlib-only pre-import verification for an authorized Ithildin API candidate."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RuntimeCandidateVerificationError(RuntimeError):
    """Raised when reviewed runtime identity cannot be established."""


@dataclass(frozen=True)
class RuntimeCandidateVerifier:
    """Retain the startup-selected candidate evidence paths for later revalidation."""

    package_root: Path
    inventory_path: Path
    authorization_path: Path
    allow_test_paths: bool = False

    def verify(self) -> dict[str, str]:
        return verify_runtime_candidate(
            package_root=self.package_root,
            inventory_path=self.inventory_path,
            authorization_path=self.authorization_path,
            allow_test_paths=self.allow_test_paths,
        )


SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
INVENTORY_FIELDS = {
    "schema_version",
    "source_commit",
    "files",
    "dependency_lock_path",
    "dependency_lock_digest",
    "release_artifact_digest",
    "review_packet_digest",
    "evidence_schema_version",
    "reviewed_inventory_digest",
    "candidate_id",
}
AUTHORIZATION_FIELDS = {
    "authorization_id",
    "candidate_id",
    "reviewed_commit",
    "inventory_schema_version",
    "reviewed_inventory_digest",
    "dependency_lock_digest",
    "release_artifact_digest",
    "review_packet_digest",
    "evidence_schema_version",
    "authorized_at",
    "record_hash",
}
FILE_FIELDS = {"path", "sha256"}


def verify_runtime_candidate(
    *,
    package_root: Path,
    inventory_path: Path,
    authorization_path: Path,
    allow_test_paths: bool = False,
) -> dict[str, str]:
    """Verify detached inventory and authorization before importing API code."""

    try:
        root = package_root.resolve(strict=True)
    except OSError as exc:
        raise RuntimeCandidateVerificationError(
            "candidate package root is unavailable"
        ) from exc
    if not root.is_dir():
        raise RuntimeCandidateVerificationError("candidate package root is not a directory")
    if _unsafe_writable(root):
        raise RuntimeCandidateVerificationError("candidate package root has unsafe writable mode")

    _require_regular_no_follow(root, inventory_path)
    inventory = _read_closed_json(inventory_path, INVENTORY_FIELDS, "candidate inventory")
    _require_string(inventory, "schema_version")
    source_commit = _require_pattern(inventory, "source_commit", COMMIT_RE)
    dependency_lock_digest = _require_digest(inventory, "dependency_lock_digest")
    release_artifact_digest = _require_digest(inventory, "release_artifact_digest")
    review_packet_digest = _require_digest(inventory, "review_packet_digest")
    evidence_schema_version = _require_string(inventory, "evidence_schema_version")

    raw_files = inventory.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise RuntimeCandidateVerificationError("candidate inventory files must be non-empty")
    normalized_files: list[dict[str, str]] = []
    previous_path = ""
    for raw_file in raw_files:
        if not isinstance(raw_file, dict) or set(raw_file) != FILE_FIELDS:
            raise RuntimeCandidateVerificationError("candidate inventory file entry is invalid")
        relative = _safe_relative_path(raw_file.get("path"))
        expected_digest = _digest_value(raw_file.get("sha256"), "file sha256")
        if relative <= previous_path:
            raise RuntimeCandidateVerificationError(
                "candidate inventory paths must be sorted and unique"
            )
        previous_path = relative
        candidate_file = root / relative
        _require_regular_no_follow(root, candidate_file)
        actual_digest = _file_digest(candidate_file)
        if actual_digest != expected_digest:
            raise RuntimeCandidateVerificationError("candidate inventory file digest mismatch")
        normalized_files.append({"path": relative, "sha256": actual_digest})

    inventory_core = {
        "schema_version": inventory["schema_version"],
        "files": normalized_files,
    }
    reviewed_inventory_digest = _sha256_json(inventory_core)
    if reviewed_inventory_digest != _require_digest(inventory, "reviewed_inventory_digest"):
        raise RuntimeCandidateVerificationError("reviewed inventory digest mismatch")

    dependency_lock_path = _safe_relative_path(inventory.get("dependency_lock_path"))
    if dependency_lock_path != "uv.lock":
        raise RuntimeCandidateVerificationError("dependency lock path must be uv.lock")
    lock_path = root / dependency_lock_path
    _require_regular_no_follow(root, lock_path)
    if _file_digest(lock_path) != dependency_lock_digest:
        raise RuntimeCandidateVerificationError("dependency lock digest mismatch")

    candidate_core = {
        "source_commit": source_commit,
        "inventory_schema_version": inventory["schema_version"],
        "reviewed_inventory_digest": reviewed_inventory_digest,
        "dependency_lock_digest": dependency_lock_digest,
        "release_artifact_digest": release_artifact_digest,
        "evidence_schema_version": evidence_schema_version,
    }
    candidate_id = _sha256_json(candidate_core)
    if candidate_id != _require_digest(inventory, "candidate_id"):
        raise RuntimeCandidateVerificationError("candidate id mismatch")

    authorization = _read_detached_authorization(
        authorization_path,
        allow_test_paths=allow_test_paths,
    )
    record_hash = _require_digest(authorization, "record_hash")
    authorization_core = {
        key: value for key, value in authorization.items() if key != "record_hash"
    }
    if _sha256_json(authorization_core) != record_hash:
        raise RuntimeCandidateVerificationError("candidate authorization record hash mismatch")

    expected = {
        "candidate_id": candidate_id,
        "reviewed_commit": source_commit,
        "inventory_schema_version": inventory["schema_version"],
        "reviewed_inventory_digest": reviewed_inventory_digest,
        "dependency_lock_digest": dependency_lock_digest,
        "release_artifact_digest": release_artifact_digest,
        "review_packet_digest": review_packet_digest,
        "evidence_schema_version": evidence_schema_version,
    }
    for key, value in expected.items():
        if authorization.get(key) != value:
            raise RuntimeCandidateVerificationError(
                f"candidate authorization does not match verified {key}"
            )
    authorization_id = _require_string(authorization, "authorization_id")
    _require_string(authorization, "authorized_at")

    return {
        "posture": "reviewed",
        "candidate_id": candidate_id,
        "source_commit": source_commit,
        "inventory_schema_version": str(inventory["schema_version"]),
        "reviewed_inventory_digest": reviewed_inventory_digest,
        "dependency_lock_digest": dependency_lock_digest,
        "release_artifact_digest": release_artifact_digest,
        "review_packet_digest": review_packet_digest,
        "evidence_schema_version": evidence_schema_version,
        "authorization_id": authorization_id,
    }


def verifier_from_environment() -> RuntimeCandidateVerifier:
    root = Path(os.environ.get("ITHILDIN_RUNTIME_PACKAGE_ROOT", "/app"))
    inventory = Path(
        os.environ.get(
            "ITHILDIN_RUNTIME_CANDIDATE_INVENTORY_PATH",
            "/app/runtime-candidate-inventory.json",
        )
    )
    authorization = Path(
        os.environ.get(
            "ITHILDIN_RUNTIME_CANDIDATE_AUTHORIZATION_PATH",
            "/run/ithildin-authority/api-candidate.json",
        )
    )
    return RuntimeCandidateVerifier(
        package_root=root,
        inventory_path=inventory,
        authorization_path=authorization,
    )


def verify_from_environment() -> dict[str, str]:
    return verifier_from_environment().verify()


def _read_closed_json(path: Path, fields: set[str], label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeCandidateVerificationError(f"{label} is unavailable or malformed") from exc
    if not isinstance(value, dict) or set(value) != fields:
        raise RuntimeCandidateVerificationError(f"{label} fields are not closed")
    return value


def _read_detached_authorization(
    path: Path,
    *,
    allow_test_paths: bool,
) -> dict[str, Any]:
    if not allow_test_paths and path.parent != Path("/run/ithildin-authority"):
        raise RuntimeCandidateVerificationError("candidate authorization path is not detached")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RuntimeCandidateVerificationError(
            "candidate authorization is unavailable or unsafe"
        ) from exc
    try:
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode):
            raise RuntimeCandidateVerificationError(
                "candidate authorization is not a regular file"
            )
        if details.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            raise RuntimeCandidateVerificationError("candidate authorization is writable")
        if details.st_uid not in {0, os.geteuid()}:
            raise RuntimeCandidateVerificationError(
                "candidate authorization owner is not trusted"
            )
        raw = os.read(descriptor, 65_537)
        if len(raw) > 65_536:
            raise RuntimeCandidateVerificationError("candidate authorization is too large")
    finally:
        os.close(descriptor)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeCandidateVerificationError(
            "candidate authorization is unavailable or malformed"
        ) from exc
    if not isinstance(value, dict) or set(value) != AUTHORIZATION_FIELDS:
        raise RuntimeCandidateVerificationError("candidate authorization fields are not closed")
    return value


def _require_regular_no_follow(root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise RuntimeCandidateVerificationError(
            "candidate inventory path escapes package root"
        ) from exc
    current = root
    for part in relative.parts:
        current = current / part
        try:
            details = current.lstat()
        except OSError as exc:
            raise RuntimeCandidateVerificationError(
                "candidate inventory file is unavailable"
            ) from exc
        if stat.S_ISLNK(details.st_mode):
            raise RuntimeCandidateVerificationError("candidate inventory path contains a symlink")
    final_details = path.stat()
    if not stat.S_ISREG(final_details.st_mode):
        raise RuntimeCandidateVerificationError("candidate inventory entry is not a regular file")
    broadly_writable = final_details.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    process_owned_writable = (
        final_details.st_uid == os.geteuid() and final_details.st_mode & stat.S_IWUSR
    )
    if broadly_writable or process_owned_writable:
        raise RuntimeCandidateVerificationError(
            "candidate inventory file has unsafe writable mode"
        )


def _safe_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise RuntimeCandidateVerificationError("candidate inventory path is invalid")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise RuntimeCandidateVerificationError("candidate inventory path is unsafe")
    return value


def _unsafe_writable(path: Path) -> bool:
    details = path.stat()
    broadly_writable = details.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    process_owned_writable = details.st_uid == os.geteuid() and details.st_mode & stat.S_IWUSR
    return bool(broadly_writable or process_owned_writable)


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise RuntimeCandidateVerificationError("candidate inventory file cannot be read") from exc
    return "sha256:" + digest.hexdigest()


def _sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _require_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise RuntimeCandidateVerificationError(f"{field} must be a non-empty string")
    return value


def _require_pattern(payload: dict[str, Any], field: str, pattern: re.Pattern[str]) -> str:
    value = _require_string(payload, field)
    if not pattern.fullmatch(value):
        raise RuntimeCandidateVerificationError(f"{field} is malformed")
    return value


def _require_digest(payload: dict[str, Any], field: str) -> str:
    return _require_pattern(payload, field, SHA256_RE)


def _digest_value(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise RuntimeCandidateVerificationError(f"{field} is malformed")
    return value

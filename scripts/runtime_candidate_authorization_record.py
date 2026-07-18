"""Create a detached runtime-candidate authorization after explicit operator review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_CANDIDATE_FIELDS = {
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


class AuthorizationRecordError(RuntimeError):
    """Raised when an operator authorization cannot be created safely."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--review-packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorize", action="store_true")
    args = parser.parse_args()
    if not args.authorize:
        parser.error("--authorize is required for this operator action")
    record = build_authorization_record(
        candidate_manifest_path=args.candidate_manifest,
        review_packet_path=args.review_packet,
        repo_root=Path.cwd(),
        require_clean_git=True,
    )
    write_authorization_record(args.output, record)
    print(f"wrote detached runtime-candidate authorization: {args.output}")
    return 0


def build_authorization_record(
    *,
    candidate_manifest_path: Path,
    review_packet_path: Path,
    repo_root: Path,
    require_clean_git: bool,
    authorized_at: datetime | None = None,
) -> dict[str, Any]:
    candidate = _read_json_object(candidate_manifest_path, "candidate manifest")
    if set(candidate) != REQUIRED_CANDIDATE_FIELDS:
        raise AuthorizationRecordError("candidate manifest fields are not closed")
    _validate_candidate_manifest(candidate, repo_root)
    source_commit = _pattern(candidate.get("source_commit"), COMMIT_RE, "source commit")
    candidate_id = _digest(candidate.get("candidate_id"), "candidate id")
    reviewed_inventory_digest = _digest(
        candidate.get("reviewed_inventory_digest"), "reviewed inventory digest"
    )
    dependency_lock_digest = _digest(
        candidate.get("dependency_lock_digest"), "dependency lock digest"
    )
    release_artifact_digest = _digest(
        candidate.get("release_artifact_digest"), "release artifact digest"
    )
    review_packet_digest = _digest(
        candidate.get("review_packet_digest"), "review packet digest"
    )
    inventory_schema_version = _string(candidate.get("schema_version"), "schema version")
    evidence_schema_version = _string(
        candidate.get("evidence_schema_version"), "evidence schema version"
    )
    if _file_digest(review_packet_path) != review_packet_digest:
        raise AuthorizationRecordError("review packet digest does not match candidate")
    packet = _read_json_object(review_packet_path, "review packet")
    if packet.get("candidate_id") != candidate_id:
        raise AuthorizationRecordError("review packet does not name candidate id")

    if require_clean_git:
        head = _git(repo_root, "rev-parse", "HEAD").strip()
        if head != source_commit:
            raise AuthorizationRecordError("reviewed commit does not match repository HEAD")
        if _git(repo_root, "status", "--porcelain").strip():
            raise AuthorizationRecordError("dirty candidate cannot be authorized")

    timestamp = authorized_at or datetime.now(UTC)
    record: dict[str, Any] = {
        "authorization_id": f"rca_{uuid4().hex}",
        "candidate_id": candidate_id,
        "reviewed_commit": source_commit,
        "inventory_schema_version": inventory_schema_version,
        "reviewed_inventory_digest": reviewed_inventory_digest,
        "dependency_lock_digest": dependency_lock_digest,
        "release_artifact_digest": release_artifact_digest,
        "review_packet_digest": review_packet_digest,
        "evidence_schema_version": evidence_schema_version,
        "authorized_at": timestamp.isoformat(),
    }
    record["record_hash"] = _sha256_json(record)
    return record


def write_authorization_record(path: Path, record: dict[str, Any]) -> None:
    if path.parent.name != "runtime-authority":
        raise AuthorizationRecordError("authorization output must be under runtime-authority/")
    if path.parent.is_symlink():
        raise AuthorizationRecordError("authorization output directory must not be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    parent_mode = path.parent.stat().st_mode
    if parent_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise AuthorizationRecordError("authorization output directory is broadly writable")
    data = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode()
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    except OSError as exc:
        raise AuthorizationRecordError("authorization output already exists or is unsafe") from exc
    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o444)
    finally:
        os.close(descriptor)


def _validate_candidate_manifest(candidate: dict[str, Any], package_root: Path) -> None:
    schema_version = _string(candidate.get("schema_version"), "schema version")
    raw_files = candidate.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise AuthorizationRecordError("candidate files must be non-empty")
    normalized: list[dict[str, str]] = []
    previous = ""
    for item in raw_files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise AuthorizationRecordError("candidate file entry is invalid")
        relative = _safe_relative(item.get("path"))
        expected_digest = _digest(item.get("sha256"), "candidate file digest")
        if relative <= previous:
            raise AuthorizationRecordError("candidate paths must be sorted and unique")
        previous = relative
        candidate_file = package_root / relative
        if candidate_file.is_symlink() or not candidate_file.is_file():
            raise AuthorizationRecordError("candidate file is unavailable or unsafe")
        actual_digest = _file_digest(candidate_file)
        if actual_digest != expected_digest:
            raise AuthorizationRecordError("candidate file digest mismatch")
        normalized.append({"path": relative, "sha256": actual_digest})
    reviewed_inventory_digest = _sha256_json(
        {"schema_version": schema_version, "files": normalized}
    )
    if reviewed_inventory_digest != candidate.get("reviewed_inventory_digest"):
        raise AuthorizationRecordError("reviewed inventory digest mismatch")
    dependency_lock_path = _safe_relative(candidate.get("dependency_lock_path"))
    if dependency_lock_path != "uv.lock":
        raise AuthorizationRecordError("dependency lock path must be uv.lock")
    dependency_lock_digest = _file_digest(package_root / dependency_lock_path)
    if dependency_lock_digest != candidate.get("dependency_lock_digest"):
        raise AuthorizationRecordError("dependency lock digest mismatch")
    candidate_core = {
        "source_commit": candidate.get("source_commit"),
        "inventory_schema_version": schema_version,
        "reviewed_inventory_digest": reviewed_inventory_digest,
        "dependency_lock_digest": dependency_lock_digest,
        "release_artifact_digest": candidate.get("release_artifact_digest"),
        "evidence_schema_version": candidate.get("evidence_schema_version"),
    }
    if _sha256_json(candidate_core) != candidate.get("candidate_id"):
        raise AuthorizationRecordError("candidate id mismatch")


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuthorizationRecordError(f"{label} is unavailable or malformed") from exc
    if not isinstance(value, dict):
        raise AuthorizationRecordError(f"{label} must be an object")
    return value


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AuthorizationRecordError("git candidate state is unavailable")
    return result.stdout


def _file_digest(path: Path) -> str:
    try:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise AuthorizationRecordError("review packet is unavailable") from exc


def _sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AuthorizationRecordError(f"{label} must be a non-empty string")
    return value


def _pattern(value: object, pattern: re.Pattern[str], label: str) -> str:
    result = _string(value, label)
    if not pattern.fullmatch(result):
        raise AuthorizationRecordError(f"{label} is malformed")
    return result


def _digest(value: object, label: str) -> str:
    return _pattern(value, SHA256_RE, label)


def _safe_relative(value: object) -> str:
    result = _string(value, "candidate path")
    path = Path(result)
    if path.is_absolute() or ".." in path.parts or "\\" in result or path.as_posix() != result:
        raise AuthorizationRecordError("candidate path is unsafe")
    return result


if __name__ == "__main__":
    raise SystemExit(main())

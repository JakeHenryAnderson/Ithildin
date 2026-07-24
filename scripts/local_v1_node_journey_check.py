"""Validate one explicitly selected Local-v1 synthetic Node journey report."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import cast

from ithildin_schemas import JsonObject

from scripts.local_v1_node_journey_evidence import (
    REPORT_JSON,
    REPORT_MARKDOWN,
    EvidenceValidationError,
    render_markdown,
    scan_safe_text,
    validate_report,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT_BASE = ROOT / "var/local-v1-node-journey"
_RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class EvidenceCheckError(RuntimeError):
    """Raised when selected evidence is unavailable or unsafe."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--expected-candidate", required=True)
    args = parser.parse_args()
    try:
        report_root = resolve_report_root(args.report_root)
        report = check_report(
            report_root,
            expected_candidate=args.expected_candidate,
        )
    except (EvidenceCheckError, EvidenceValidationError) as exc:
        print(f"Local-v1 Node journey evidence check failed: {exc}", file=sys.stderr)
        return 1
    print(
        "Local-v1 Node journey evidence valid: "
        f"run={report['run_id']} candidate={args.expected_candidate}"
    )
    return 0


def resolve_report_root(selected: Path) -> Path:
    _require_safe_base(REPORT_BASE)
    raw = selected if selected.is_absolute() else ROOT / selected
    if raw.is_symlink():
        raise EvidenceCheckError("selected report root must not be a symlink")
    try:
        relative = raw.relative_to(REPORT_BASE)
    except ValueError as exc:
        raise EvidenceCheckError("report root is outside the ignored evidence base") from exc
    if len(relative.parts) != 1 or not _RUN_ID.fullmatch(relative.name):
        raise EvidenceCheckError("report root is not a closed run directory")
    return raw


def check_report(
    report_root: Path,
    *,
    expected_candidate: str,
    now: datetime | None = None,
) -> JsonObject:
    if not _COMMIT.fullmatch(expected_candidate):
        raise EvidenceCheckError("expected candidate must be exactly 40 lowercase hex")
    selected = resolve_report_root(report_root)
    base_descriptor = _open_directory(REPORT_BASE)
    run_descriptor = -1
    try:
        run_descriptor = _open_directory_at(base_descriptor, selected.name)
        json_text = _read_private_regular_at(run_descriptor, REPORT_JSON)
        markdown_text = _read_private_regular_at(run_descriptor, REPORT_MARKDOWN)
        _revalidate_directory(REPORT_BASE, base_descriptor)
        _revalidate_directory_at(base_descriptor, selected.name, run_descriptor)
    finally:
        if run_descriptor >= 0:
            os.close(run_descriptor)
        os.close(base_descriptor)
    scan_safe_text(json_text)
    scan_safe_text(markdown_text)
    try:
        raw = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise EvidenceCheckError("JSON report is malformed") from exc
    if not isinstance(raw, dict):
        raise EvidenceCheckError("JSON report must be an object")
    report = cast(JsonObject, raw)
    validate_report(
        report,
        directory_run_id=selected.name,
        expected_candidate=expected_candidate,
        now=now,
    )
    if markdown_text != render_markdown(report):
        raise EvidenceCheckError("Markdown report does not match the JSON report")
    return report


def _require_safe_base(base: Path) -> None:
    if (
        base.name != "local-v1-node-journey"
        or base.parent != ROOT / "var"
        or base.parent.is_symlink()
        or not base.parent.is_dir()
        or base.is_symlink()
        or not base.is_dir()
    ):
        raise EvidenceCheckError("report base is outside the closed ignored path")


def _open_directory(path: Path) -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise EvidenceCheckError("report directory is unavailable or unsafe") from exc
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise EvidenceCheckError("report directory is not a directory")
    return descriptor


def _open_directory_at(parent: int, name: str) -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        return os.open(name, flags, dir_fd=parent)
    except OSError as exc:
        raise EvidenceCheckError("selected report directory is unavailable or unsafe") from exc


def _read_private_regular_at(parent: int, name: str) -> str:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=parent)
    except OSError as exc:
        raise EvidenceCheckError(f"report file is unavailable: {name}") from exc
    try:
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode):
            raise EvidenceCheckError(f"report file is not regular: {name}")
        if stat.S_IMODE(details.st_mode) & 0o077:
            raise EvidenceCheckError(f"report file permissions are not owner-only: {name}")
        raw = os.read(descriptor, 1_048_577)
    finally:
        os.close(descriptor)
    if len(raw) > 1_048_576:
        raise EvidenceCheckError(f"report file is too large: {name}")
    try:
        return raw.decode("utf-8")
    except UnicodeError as exc:
        raise EvidenceCheckError(f"report file is not UTF-8: {name}") from exc


def _revalidate_directory(path: Path, descriptor: int) -> None:
    try:
        current = os.lstat(path)
        held = os.fstat(descriptor)
    except OSError as exc:
        raise EvidenceCheckError("report base changed during validation") from exc
    if (
        not stat.S_ISDIR(current.st_mode)
        or current.st_dev != held.st_dev
        or current.st_ino != held.st_ino
    ):
        raise EvidenceCheckError("report base changed during validation")


def _revalidate_directory_at(parent: int, name: str, descriptor: int) -> None:
    try:
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        held = os.fstat(descriptor)
    except OSError as exc:
        raise EvidenceCheckError("report run changed during validation") from exc
    if (
        not stat.S_ISDIR(current.st_mode)
        or current.st_dev != held.st_dev
        or current.st_ino != held.st_ino
    ):
        raise EvidenceCheckError("report run changed during validation")


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate one explicitly selected Local-v1 constrained mission journey report."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import cast

from ithildin_schemas import JsonObject, canonical_json

from scripts.local_v1_constrained_mission_journey import (
    REPORT_JSON,
    REPORT_MARKDOWN,
    ConstrainedJourneyError,
    render_markdown,
    validate_report,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT_BASE = ROOT / "var/local-v1-constrained-mission-journey"
_RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class ConstrainedJourneyCheckError(RuntimeError):
    """A safe checker error."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--expected-candidate", required=True)
    args = parser.parse_args()
    try:
        report = check_report(
            args.report_root,
            expected_candidate=args.expected_candidate,
        )
    except (ConstrainedJourneyCheckError, ConstrainedJourneyError) as exc:
        print(f"Constrained mission journey evidence check failed: {exc}", file=sys.stderr)
        return 1
    print(
        "Constrained mission journey evidence valid: "
        f"run={report['run_id']} candidate={args.expected_candidate}"
    )
    return 0


def check_report(report_root: Path, *, expected_candidate: str) -> JsonObject:
    if not _COMMIT.fullmatch(expected_candidate):
        raise ConstrainedJourneyCheckError("expected candidate is invalid")
    selected = resolve_report_root(report_root)
    base_descriptor = _open_directory(REPORT_BASE)
    run_descriptor = -1
    try:
        run_descriptor = _open_directory_at(base_descriptor, selected.name)
        json_text = _read_private_regular_at(run_descriptor, REPORT_JSON)
        markdown_text = _read_private_regular_at(run_descriptor, REPORT_MARKDOWN)
    finally:
        if run_descriptor >= 0:
            os.close(run_descriptor)
        os.close(base_descriptor)
    try:
        raw = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ConstrainedJourneyCheckError("report JSON is malformed") from exc
    if not isinstance(raw, dict):
        raise ConstrainedJourneyCheckError("report JSON must be an object")
    report = cast(JsonObject, raw)
    validate_report(report, expected_candidate=expected_candidate)
    if json_text != canonical_json(report):
        raise ConstrainedJourneyCheckError("report JSON is not canonical")
    if markdown_text != render_markdown(report):
        raise ConstrainedJourneyCheckError("report Markdown differs from JSON")
    return report


def resolve_report_root(selected: Path) -> Path:
    raw = selected if selected.is_absolute() else ROOT / selected
    if raw.is_symlink():
        raise ConstrainedJourneyCheckError("selected report root must not be a symlink")
    try:
        relative = raw.relative_to(REPORT_BASE)
    except ValueError as exc:
        raise ConstrainedJourneyCheckError("report root is outside the evidence base") from exc
    if len(relative.parts) != 1 or not _RUN_ID.fullmatch(relative.name):
        raise ConstrainedJourneyCheckError("report root is not a closed run directory")
    return raw


def _open_directory(path: Path) -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ConstrainedJourneyCheckError("report directory is unavailable") from exc
    details = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(details.st_mode)
        or stat.S_IMODE(details.st_mode) != 0o700
        or details.st_uid != os.geteuid()
        or details.st_gid != os.getegid()
    ):
        os.close(descriptor)
        raise ConstrainedJourneyCheckError("report directory is unsafe")
    return descriptor


def _open_directory_at(parent: int, name: str) -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=parent)
    except OSError as exc:
        raise ConstrainedJourneyCheckError("selected report directory is unavailable") from exc
    details = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(details.st_mode)
        or stat.S_IMODE(details.st_mode) != 0o700
        or details.st_uid != os.geteuid()
        or details.st_gid != os.getegid()
    ):
        os.close(descriptor)
        raise ConstrainedJourneyCheckError("selected report directory is unsafe")
    return descriptor


def _read_private_regular_at(parent: int, name: str) -> str:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=parent)
    except OSError as exc:
        raise ConstrainedJourneyCheckError("report file is unavailable") from exc
    try:
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode)
            or stat.S_IMODE(details.st_mode) != 0o600
            or details.st_uid != os.geteuid()
            or details.st_gid != os.getegid()
        ):
            raise ConstrainedJourneyCheckError("report file permissions are unsafe")
        raw = os.read(descriptor, 1_048_577)
    finally:
        os.close(descriptor)
    if len(raw) > 1_048_576:
        raise ConstrainedJourneyCheckError("report file is too large")
    try:
        return raw.decode("utf-8")
    except UnicodeError as exc:
        raise ConstrainedJourneyCheckError("report file is not UTF-8") from exc


if __name__ == "__main__":
    raise SystemExit(main())

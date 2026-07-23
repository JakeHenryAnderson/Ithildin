"""Shared immutable review-candidate packet validation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from scripts import packet_redaction_scan


def immutable_packet_valid(packet_path: Path, candidate_commit: str) -> bool:
    required_paths = {
        "artifact-hashes.json",
        "git-summary.txt",
        "packet-redaction-scan.txt",
        "release-check.txt",
    }
    try:
        packet_absolute = packet_path.absolute()
        packet_resolved = packet_path.resolve(strict=True)
    except OSError:
        return False
    if (
        not packet_path.is_dir()
        or packet_path.is_symlink()
        or packet_resolved != packet_absolute
        or packet_path.name != f"ithildin-v0.2-review-packet-{candidate_commit[:12]}"
        or not all(
            packet_path.joinpath(relative).is_file()
            and not packet_path.joinpath(relative).is_symlink()
            for relative in required_paths
        )
    ):
        return False

    try:
        git_summary = packet_path.joinpath("git-summary.txt").read_text(encoding="utf-8")
        release_check = packet_path.joinpath("release-check.txt").read_text(encoding="utf-8")
        redaction_scan = packet_path.joinpath("packet-redaction-scan.txt").read_text(
            encoding="utf-8"
        )
        artifact_hashes = json.loads(
            packet_path.joinpath("artifact-hashes.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False

    git_summary_lines = git_summary.splitlines()
    git_summary_commit_lines = [
        line.strip()
        for line in git_summary_lines
        if line.strip().startswith("commit=")
    ]
    git_summary_dirty_lines = [
        line.strip()
        for line in git_summary_lines
        if line.strip().startswith("dirty=")
    ]
    release_lines = release_check.splitlines()
    if (
        len(release_lines) < 9
        or release_lines[:4]
        != ["$ make release-check", "returncode=0", "", "## stdout"]
        or release_lines.count("## stdout") != 1
        or release_lines.count("## stderr") != 1
        or not release_check.endswith("\n\n")
    ):
        return False
    stderr_index = release_lines.index("## stderr")
    if stderr_index < 6 or release_lines[stderr_index - 1] != "":
        return False
    release_stdout_lines = release_lines[4:stderr_index]
    while release_stdout_lines and not release_stdout_lines[-1].strip():
        release_stdout_lines.pop()
    release_stderr_lines = release_lines[stderr_index + 1 :]
    release_commit_lines = [
        line.strip()
        for line in release_stdout_lines
        if line.strip().startswith("git_commit=")
    ]
    release_dirty_lines = [
        line.strip()
        for line in release_stdout_lines
        if line.strip().startswith("git_dirty=")
    ]
    release_stdout_returncodes = [
        line.strip()
        for line in release_stdout_lines
        if line.strip().startswith("returncode=")
    ]
    if (
        git_summary_commit_lines != [f"commit={candidate_commit}"]
        or git_summary_dirty_lines != ["dirty=false"]
        or not release_stdout_lines
        or release_stdout_lines[0] != "$ make release-check"
        or release_commit_lines != [f"git_commit={candidate_commit}"]
        or release_dirty_lines != ["git_dirty=false"]
        or release_stdout_returncodes != ["returncode=0"]
        or release_stdout_lines[-1] != "returncode=0"
        or release_stderr_lines != [""]
        or "findings: `0`" not in redaction_scan
        or "Packet redaction scan passed." not in redaction_scan
        or not isinstance(artifact_hashes, list)
    ):
        return False

    manifest_paths: set[str] = set()
    for item in artifact_hashes:
        if not isinstance(item, dict):
            return False
        relative = item.get("path")
        expected_sha256 = item.get("sha256")
        expected_bytes = item.get("bytes")
        if (
            not isinstance(relative, str)
            or not isinstance(expected_sha256, str)
            or type(expected_bytes) is not int
        ):
            return False
        relative_path = Path(relative)
        if (
            relative in manifest_paths
            or not relative_path.parts
            or relative_path.is_absolute()
            or ".." in relative_path.parts
            or relative_path.as_posix() != relative
            or relative == "artifact-hashes.json"
        ):
            return False
        artifact_path = packet_path / relative_path
        try:
            artifact_resolved = artifact_path.resolve(strict=True)
        except OSError:
            return False
        if (
            not artifact_path.is_file()
            or artifact_path.is_symlink()
            or artifact_resolved != artifact_path.absolute()
            or not artifact_resolved.is_relative_to(packet_resolved)
        ):
            return False
        try:
            content = artifact_path.read_bytes()
        except OSError:
            return False
        if len(content) != expected_bytes:
            return False
        if f"sha256:{hashlib.sha256(content).hexdigest()}" != expected_sha256:
            return False
        manifest_paths.add(relative)

    disk_paths: set[str] = set()
    for path in packet_path.rglob("*"):
        if path.is_symlink():
            return False
        if path.is_file():
            disk_paths.add(path.relative_to(packet_path).as_posix())
        elif not path.is_dir():
            return False
    if manifest_paths | {"artifact-hashes.json"} != disk_paths:
        return False
    if not required_paths.difference({"artifact-hashes.json"}).issubset(manifest_paths):
        return False

    roots_match = re.search(r"(?m)^roots: `1`$", redaction_scan) is not None
    scanned_match = re.search(r"(?m)^scanned_files: `(\d+)`$", redaction_scan)
    if (
        not roots_match
        or scanned_match is None
        or int(scanned_match.group(1)) != len(disk_paths) - 2
    ):
        return False
    try:
        current_redaction = packet_redaction_scan.scan_packet_paths([packet_path])
    except packet_redaction_scan.PacketRedactionScanError:
        return False
    return (
        not current_redaction.findings
        and current_redaction.scanned_files == len(disk_paths)
        and current_redaction.roots == [packet_resolved.as_posix()]
    )

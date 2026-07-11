"""Validate v0.4 review-run manifest artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, TypedDict, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_DIR = ROOT / "var/review-runs"

REQUIRED_FIELDS = {
    "review_id",
    "prompt_file",
    "reviewer_type",
    "reviewer_name",
    "date",
    "commit",
    "dirty",
    "files_inspected",
    "tests_run",
    "output_file",
    "finding_count",
    "severity_counts",
    "closure_matrix_rows_touched",
}
VALID_REVIEWER_TYPES = {"codex_internal", "internal_ai", "external_ai", "human"}
VALID_BINDINGS = {"historical", "current_candidate"}
VALID_SEVERITIES = ("critical", "high", "medium", "low", "informational")
FINDING_ID_PATTERN = re.compile(
    r"^(V03-(INT|EXT|DOCS)-[A-Z0-9]+-\d{3}|"
    r"EXT-(PA|FS|HTTP|SE|PR|MCP|UI|REL)-\d{3}|SUB-GITMETA-\d{3}|"
    r"XH-GITMETA-\d{3})$"
)


class ReviewRunManifestError(RuntimeError):
    """Raised when review-run manifests are invalid."""


class ReviewRunSummary(TypedDict):
    path: str
    review_id: str
    reviewer_type: str
    finding_count: int
    critical: int
    high: int
    binding: str


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", default=str(DEFAULT_RUNS_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        summaries = validate_review_runs(Path(args.runs_dir), ROOT)
    except ReviewRunManifestError as exc:
        print(f"review-run manifest validation failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"count": len(summaries), "review_runs": summaries}, indent=2))
    else:
        print(f"Review-run manifest validation passed: {len(summaries)} run(s).")
        for summary in summaries:
            print(
                f"- {summary['review_id']} {summary['reviewer_type']} "
                f"findings={summary['finding_count']} "
                f"critical={summary['critical']} high={summary['high']} "
                f"({summary['path']})"
            )
    return 0


def validate_review_runs(runs_dir: Path, repo_root: Path) -> list[ReviewRunSummary]:
    if not runs_dir.exists():
        return []
    if not runs_dir.is_dir():
        raise ReviewRunManifestError(f"review-runs path is not a directory: {runs_dir}")

    summaries: list[ReviewRunSummary] = []
    for path in sorted(runs_dir.rglob("review-run-*.json")):
        manifest = _read_manifest(path)
        summaries.append(_validate_manifest(path, manifest, repo_root))
    return summaries


def _read_manifest(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ReviewRunManifestError(f"review-run manifest must not be a symlink: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReviewRunManifestError(f"{path} is not valid JSON") from exc
    if not isinstance(raw, dict):
        raise ReviewRunManifestError(f"{path} must contain a JSON object")
    return raw


def _validate_manifest(
    path: Path,
    manifest: dict[str, Any],
    repo_root: Path,
) -> ReviewRunSummary:
    missing = sorted(field for field in REQUIRED_FIELDS if field not in manifest)
    if missing:
        raise ReviewRunManifestError(f"{_display(path, repo_root)} missing {missing}")

    review_id = _string(manifest["review_id"], "review_id", path)
    reviewer_type = _string(manifest["reviewer_type"], "reviewer_type", path)
    if reviewer_type not in VALID_REVIEWER_TYPES:
        raise ReviewRunManifestError(f"{review_id} has invalid reviewer_type: {reviewer_type}")
    _required_string(manifest["reviewer_name"], "reviewer_name", path)
    _required_string(manifest["date"], "date", path)

    commit = _required_string(manifest["commit"], "commit", path)
    if not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        raise ReviewRunManifestError(f"{review_id} has invalid commit")
    binding = _binding(manifest.get("binding", "historical"), review_id)
    _require_commit_exists(repo_root, commit, review_id)

    dirty = manifest["dirty"]
    if not isinstance(dirty, bool):
        raise ReviewRunManifestError(f"{review_id} dirty must be boolean")
    if binding == "current_candidate":
        current_commit = _git(repo_root, ["rev-parse", "HEAD"])
        if commit != current_commit:
            raise ReviewRunManifestError(
                f"{review_id} current-candidate commit does not exactly match current HEAD"
            )
        current_dirty = current_tree_dirty(repo_root)
        if dirty != current_dirty:
            raise ReviewRunManifestError(
                f"{review_id} current-candidate dirty state does not match current tree"
            )
        expected_fingerprint = _required_string(
            manifest.get("tree_fingerprint"), "tree_fingerprint", path
        )
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", expected_fingerprint):
            raise ReviewRunManifestError(
                f"{review_id} current-candidate tree_fingerprint is invalid"
            )
        observed_fingerprint = current_tree_fingerprint(repo_root)
        if expected_fingerprint != observed_fingerprint:
            raise ReviewRunManifestError(
                f"{review_id} current-candidate tree fingerprint does not match current tree"
            )

    _existing_path(repo_root, _required_string(manifest["prompt_file"], "prompt_file", path))
    _existing_path(repo_root, _required_string(manifest["output_file"], "output_file", path))
    files_inspected = _string_list(manifest["files_inspected"], "files_inspected", path)
    tests_run = _string_list(manifest["tests_run"], "tests_run", path)
    _string_list(
        manifest["closure_matrix_rows_touched"],
        "closure_matrix_rows_touched",
        path,
    )
    if not files_inspected:
        raise ReviewRunManifestError(f"{review_id} files_inspected must not be empty")
    if not tests_run:
        raise ReviewRunManifestError(f"{review_id} tests_run must not be empty")

    findings = manifest.get("findings", [])
    if not isinstance(findings, list):
        raise ReviewRunManifestError(f"{review_id} findings must be a list")
    finding_count = _int(manifest["finding_count"], "finding_count", path)
    if finding_count != len(findings):
        raise ReviewRunManifestError(f"{review_id} finding_count does not match findings")

    severity_counts = _severity_counts(manifest["severity_counts"], review_id)
    observed_counts = {severity: 0 for severity in VALID_SEVERITIES}
    seen_ids: set[str] = set()
    for finding in findings:
        if not isinstance(finding, dict):
            raise ReviewRunManifestError(f"{review_id} finding entries must be objects")
        finding_id = _required_string(finding.get("finding_id"), "finding_id", path)
        if not FINDING_ID_PATTERN.fullmatch(finding_id):
            raise ReviewRunManifestError(f"{review_id} has invalid finding ID: {finding_id}")
        if finding_id in seen_ids:
            raise ReviewRunManifestError(f"{review_id} has duplicate finding ID: {finding_id}")
        seen_ids.add(finding_id)
        severity = _required_string(finding.get("severity"), "severity", path).lower()
        if severity not in VALID_SEVERITIES:
            raise ReviewRunManifestError(f"{finding_id} has invalid severity: {severity}")
        observed_counts[severity] += 1
        if finding.get("kind") == "implementation":
            _string_list(finding.get("files_functions"), "files_functions", path, required=True)
        if finding.get("disposition") in {"fixed", "closed"}:
            _required_string(finding.get("verification_notes"), "verification_notes", path)

    if severity_counts != observed_counts:
        raise ReviewRunManifestError(f"{review_id} severity_counts do not match findings")

    return {
        "path": _display(path, repo_root),
        "review_id": review_id,
        "reviewer_type": reviewer_type,
        "finding_count": finding_count,
        "critical": severity_counts["critical"],
        "high": severity_counts["high"],
        "binding": binding,
    }


def _binding(value: object, review_id: str) -> str:
    if not isinstance(value, str) or value not in VALID_BINDINGS:
        raise ReviewRunManifestError(f"{review_id} has invalid binding: {value}")
    return value


def _require_commit_exists(repo_root: Path, commit: str, review_id: str) -> None:
    try:
        _git(repo_root, ["cat-file", "-e", f"{commit}^{{commit}}"])
    except subprocess.CalledProcessError as exc:
        raise ReviewRunManifestError(
            f"{review_id} recorded commit does not exist in repository history"
        ) from exc


def current_tree_dirty(repo_root: Path) -> bool:
    return bool(_git(repo_root, ["status", "--short", "--untracked-files=all"]))


def current_tree_fingerprint(repo_root: Path) -> str:
    """Bind HEAD plus staged, unstaged, and untracked bytes without emitting their contents."""
    hasher = hashlib.sha256()
    hasher.update(b"ithildin-review-tree-v1\0")
    head = _git_bytes(repo_root, ["rev-parse", "HEAD"]).strip()
    index_diff = _git_bytes(
        repo_root,
        ["diff", "--cached", "--binary", "--no-ext-diff", "HEAD", "--"],
    )
    worktree_diff = _git_bytes(
        repo_root,
        ["diff", "--binary", "--no-ext-diff", "--"],
    )
    hasher.update(len(head).to_bytes(8, "big"))
    hasher.update(head)
    hasher.update(b"index\0")
    hasher.update(len(index_diff).to_bytes(8, "big"))
    hasher.update(index_diff)
    hasher.update(b"worktree\0")
    hasher.update(len(worktree_diff).to_bytes(8, "big"))
    hasher.update(worktree_diff)

    untracked = _git_bytes(
        repo_root,
        ["ls-files", "--others", "--exclude-standard", "-z"],
    ).split(b"\0")
    for raw_path in sorted(item for item in untracked if item):
        relative_path = os.fsdecode(raw_path)
        candidate = repo_root / relative_path
        try:
            candidate.parent.resolve().relative_to(repo_root.resolve())
        except ValueError as exc:
            raise ReviewRunManifestError(
                f"untracked path escapes repository while fingerprinting: {relative_path}"
            ) from exc
        metadata = candidate.lstat()
        hasher.update(b"path\0")
        hasher.update(len(raw_path).to_bytes(8, "big"))
        hasher.update(raw_path)
        if stat.S_ISLNK(metadata.st_mode):
            link_target = os.fsencode(os.readlink(candidate))
            confirmed = candidate.lstat()
            if (confirmed.st_dev, confirmed.st_ino, confirmed.st_mode) != (
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_mode,
            ):
                raise ReviewRunManifestError(
                    f"untracked symlink changed while fingerprinting: {relative_path}"
                )
            hasher.update(stat.S_IFMT(metadata.st_mode).to_bytes(8, "big"))
            hasher.update(stat.S_IMODE(metadata.st_mode).to_bytes(8, "big"))
            hasher.update(len(link_target).to_bytes(8, "big"))
            hasher.update(link_target)
        elif stat.S_ISREG(metadata.st_mode):
            descriptor = -1
            try:
                descriptor = os.open(
                    candidate,
                    os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                )
                confirmed = os.fstat(descriptor)
                if not stat.S_ISREG(confirmed.st_mode) or (
                    confirmed.st_dev,
                    confirmed.st_ino,
                ) != (metadata.st_dev, metadata.st_ino):
                    raise ReviewRunManifestError(
                        f"untracked file changed while fingerprinting: {relative_path}"
                    )
                hasher.update(stat.S_IFMT(confirmed.st_mode).to_bytes(8, "big"))
                hasher.update(stat.S_IMODE(confirmed.st_mode).to_bytes(8, "big"))
                hasher.update(confirmed.st_size.to_bytes(8, "big"))
                with os.fdopen(descriptor, "rb", closefd=True) as stream:
                    descriptor = -1
                    while chunk := stream.read(1024 * 1024):
                        hasher.update(chunk)
            except OSError as exc:
                raise ReviewRunManifestError(
                    f"cannot safely fingerprint untracked file: {relative_path}"
                ) from exc
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
        else:
            raise ReviewRunManifestError(
                f"unsupported untracked file type while fingerprinting: {relative_path}"
            )
    return "sha256:" + hasher.hexdigest()


def _severity_counts(value: object, review_id: str) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ReviewRunManifestError(f"{review_id} severity_counts must be an object")
    counts: dict[str, int] = {}
    for severity in VALID_SEVERITIES:
        item = value.get(severity, 0)
        if not isinstance(item, int) or item < 0:
            raise ReviewRunManifestError(f"{review_id} invalid count for {severity}")
        counts[severity] = item
    return counts


def _existing_path(repo_root: Path, raw_path: str) -> None:
    path = (repo_root / raw_path).resolve()
    try:
        path.relative_to(repo_root)
    except ValueError as exc:
        raise ReviewRunManifestError(f"path escapes repo: {raw_path}") from exc
    if not path.exists():
        raise ReviewRunManifestError(f"path does not exist: {raw_path}")


def _string(value: object, field: str, path: Path) -> str:
    if not isinstance(value, str):
        raise ReviewRunManifestError(f"{path} field {field} must be a string")
    return value


def _required_string(value: object, field: str, path: Path) -> str:
    string = _string(value, field, path)
    if not string.strip():
        raise ReviewRunManifestError(f"{path} field {field} must not be empty")
    return string


def _string_list(
    value: object,
    field: str,
    path: Path,
    *,
    required: bool = False,
) -> list[str]:
    if value is None and not required:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ReviewRunManifestError(f"{path} field {field} must be a string list")
    if required and not value:
        raise ReviewRunManifestError(f"{path} field {field} must not be empty")
    return cast(list[str], value)


def _int(value: object, field: str, path: Path) -> int:
    if not isinstance(value, int) or value < 0:
        raise ReviewRunManifestError(f"{path} field {field} must be a non-negative integer")
    return value


def _git(repo_root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_bytes(repo_root: Path, args: list[str]) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return completed.stdout


def _display(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())

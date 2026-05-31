"""Validate v0.4 review-run manifest artifacts."""

from __future__ import annotations

import argparse
import json
import re
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
VALID_SEVERITIES = ("critical", "high", "medium", "low", "informational")
FINDING_ID_PATTERN = re.compile(
    r"^(V03-(INT|EXT|DOCS)-[A-Z0-9]+-\d{3}|"
    r"EXT-(PA|FS|HTTP|SE|PR|MCP|UI|REL)-\d{3})$"
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
    current_commit = _git(repo_root, ["rev-parse", "HEAD"])
    if commit != current_commit and commit != current_commit[: len(commit)]:
        raise ReviewRunManifestError(f"{review_id} commit does not match current HEAD")

    dirty = manifest["dirty"]
    if not isinstance(dirty, bool):
        raise ReviewRunManifestError(f"{review_id} dirty must be boolean")
    current_dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty != current_dirty:
        raise ReviewRunManifestError(f"{review_id} dirty state does not match current tree")

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
    }


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


def _display(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())

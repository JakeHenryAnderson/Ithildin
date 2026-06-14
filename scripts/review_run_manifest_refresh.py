"""Refresh ignored review-run manifest commit pointers and dirty flags."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, TypedDict

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


class ReviewRunManifestRefreshError(RuntimeError):
    """Raised when review-run manifests cannot be refreshed safely."""


class ReviewRunManifestRefreshRecord(TypedDict):
    path: str
    review_id: str
    commit_before: str
    commit_after: str
    dirty_before: bool
    dirty_after: bool
    changed: bool


class ReviewRunManifestRefreshSummary(TypedDict):
    runs_dir: str
    repo_root: str
    scanned: int
    changed: int
    refreshed: int
    needs_refresh: bool
    records: list[ReviewRunManifestRefreshRecord]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", default=str(DEFAULT_RUNS_DIR))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        summary = refresh_review_run_manifests(Path(args.runs_dir), ROOT, write=args.write)
    except ReviewRunManifestRefreshError as exc:
        print(f"review-run manifest refresh failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        _print_summary(summary, write=args.write)

    if summary["needs_refresh"] and not args.write:
        return 1
    return 0


def refresh_review_run_manifests(
    runs_dir: Path,
    repo_root: Path,
    *,
    write: bool,
) -> ReviewRunManifestRefreshSummary:
    allowed_root = (repo_root / "var/review-runs").resolve()
    resolved_runs_dir = runs_dir.resolve()
    _ensure_within(resolved_runs_dir, allowed_root, "runs-dir")

    current_commit = _git(repo_root, ["rev-parse", "HEAD"])
    current_dirty = _tracked_dirty(repo_root)

    records: list[ReviewRunManifestRefreshRecord] = []
    scanned = 0
    changed = 0

    if resolved_runs_dir.exists() and not resolved_runs_dir.is_dir():
        raise ReviewRunManifestRefreshError(f"review-runs path is not a directory: {runs_dir}")

    candidate_paths = (
        sorted(resolved_runs_dir.rglob("review-run-*.json")) if resolved_runs_dir.exists() else []
    )
    for path in candidate_paths:
        _ensure_within(path.resolve(), allowed_root, "review-run manifest")
        scanned += 1
        manifest = _read_manifest(path)
        review_id = _required_string(manifest.get("review_id"), "review_id", path)
        _validate_required_fields(manifest, path, review_id)

        commit_before = _required_string(manifest.get("commit"), "commit", path)
        dirty_before = _required_bool(manifest.get("dirty"), "dirty", path, review_id)
        updated_manifest = dict(manifest)
        updated_manifest["commit"] = current_commit
        updated_manifest["dirty"] = current_dirty
        rendered = _render_manifest(updated_manifest)
        changed_here = rendered != path.read_text(encoding="utf-8")
        if changed_here:
            changed += 1
            if write:
                path.write_text(rendered, encoding="utf-8")

        records.append(
            {
                "path": _display(path, repo_root),
                "review_id": review_id,
                "commit_before": commit_before,
                "commit_after": current_commit,
                "dirty_before": dirty_before,
                "dirty_after": current_dirty,
                "changed": changed_here,
            }
        )

    return {
        "runs_dir": _display(resolved_runs_dir, repo_root),
        "repo_root": repo_root.resolve().as_posix(),
        "scanned": scanned,
        "changed": changed,
        "refreshed": changed if write else 0,
        "needs_refresh": changed > 0,
        "records": records,
    }


def _validate_required_fields(manifest: dict[str, Any], path: Path, review_id: str) -> None:
    missing = sorted(field for field in REQUIRED_FIELDS if field not in manifest)
    if missing:
        raise ReviewRunManifestRefreshError(f"{review_id} missing {missing} in {path}")


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReviewRunManifestRefreshError(f"{path} is not valid JSON") from exc
    if not isinstance(raw, dict):
        raise ReviewRunManifestRefreshError(f"{path} must contain a JSON object")
    return raw


def _render_manifest(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def _required_string(value: object, field: str, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewRunManifestRefreshError(f"{path} field {field} must be a non-empty string")
    return value


def _required_bool(value: object, field: str, path: Path, review_id: str) -> bool:
    if not isinstance(value, bool):
        raise ReviewRunManifestRefreshError(f"{review_id} field {field} must be boolean in {path}")
    return value


def _tracked_dirty(repo_root: Path) -> bool:
    output = _git(repo_root, ["status", "--short", "--untracked-files=no"])
    return bool(output.strip())


def _ensure_within(path: Path, root: Path, label: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ReviewRunManifestRefreshError(f"{label} escapes allowed root: {path}") from exc


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


def _print_summary(summary: ReviewRunManifestRefreshSummary, *, write: bool) -> None:
    mode = "refreshed" if write else "would refresh"
    print(
        f"Review-run manifest {mode}: {summary['scanned']} scanned, "
        f"{summary['changed']} needing refresh."
    )
    for record in summary["records"]:
        if record["changed"]:
            action = "updated" if write else "needs refresh"
            print(
                f"- {record['path']}: {action} "
                f"(commit {record['commit_before']} -> {record['commit_after']}, "
                f"dirty {record['dirty_before']} -> {record['dirty_after']})"
            )


if __name__ == "__main__":
    raise SystemExit(main())

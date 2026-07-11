"""Detect stale current-candidate reviews without rewriting executed review provenance."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, TypedDict

if __package__:
    from scripts import review_run_manifest as _review_run_manifest
else:  # Direct execution places scripts/ rather than repo root on sys.path.
    import review_run_manifest as _review_run_manifest  # type: ignore[import-not-found,no-redef]

current_tree_dirty = _review_run_manifest.current_tree_dirty
current_tree_fingerprint = _review_run_manifest.current_tree_fingerprint

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
    binding: str


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
        if args.write:
            print("--write is compatibility-only; executed review manifests are immutable.")
        _print_summary(summary)

    if summary["needs_refresh"]:
        return 1
    return 0


def refresh_review_run_manifests(
    runs_dir: Path,
    repo_root: Path,
    *,
    write: bool,
) -> ReviewRunManifestRefreshSummary:
    _ = write  # Compatibility flag only; executed review evidence is immutable.
    allowed_root = (repo_root / "var/review-runs").resolve()
    resolved_runs_dir = runs_dir.resolve()
    _ensure_within(resolved_runs_dir, allowed_root, "runs-dir")

    current_commit: str | None = None
    current_dirty: bool | None = None
    current_fingerprint: str | None = None

    records: list[ReviewRunManifestRefreshRecord] = []
    scanned = 0
    changed = 0

    if resolved_runs_dir.exists() and not resolved_runs_dir.is_dir():
        raise ReviewRunManifestRefreshError(f"review-runs path is not a directory: {runs_dir}")

    candidate_paths = (
        sorted(resolved_runs_dir.rglob("review-run-*.json")) if resolved_runs_dir.exists() else []
    )
    for path in candidate_paths:
        if path.is_symlink():
            raise ReviewRunManifestRefreshError(
                f"review-run manifest must not be a symlink: {path}"
            )
        _ensure_within(path.resolve(), allowed_root, "review-run manifest")
        scanned += 1
        manifest = _read_manifest(path)
        review_id = _required_string(manifest.get("review_id"), "review_id", path)
        _validate_required_fields(manifest, path, review_id)
        binding = _binding(manifest.get("binding", "historical"), review_id, path)

        commit_before = _required_string(manifest.get("commit"), "commit", path)
        dirty_before = _required_bool(manifest.get("dirty"), "dirty", path, review_id)
        commit_after = commit_before
        dirty_after = dirty_before
        if binding == "current_candidate":
            if current_commit is None:
                current_commit = _git(repo_root, ["rev-parse", "HEAD"])
                current_dirty = current_tree_dirty(repo_root)
                current_fingerprint = current_tree_fingerprint(repo_root)
            assert current_dirty is not None
            assert current_fingerprint is not None
            commit_after = current_commit
            dirty_after = current_dirty
            changed_here = any(
                [
                    commit_before != current_commit,
                    dirty_before != current_dirty,
                    manifest.get("tree_fingerprint") != current_fingerprint,
                ]
            )
        else:
            changed_here = False
        if changed_here:
            changed += 1

        records.append(
            {
                "path": _display(path, repo_root),
                "review_id": review_id,
                "commit_before": commit_before,
                "commit_after": commit_after,
                "dirty_before": dirty_before,
                "dirty_after": dirty_after,
                "changed": changed_here,
                "binding": binding,
            }
        )

    return {
        "runs_dir": _display(resolved_runs_dir, repo_root),
        "repo_root": repo_root.resolve().as_posix(),
        "scanned": scanned,
        "changed": changed,
        "refreshed": 0,
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


def _required_string(value: object, field: str, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewRunManifestRefreshError(f"{path} field {field} must be a non-empty string")
    return value


def _required_bool(value: object, field: str, path: Path, review_id: str) -> bool:
    if not isinstance(value, bool):
        raise ReviewRunManifestRefreshError(f"{review_id} field {field} must be boolean in {path}")
    return value


def _binding(value: object, review_id: str, path: Path) -> str:
    if not isinstance(value, str) or value not in {"historical", "current_candidate"}:
        raise ReviewRunManifestRefreshError(
            f"{review_id} has invalid binding in {path}: {value}"
        )
    return value


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


def _print_summary(summary: ReviewRunManifestRefreshSummary) -> None:
    print(
        f"Review-run manifest checked for staleness: {summary['scanned']} scanned, "
        f"{summary['changed']} stale current-candidate review(s)."
    )
    for record in summary["records"]:
        if record["changed"]:
            action = "stale; create a fresh review record"
            print(
                f"- {record['path']}: {action} [{record['binding']}] "
                f"(commit {record['commit_before']} -> {record['commit_after']}, "
                f"dirty {record['dirty_before']} -> {record['dirty_after']})"
            )


if __name__ == "__main__":
    raise SystemExit(main())

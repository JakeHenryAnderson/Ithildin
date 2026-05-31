"""Check manifest-change review preconditions without adding tool powers."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ithildin_api.registry import ToolRegistry, ToolRegistryError
from ithildin_schemas import JsonObject

MANIFEST_DIR = Path("tool-manifests")
MANIFEST_LOCK_PATH = Path("tool-manifests.lock.json")


@dataclass(frozen=True)
class ManifestChangeReviewResult:
    changed_files: list[str]
    manifest_files_changed: bool
    lock_changed: bool
    tool_count: int
    tool_names: list[str]
    failures: list[str]

    @property
    def passed(self) -> bool:
        return not self.failures

    def as_dict(self) -> JsonObject:
        return cast(
            JsonObject,
            {
                "changed_files": self.changed_files,
                "manifest_files_changed": self.manifest_files_changed,
                "lock_changed": self.lock_changed,
                "tool_count": self.tool_count,
                "tool_names": self.tool_names,
                "passed": self.passed,
                "failures": self.failures,
            },
        )


def evaluate_manifest_change_review(
    *,
    changed_files: list[str],
    tool_names: list[str],
) -> ManifestChangeReviewResult:
    normalized = sorted({path for path in changed_files if path})
    manifest_files_changed = any(_is_manifest_path(path) for path in normalized)
    lock_changed = MANIFEST_LOCK_PATH.as_posix() in normalized
    failures: list[str] = []

    if manifest_files_changed and not lock_changed:
        failures.append("tool manifest changes require tool-manifests.lock.json changes")
    if lock_changed and not manifest_files_changed:
        failures.append("manifest lock changes require an accompanying manifest change")
    if any(
        path.startswith("tool-manifests/") and not _is_manifest_path(path)
        for path in normalized
    ):
        failures.append("tool-manifests changes must be YAML manifests only")

    return ManifestChangeReviewResult(
        changed_files=normalized,
        manifest_files_changed=manifest_files_changed,
        lock_changed=lock_changed,
        tool_count=len(tool_names),
        tool_names=tool_names,
        failures=failures,
    )


def run_review(repo_root: Path) -> ManifestChangeReviewResult:
    registry = ToolRegistry.load(
        repo_root / MANIFEST_DIR,
        lock_path=repo_root / MANIFEST_LOCK_PATH,
        require_lock=True,
    )
    tool_names = sorted(tool.manifest.name for tool in registry.list_tools())
    changed_files = _changed_files(repo_root)
    return evaluate_manifest_change_review(changed_files=changed_files, tool_names=tool_names)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    try:
        result = run_review(repo_root)
    except ToolRegistryError as exc:
        print(f"manifest change review failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    else:
        print(f"Manifest change review: {'passed' if result.passed else 'failed'}")
        print(f"Tools: {result.tool_count}")
        print(f"Changed files: {len(result.changed_files)}")
        for failure in result.failures:
            print(f"- {failure}", file=sys.stderr)
    return 0 if result.passed else 1


def _changed_files(repo_root: Path) -> list[str]:
    completed = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "HEAD",
            "--",
            MANIFEST_DIR.as_posix(),
            MANIFEST_LOCK_PATH.as_posix(),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _is_manifest_path(path: str) -> bool:
    return path.startswith("tool-manifests/") and path.endswith((".yaml", ".yml"))


if __name__ == "__main__":
    raise SystemExit(main())

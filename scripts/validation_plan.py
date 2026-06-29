"""Recommend validation gates for the current or provided file changes."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

RUNTIME_PREFIXES = (
    "apps/api/src/",
    "apps/mcp-server/src/",
    "packages/",
)
UI_PREFIXES = ("apps/ui/",)
DOC_PREFIXES = ("docs/",)
TEST_PREFIXES = ("tests/",)
SCRIPT_PREFIXES = ("scripts/",)
MANIFEST_PREFIXES = ("tool-manifests/",)
POLICY_PREFIXES = ("policies/", "principals/", "workspaces/")
REVIEW_PACKET_PREFIXES = ("var/review-packets/", "var/review-runs/")
CONFIG_FILES = {
    "Makefile",
    "pyproject.toml",
    "uv.lock",
    "package.json",
    "package-lock.json",
    "apps/ui/package.json",
    "apps/ui/package-lock.json",
}
DOC_FILES = {"README.md", "AGENTS.md"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="changed files to classify")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    files = args.files or changed_files(ROOT)
    report = build_report(files)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0


def build_report(files: list[str]) -> dict[str, Any]:
    normalized = sorted({_normalize_path(path) for path in files if path.strip()})
    categories = sorted({_classify(path) for path in normalized})
    commands = _commands_for_categories(categories)
    return {
        "schema_version": "1",
        "files": normalized,
        "file_count": len(normalized),
        "categories": categories,
        "recommended_commands": commands,
        "full_release_gate_required": _requires_full_release(categories),
        "review_candidate_required": "review_packet" in categories,
        "notes": _notes_for_categories(categories),
    }


def changed_files(repo_root: Path) -> list[str]:
    output = subprocess.check_output(
        ["git", "status", "--short"],
        cwd=repo_root,
        text=True,
    )
    files: list[str] = []
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin validation plan",
        f"file_count: {report['file_count']}",
        "categories: " + (", ".join(report["categories"]) or "none"),
        f"full_release_gate_required: {str(report['full_release_gate_required']).lower()}",
        f"review_candidate_required: {str(report['review_candidate_required']).lower()}",
        "recommended_commands:",
    ]
    lines.extend(f"- {command}" for command in report["recommended_commands"])
    if report["notes"]:
        lines.append("notes:")
        lines.extend(f"- {note}" for note in report["notes"])
    if report["files"]:
        lines.append("files:")
        lines.extend(f"- {path}" for path in report["files"])
    return "\n".join(lines)


def _classify(path: str) -> str:
    if path.startswith(REVIEW_PACKET_PREFIXES):
        return "review_packet"
    if path.startswith(MANIFEST_PREFIXES) or path == "tool-manifests.lock.json":
        return "manifest"
    if path.startswith(POLICY_PREFIXES):
        return "policy_registry"
    if path.startswith(RUNTIME_PREFIXES):
        return "runtime"
    if path.startswith(UI_PREFIXES):
        return "ui"
    if path.startswith(TEST_PREFIXES):
        return "tests"
    if path.startswith(SCRIPT_PREFIXES):
        return "scripts"
    if path.startswith(DOC_PREFIXES) or path in DOC_FILES:
        return "docs"
    if path in CONFIG_FILES:
        return "config"
    return "other"


def _commands_for_categories(categories: list[str]) -> list[str]:
    if not categories:
        return ["make quick-check"]

    commands = ["make quick-check"]
    if any(category in categories for category in ["docs", "scripts", "tests", "config"]):
        commands.append("make readiness-check")
    if "manifest" in categories:
        commands.extend(["make manifest-lock-check", "make tool-surface-invariant-gate"])
    if "policy_registry" in categories:
        commands.extend(["make policy-test", "make policy-parity"])
    if "ui" in categories:
        commands.extend(
            [
                "npm run test --prefix apps/ui -- --run",
                "npm run build --prefix apps/ui",
            ]
        )
    if "runtime" in categories:
        commands.extend(["make test", "make release-check"])
    elif _requires_full_release(categories):
        commands.append("make release-check")
    if "review_packet" in categories:
        commands.append("make review-candidate")
    return _dedupe(commands)


def _requires_full_release(categories: list[str]) -> bool:
    release_categories = {"runtime", "manifest", "policy_registry", "ui", "review_packet"}
    return bool(release_categories.intersection(categories))


def _notes_for_categories(categories: list[str]) -> list[str]:
    notes: list[str] = []
    if "runtime" in categories:
        notes.append("Runtime changes need focused subsystem tests before the full release gate.")
    if "manifest" in categories:
        notes.append("Manifest changes must intentionally refresh and verify the manifest lock.")
    if "policy_registry" in categories:
        notes.append("Policy or registry changes need policy parity and fail-closed coverage.")
    if "ui" in categories:
        notes.append(
            "UI changes need UI interaction/build checks plus relevant API contract tests."
        )
    if "review_packet" in categories:
        notes.append(
            "Generated packet changes should be verified with review-candidate before handoff."
        )
    if categories and not _requires_full_release(categories):
        notes.append("Fast gates are development evidence, not release-readiness proof.")
    return notes


def _dedupe(commands: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for command in commands:
        if command in seen:
            continue
        seen.add(command)
        deduped.append(command)
    return deduped


def _normalize_path(path: str) -> str:
    return path.strip().removeprefix("./")


if __name__ == "__main__":
    raise SystemExit(main())

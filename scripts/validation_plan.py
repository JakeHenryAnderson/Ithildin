"""Recommend validation gates for the current or provided file changes."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import time
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
    parser.add_argument(
        "--run",
        action="store_true",
        help="run the recommended commands after building the plan",
    )
    parser.add_argument(
        "--include-release",
        action="store_true",
        help=(
            "include slow release/review gates in the executable command plan; "
            "by default they are reported as deferred handoff commands"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=900.0,
        help="per-command timeout in seconds when --run is used",
    )
    args = parser.parse_args()

    files = args.files or changed_files(ROOT)
    report = build_report(files, include_release=args.include_release)
    if args.run:
        report["execution"] = run_commands(
            report["recommended_commands"],
            timeout_seconds=args.timeout,
        )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    execution = report.get("execution")
    if execution and not execution["valid"]:
        return 1
    return 0


def build_report(files: list[str], *, include_release: bool = False) -> dict[str, Any]:
    normalized = sorted({_normalize_path(path) for path in files if path.strip()})
    categories = sorted({_classify(path) for path in normalized})
    commands = _commands_for_categories(categories, normalized)
    slow_commands = _slow_commands_for_categories(categories)
    recommended_commands = commands + slow_commands if include_release else commands
    return {
        "schema_version": "1",
        "files": normalized,
        "file_count": len(normalized),
        "categories": categories,
        "recommended_commands": recommended_commands,
        "development_commands": commands,
        "deferred_handoff_commands": [] if include_release else slow_commands,
        "include_release": include_release,
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
        f"include_release: {str(report['include_release']).lower()}",
        f"full_release_gate_required: {str(report['full_release_gate_required']).lower()}",
        f"review_candidate_required: {str(report['review_candidate_required']).lower()}",
        "recommended_commands:",
    ]
    lines.extend(f"- {command}" for command in report["recommended_commands"])
    if report["deferred_handoff_commands"]:
        lines.append("deferred_handoff_commands:")
        lines.extend(f"- {command}" for command in report["deferred_handoff_commands"])
    if report["notes"]:
        lines.append("notes:")
        lines.extend(f"- {note}" for note in report["notes"])
    if report["files"]:
        lines.append("files:")
        lines.extend(f"- {path}" for path in report["files"])
    if "execution" in report:
        execution = report["execution"]
        lines.extend(
            [
                "execution:",
                f"- valid: {str(execution['valid']).lower()}",
                f"- total_elapsed_seconds: {execution['total_elapsed_seconds']}",
            ]
        )
        for result in execution["results"]:
            lines.append(
                "- "
                f"{result['command']} "
                f"returncode={result['returncode']} "
                f"elapsed_seconds={result['elapsed_seconds']}"
            )
            if result["returncode"] != 0 and result["output_tail"]:
                lines.append("  output_tail:")
                lines.extend(f"  {line}" for line in result["output_tail"].splitlines())
    return "\n".join(lines)


def run_commands(commands: list[str], *, timeout_seconds: float) -> dict[str, Any]:
    results = [
        _run_command(command, timeout_seconds=timeout_seconds)
        for command in commands
    ]
    return {
        "valid": all(result["returncode"] == 0 for result in results),
        "command_count": len(results),
        "total_elapsed_seconds": round(
            sum(result["elapsed_seconds"] for result in results),
            3,
        ),
        "results": results,
    }


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


def _commands_for_categories(categories: list[str], files: list[str]) -> list[str]:
    if not categories:
        return ["make quick-check"]

    if categories == ["docs"]:
        return ["make docs-check"]

    needs_readiness = any(
        category in categories for category in ["docs", "scripts", "tests", "config"]
    )
    commands = ["make readiness-check" if needs_readiness else "make quick-check"]
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
        commands.append("make runtime-check")
    commands.extend(_changed_test_commands(files))
    return _dedupe(commands)


def _slow_commands_for_categories(categories: list[str]) -> list[str]:
    commands: list[str] = []
    if _requires_full_release(categories):
        commands.append("make release-check")
    if "review_packet" in categories:
        commands.append("make review-candidate")
    return commands


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
    if "tests" in categories:
        notes.append(
            "Changed Python test files are run directly as focused evidence; broaden to "
            "test-fast or release-check before checkpoint claims when risk warrants it."
        )
    if categories == ["docs"]:
        notes.append(
            "Pure docs changes can use docs-check; mixed docs/script/config changes still need "
            "readiness-check."
        )
    if _requires_full_release(categories):
        notes.append(
            "Full release/review gates are deferred by default; use --include-release for a "
            "handoff-ready run."
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


def _changed_test_commands(files: list[str]) -> list[str]:
    test_files = [
        path
        for path in files
        if path.startswith("tests/")
        and path.endswith(".py")
        and "::" not in path
    ]
    if not test_files:
        return []
    quoted_paths = " ".join(shlex.quote(path) for path in test_files)
    return [f'uv run pytest {quoted_paths} -m "not slow_packet" -q']


def _normalize_path(path: str) -> str:
    return path.strip().removeprefix("./")


def _run_command(command: str, *, timeout_seconds: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            shlex.split(command),
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            check=False,
        )
        elapsed = time.monotonic() - started
        return {
            "command": command,
            "returncode": completed.returncode,
            "elapsed_seconds": round(elapsed, 3),
            "timed_out": False,
            "output_tail": _tail(completed.stdout),
        }
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        return {
            "command": command,
            "returncode": 124,
            "elapsed_seconds": round(elapsed, 3),
            "timed_out": True,
            "output_tail": _tail(output),
        }


def _tail(output: str, *, max_lines: int = 20) -> str:
    return "\n".join(output.splitlines()[-max_lines:])


if __name__ == "__main__":
    raise SystemExit(main())

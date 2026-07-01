"""Run the smallest current-state progress check for the development loop."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DIRTY_COMMAND = "make dev-check"
CLEAN_COMMAND = "make handoff-dry-run"
DEFERRED_PROOF_COMMANDS = ["make release-check", "make review-candidate"]
OUTPUT_TAIL_LINES = 80


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the selected command without running it",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=1800.0,
        help="timeout in seconds for the selected command",
    )
    args = parser.parse_args()

    report = build_report(ROOT, dry_run=args.dry_run, timeout_seconds=args.timeout)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(
    repo_root: Path,
    *,
    dry_run: bool = False,
    timeout_seconds: float = 1800.0,
) -> dict[str, Any]:
    dirty_files = _dirty_files(repo_root)
    dirty = bool(dirty_files)
    command = DIRTY_COMMAND if dirty else CLEAN_COMMAND
    mode = "dirty_tree_development_gate" if dirty else "clean_tree_handoff_sanity"
    report: dict[str, Any] = {
        "schema_version": "1",
        "valid": True,
        "repo_root": str(repo_root),
        "git_commit": _git(repo_root, ["rev-parse", "HEAD"]),
        "git_dirty": dirty,
        "dirty_file_count": len(dirty_files),
        "dirty_files": dirty_files,
        "mode": mode,
        "selected_command": command,
        "dry_run": dry_run,
        "release_proof": False,
        "handoff_proof": False,
        "deferred_proof_commands": DEFERRED_PROOF_COMMANDS,
        "notes": _notes(dirty),
        "execution": None,
    }
    if dry_run:
        return report

    execution = _run(command, repo_root=repo_root, timeout_seconds=timeout_seconds)
    report["execution"] = execution
    report["valid"] = execution["returncode"] == 0
    return report


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin progress check",
        f"valid: {str(report['valid']).lower()}",
        f"git_commit: {report['git_commit']}",
        f"git_dirty: {str(report['git_dirty']).lower()}",
        f"dirty_file_count: {report['dirty_file_count']}",
        f"mode: {report['mode']}",
        f"selected_command: {report['selected_command']}",
        f"dry_run: {str(report['dry_run']).lower()}",
        f"release_proof: {str(report['release_proof']).lower()}",
        f"handoff_proof: {str(report['handoff_proof']).lower()}",
        "deferred_proof_commands:",
    ]
    lines.extend(f"- {command}" for command in report["deferred_proof_commands"])
    lines.append("notes:")
    lines.extend(f"- {note}" for note in report["notes"])
    if report["dirty_files"]:
        lines.append("dirty_files:")
        lines.extend(f"- {path}" for path in report["dirty_files"][:40])
        omitted = len(report["dirty_files"]) - 40
        if omitted > 0:
            lines.append(f"- ... {omitted} more")
    execution = report.get("execution")
    if execution:
        lines.extend(
            [
                "execution:",
                f"- command: {execution['command']}",
                f"- returncode: {execution['returncode']}",
                f"- elapsed_seconds: {execution['elapsed_seconds']}",
            ]
        )
        if execution["returncode"] != 0 and execution["output_tail"]:
            lines.append("output_tail:")
            lines.extend(execution["output_tail"].splitlines())
    return "\n".join(lines)


def _dirty_files(repo_root: Path) -> list[str]:
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


def _notes(dirty: bool) -> list[str]:
    if dirty:
        return [
            "Dirty tree: run the dirty-file-aware development gate first.",
            "This is not release proof and does not refresh reviewer handoff packets.",
            "Run deferred proof commands before release, checkpoint, or handoff claims.",
        ]
    return [
        "Clean tree: run the cheap current-artifact handoff sanity path.",
        "This checks artifact freshness and send/readiness routing without rebuilding the "
        "full packet.",
        "Run deferred proof commands before release, checkpoint, or handoff claims.",
    ]


def _run(command: str, *, repo_root: Path, timeout_seconds: float) -> dict[str, Any]:
    start = time.monotonic()
    result = subprocess.run(
        command,
        cwd=repo_root,
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
    )
    elapsed = round(time.monotonic() - start, 3)
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    return {
        "command": command,
        "returncode": result.returncode,
        "elapsed_seconds": elapsed,
        "output_tail": _tail(output),
    }


def _tail(text: str) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-OUTPUT_TAIL_LINES:])


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

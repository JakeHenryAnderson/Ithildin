"""Summarize the latest captured release-check transcript without rerunning it."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRANSCRIPT = ROOT / "var/review-packets/v3/review-candidate-release-check.txt"
DEFAULT_TAIL_LINES = 40
COMMAND_PREFIXES = (
    "uv run ",
    "npm run ",
    "make ",
    "/Library/Developer/CommandLineTools/usr/bin/make ",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transcript",
        default=str(DEFAULT_TRANSCRIPT.relative_to(ROOT)),
        help="release-check transcript path relative to the repo root or absolute",
    )
    parser.add_argument("--tail-lines", type=int, default=DEFAULT_TAIL_LINES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    transcript_path = Path(args.transcript)
    if not transcript_path.is_absolute():
        transcript_path = ROOT / transcript_path
    report = build_report(transcript_path, tail_lines=args.tail_lines)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(path: Path, *, tail_lines: int = DEFAULT_TAIL_LINES) -> dict[str, Any]:
    failures: list[str] = []
    if not path.exists():
        return {
            "schema_version": "1",
            "valid": False,
            "failures": [f"release-check transcript is missing: {_display_path(path)}"],
            "transcript_path": _display_path(path),
            "exists": False,
            "passed": False,
            "returncode": None,
            "git_commit": None,
            "git_dirty": None,
            "line_count": 0,
            "command_count": 0,
            "command_prefix_counts": {},
            "script_command_count": 0,
            "pytest_invocation_count": 0,
            "npm_invocation_count": 0,
            "make_invocation_count": 0,
            "last_observed_command": None,
            "tail": "",
            "notes": _notes(),
        }

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    returncode = _last_returncode(lines)
    git_commit = _first_value(lines, "git_commit=")
    git_dirty = _first_value(lines, "git_dirty=")
    commands = _commands(lines)
    prefix_counts = Counter(_command_prefix(command) for command in commands)
    if returncode is None:
        failures.append("release-check transcript has no returncode line")
    if git_commit is None:
        failures.append("release-check transcript has no git_commit line")
    if git_dirty is None:
        failures.append("release-check transcript has no git_dirty line")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "transcript_path": _display_path(path),
        "exists": True,
        "passed": returncode == 0,
        "returncode": returncode,
        "git_commit": git_commit,
        "git_dirty": _bool_value(git_dirty),
        "line_count": len(lines),
        "command_count": len(commands),
        "command_prefix_counts": dict(sorted(prefix_counts.items())),
        "script_command_count": sum(
            1 for command in commands if command.startswith("uv run python scripts/")
        ),
        "pytest_invocation_count": sum("pytest" in command for command in commands),
        "npm_invocation_count": sum(command.startswith("npm run ") for command in commands),
        "make_invocation_count": sum(
            command.startswith("make ")
            or command.startswith("/Library/Developer/CommandLineTools/usr/bin/make ")
            for command in commands
        ),
        "last_observed_command": commands[-1] if commands else None,
        "tail": "\n".join(lines[-max(tail_lines, 0) :]),
        "notes": _notes(),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin release-check transcript summary",
        f"valid: {str(report['valid']).lower()}",
        f"transcript_path: {report['transcript_path']}",
        f"exists: {str(report['exists']).lower()}",
        f"passed: {str(report['passed']).lower()}",
        f"returncode: {report['returncode']}",
        f"git_commit: {report['git_commit']}",
        f"git_dirty: {report['git_dirty']}",
        f"line_count: {report['line_count']}",
        f"command_count: {report['command_count']}",
        f"script_command_count: {report['script_command_count']}",
        f"pytest_invocation_count: {report['pytest_invocation_count']}",
        f"npm_invocation_count: {report['npm_invocation_count']}",
        f"make_invocation_count: {report['make_invocation_count']}",
        f"last_observed_command: {report['last_observed_command']}",
        "command_prefix_counts:",
    ]
    prefix_counts = report["command_prefix_counts"]
    if prefix_counts:
        lines.extend(f"- {prefix}: {count}" for prefix, count in prefix_counts.items())
    else:
        lines.append("- none")
    lines.append("notes:")
    lines.extend(f"- {note}" for note in report["notes"])
    if report["tail"]:
        lines.append("tail:")
        lines.extend(f"  {line}" for line in str(report["tail"]).splitlines())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _commands(lines: list[str]) -> list[str]:
    commands: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("$ "):
            stripped = stripped[2:]
        if stripped.startswith(COMMAND_PREFIXES):
            commands.append(stripped)
    return commands


def _command_prefix(command: str) -> str:
    if command.startswith("uv run python scripts/"):
        return "uv_python_scripts"
    if command.startswith("uv run pytest"):
        return "uv_pytest"
    if command.startswith("uv run ruff"):
        return "uv_ruff"
    if command.startswith("uv run mypy"):
        return "uv_mypy"
    if command.startswith("npm run "):
        return "npm"
    if command.startswith("make ") or command.startswith(
        "/Library/Developer/CommandLineTools/usr/bin/make "
    ):
        return "make"
    return "other"


def _last_returncode(lines: list[str]) -> int | None:
    for line in reversed(lines):
        match = re.fullmatch(r"returncode=(\d+)", line.strip())
        if match:
            return int(match.group(1))
    return None


def _first_value(lines: list[str], prefix: str) -> str | None:
    for line in lines:
        if line.startswith(prefix):
            return line.removeprefix(prefix)
    return None


def _bool_value(value: str | None) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _notes() -> list[str]:
    return [
        "This command parses an existing transcript only; it does not rerun release-check.",
        "Use it after a long release transcript to identify the last observed subcommand.",
        "It is diagnostic evidence, not release proof.",
    ]


if __name__ == "__main__":
    raise SystemExit(main())

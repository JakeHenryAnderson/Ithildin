"""Time selected validation gate profiles without changing release semantics."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

PROFILES: dict[str, list[str]] = {
    "fast": ["make smart-check"],
    "quick": ["make quick-check"],
    "readiness": ["make readiness-check"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default="fast",
        help="validation profile to time",
    )
    parser.add_argument(
        "--command",
        action="append",
        default=[],
        help="explicit command to time; may be repeated and overrides --profile",
    )
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    commands = args.command or PROFILES[args.profile]
    report = build_report(commands, timeout_seconds=args.timeout, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(
    commands: list[str],
    *,
    timeout_seconds: float = 900.0,
    dry_run: bool = False,
) -> dict[str, Any]:
    results = [
        _run_command(command, timeout_seconds=timeout_seconds, dry_run=dry_run)
        for command in commands
    ]
    return {
        "schema_version": "1",
        "valid": all(result["returncode"] == 0 for result in results),
        "dry_run": dry_run,
        "command_count": len(results),
        "total_elapsed_seconds": round(
            sum(result["elapsed_seconds"] for result in results),
            3,
        ),
        "results": results,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin validation timing",
        f"valid: {str(report['valid']).lower()}",
        f"dry_run: {str(report['dry_run']).lower()}",
        f"command_count: {report['command_count']}",
        f"total_elapsed_seconds: {report['total_elapsed_seconds']}",
        "results:",
    ]
    for result in report["results"]:
        lines.append(
            "- "
            f"{result['command']} "
            f"returncode={result['returncode']} "
            f"elapsed_seconds={result['elapsed_seconds']}"
        )
    return "\n".join(lines)


def _run_command(
    command: str,
    *,
    timeout_seconds: float,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {
            "command": command,
            "argv": shlex.split(command),
            "returncode": 0,
            "elapsed_seconds": 0.0,
            "timed_out": False,
            "output_tail": "",
        }

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
            "argv": shlex.split(command),
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
            "argv": shlex.split(command),
            "returncode": 124,
            "elapsed_seconds": round(elapsed, 3),
            "timed_out": True,
            "output_tail": _tail(output),
        }


def _tail(output: str, *, max_lines: int = 20) -> str:
    return "\n".join(output.splitlines()[-max_lines:])


if __name__ == "__main__":
    raise SystemExit(main())

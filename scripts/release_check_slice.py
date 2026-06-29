"""Plan or run a category slice of the release-check target graph."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import release_check_profile

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--category",
        help="release-check profile category to slice; omit to list categories",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="execute the selected slice with make; default is plan-only",
    )
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(
        ROOT,
        category=args.category,
        run=args.run,
        timeout_seconds=args.timeout,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(
    repo_root: Path,
    *,
    category: str | None = None,
    run: bool = False,
    timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    profile = release_check_profile.build_report(repo_root)
    category_targets = {
        row["category"]: row["targets"]
        for row in profile["categories"]
        if isinstance(row["category"], str) and isinstance(row["targets"], list)
    }
    failures: list[str] = []
    selected_targets: list[str] = []
    if profile["valid"] is not True:
        failures.append("release-check profile is not valid")
    if category is not None:
        selected_targets = list(category_targets.get(category, []))
        if not selected_targets:
            failures.append(f"unknown or empty release-check category: {category}")
    execution: dict[str, Any] | None = None
    if run and selected_targets and not failures:
        execution = _run_slice(selected_targets, timeout_seconds=timeout_seconds)
        if execution["returncode"] != 0:
            failures.append(f"release-check slice failed: {category}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "run_requested": run,
        "selected_category": category,
        "available_categories": sorted(category_targets),
        "selected_target_count": len(selected_targets),
        "selected_targets": selected_targets,
        "execution": execution,
        "notes": [
            "Plan-only by default; pass --run to execute selected targets.",
            "A slice is focused development evidence, not full release proof.",
            "Run make release-check before release, external handoff, or major checkpoint claims.",
        ],
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin release-check slice",
        f"valid: {str(report['valid']).lower()}",
        f"run_requested: {str(report['run_requested']).lower()}",
        f"selected_category: {report['selected_category']}",
        f"selected_target_count: {report['selected_target_count']}",
        "available_categories: " + ", ".join(report["available_categories"]),
    ]
    if report["selected_targets"]:
        lines.append("selected_targets:")
        lines.extend(f"- {target}" for target in report["selected_targets"])
    if report["execution"]:
        execution = report["execution"]
        lines.extend(
            [
                "execution:",
                f"- command: {execution['command']}",
                f"- returncode: {execution['returncode']}",
                f"- elapsed_seconds: {execution['elapsed_seconds']}",
                f"- timed_out: {str(execution['timed_out']).lower()}",
            ]
        )
        if execution["returncode"] != 0 and execution["output_tail"]:
            lines.append("  output_tail:")
            lines.extend(f"  {line}" for line in execution["output_tail"].splitlines())
    if report["notes"]:
        lines.append("notes:")
        lines.extend(f"- {note}" for note in report["notes"])
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _run_slice(targets: list[str], *, timeout_seconds: float) -> dict[str, Any]:
    argv = ["make", *targets]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            check=False,
        )
        elapsed = time.monotonic() - started
        return {
            "command": shlex.join(argv),
            "returncode": completed.returncode,
            "elapsed_seconds": round(elapsed, 3),
            "timed_out": False,
            "output_tail": _tail(completed.stdout),
        }
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        return {
            "command": shlex.join(argv),
            "returncode": 124,
            "elapsed_seconds": round(elapsed, 3),
            "timed_out": True,
            "output_tail": _tail(output),
        }


def _tail(output: str, *, max_lines: int = 20) -> str:
    return "\n".join(output.splitlines()[-max_lines:])


if __name__ == "__main__":
    raise SystemExit(main())

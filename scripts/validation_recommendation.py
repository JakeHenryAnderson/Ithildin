"""Recommend the next validation command set without running it."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import validation_decision  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="changed files to classify")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(args.files)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(files: list[str] | None = None) -> dict[str, Any]:
    decision = validation_decision.build_report(files)
    return {
        "schema_version": "1",
        "valid": decision["valid"],
        "failures": decision["failures"],
        "git_commit": decision["git_commit"],
        "git_dirty": decision["git_dirty"],
        "file_count": decision["file_count"],
        "categories": decision["categories"],
        "recommended_mode": decision["recommended_mode"],
        "recommended_commands": decision["next_development_commands"],
        "deferred_handoff_commands": decision["deferred_handoff_commands"],
        "release_slice_commands": decision["release_slice_commands"],
        "release_or_handoff_required": decision["release_or_handoff_required"],
        "release_proof": False,
        "handoff_proof": False,
        "notes": [
            *decision["notes"],
            "This recommendation does not run commands and is not release or handoff proof.",
        ],
        "files": decision["files"],
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin validation recommendation",
        f"valid: {str(report['valid']).lower()}",
        f"git_commit: {report['git_commit']}",
        f"git_dirty: {str(report['git_dirty']).lower()}",
        f"file_count: {report['file_count']}",
        "categories: " + (", ".join(report["categories"]) or "none"),
        f"recommended_mode: {report['recommended_mode']}",
        f"release_or_handoff_required: {str(report['release_or_handoff_required']).lower()}",
        f"release_proof: {str(report['release_proof']).lower()}",
        f"handoff_proof: {str(report['handoff_proof']).lower()}",
        "recommended_commands:",
    ]
    lines.extend(f"- {command}" for command in report["recommended_commands"])
    if report["deferred_handoff_commands"]:
        lines.append("deferred_handoff_commands:")
        lines.extend(f"- {command}" for command in report["deferred_handoff_commands"])
    if report["release_slice_commands"]:
        lines.append("release_slice_commands:")
        lines.extend(f"- {command}" for command in report["release_slice_commands"])
    lines.append("notes:")
    lines.extend(f"- {note}" for note in report["notes"])
    if report["files"]:
        lines.append("files:")
        lines.extend(f"- {path}" for path in report["files"])
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

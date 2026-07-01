"""Print the compact roadmap status from the technical MVP execution board."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import technical_mvp_execution_board  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = technical_mvp_execution_board.build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_render(report))
    return 0 if report["valid"] else 1


def _render(report: dict[str, object]) -> str:
    lines = [
        "Ithildin roadmap status",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"latest_implemented_tool: {report['latest_implemented_tool']}",
        f"selected_capability: {report['selected_capability']}",
        f"technical_mvp_state: {report['technical_mvp_state']}",
        f"enterprise_next_action: {report['enterprise_next_action']}",
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        f"technical_milestones: {report['technical_milestone_count']}",
        f"enterprise_milestones: {report['enterprise_milestone_count']}",
        "current_send_set: " + ", ".join(report.get("current_send_set") or []),
        "next:",
        "- send ERG-003 and ERG-002 if not already sent",
        "- fill and validate the send receipt after the human send step",
        "- wait for responses before response normalization or lane closure",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

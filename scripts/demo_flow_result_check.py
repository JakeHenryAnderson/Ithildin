"""Validate an optional secret-free DEMO_FLOW_RESULT.md artifact."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

DEFAULT_RESULT = Path("var/review-packets/v3/operator-workbench/DEMO_FLOW_RESULT.md")
FORBIDDEN = [
    "PRIVATE KEY",
    "ITHILDIN_ADMIN_TOKEN=",
    "demo-secret-token",
    "BEGIN OPENSSH",
    "diff --git",
    "response body:",
]
REQUIRED_PHRASES = [
    "# Demo Flow Result",
    "scenario: `guided_local_demo`",
    "demo_step: `mediated_patch_flow`",
    "proposal_id:",
    "approval_id:",
    "candidate_run_ids:",
    "audit_verification_valid:",
    "DEMO_RESET_GUIDE.md",
    "does not prove OS isolation",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(args.path)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(path: Path = DEFAULT_RESULT) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": "1",
            "valid": True,
            "status": "not_run",
            "result_present": False,
            "path": path.as_posix(),
            "failures": [],
        }

    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"result missing phrase: {phrase}")
    for forbidden in FORBIDDEN:
        if forbidden in text:
            failures.append(f"result contains forbidden content: {forbidden}")
    if not re.search(r"proposal_id: `patch_[a-zA-Z0-9_]+`", text):
        failures.append("result missing patch proposal id")
    if not re.search(r"approval_id: `appr_[a-zA-Z0-9_]+`", text):
        failures.append("result missing approval id")
    if "audit_verification_valid: `true`" not in text:
        failures.append("result does not record a valid audit verification")

    return {
        "schema_version": "1",
        "valid": not failures,
        "status": "checked" if not failures else "failed",
        "result_present": True,
        "path": path.as_posix(),
        "failures": failures,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin demo-flow result check",
        f"valid: {str(report['valid']).lower()}",
        f"status: {report['status']}",
        f"result_present: {str(report['result_present']).lower()}",
        f"path: {report['path']}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

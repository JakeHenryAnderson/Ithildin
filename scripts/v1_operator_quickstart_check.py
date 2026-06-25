"""Validate the v1.0 operator quickstart and demo path wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
QUICKSTART_DOC = ROOT / "docs/codex/v1.0-operator-quickstart.md"

REQUIRED_COMMANDS = [
    "make v1-rc-status-check",
    "make live-demo-preflight",
    "make demo-readiness-summary",
    "make demo-seed",
    "make compose-up",
    "make compose-smoke",
    "make demo-flow",
    "make live-demo-status",
    "make demo-evidence-packet",
    "make workbench-evidence-packet",
    "make review-candidate",
    "make compose-down",
]

REQUIRED_PHRASES = [
    "Status: local-preview operator quickstart for the v1.0 RC path.",
    "Current governed tool count: `24`",
    "Zero-To-One Command Path",
    "Manual Review Steps",
    "Evidence Reading Order",
    "If Compose Is Unavailable",
    "What This Demonstrates",
    "What This Does Not Demonstrate",
    "http://127.0.0.1:5173",
    "uv run python -m ithildin_mcp_server",
    "WORKBENCH_DEMO_INDEX.md",
    "DEMO_READINESS_SUMMARY.md",
    "LIVE_DEMO_INDEX.md",
    "LIVE_DEMO_EVIDENCE_SUMMARY.md",
    "does not prove production deployment safety",
]

FORBIDDEN_PHRASES = [
    "production-ready",
    "compliance-grade audit",
    "tamper-proof audit",
    "secure sandbox",
    "safe arbitrary tool use",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_rel = QUICKSTART_DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)

    text = ""
    if not doc_path.exists():
        failures.append("v1.0 operator quickstart doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 operator quickstart is missing phrase: {phrase}")
        for command in REQUIRED_COMMANDS:
            if command not in text:
                failures.append(f"v1.0 operator quickstart is missing command: {command}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                failures.append(f"v1.0 operator quickstart contains forbidden phrase: {phrase}")

    for target in [
        "live-demo-preflight:",
        "demo-readiness-summary:",
        "demo-seed:",
        "compose-up:",
        "compose-smoke:",
        "demo-flow:",
        "live-demo-status:",
        "demo-evidence-packet:",
        "workbench-evidence-packet:",
        "review-candidate:",
        "compose-down:",
        "v1-operator-quickstart-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "v1-operator-quickstart-check" not in release_check_body:
        failures.append("v1-operator-quickstart-check is missing from release-check")
    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 operator quickstart is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 operator quickstart is missing from docs-site inputs")
    if "v1.0 operator quickstart" not in readme:
        failures.append("README is missing v1.0 operator quickstart reference")
    if tool_surface.get("tool_count") != 24:
        failures.append("tool surface tool count is not 24")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "quickstart_doc": doc_rel,
        "tool_count": tool_surface.get("tool_count"),
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "run_control_behavior_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_behavior_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 operator quickstart check",
        f"valid: {str(report['valid']).lower()}",
        f"quickstart_doc: {report['quickstart_doc']}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "runtime_changes_allowed: false",
        "new_power_classes_allowed: false",
        "run_control_behavior_allowed: false",
        "sandbox_orchestration_allowed: false",
        "siem_adapter_behavior_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

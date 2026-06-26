"""Validate the v1.0 operator trial checklist and wiring."""

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
CHECKLIST_DOC = ROOT / "docs/codex/v1.0-operator-trial-checklist.md"

REQUIRED_COMMANDS = [
    "make v1-rc-status-check",
    "make v1-progress-assessment",
    "make live-demo-preflight",
    "make demo-readiness-summary",
    "make demo-seed",
    "make compose-up",
    "make compose-smoke",
    "make compose-down",
    "make demo-workbench",
    "make signed-evidence-demo",
    "make negative-review-transcripts",
    "make live-demo-status",
    "make demo-evidence-packet",
    "make workbench-evidence-packet",
    "make release-check",
    "make review-candidate",
    "git status --short",
]

REQUIRED_PHRASES = [
    "Status: local-preview operator trial checklist for the v1.0 RC path.",
    "Trial Metadata",
    "Governed tool count | `24`",
    "Latest implemented tool | `sandbox.artifact.write_text`",
    "Selected next capability | `not selected`",
    "Required Preflight",
    "Optional Compose Path",
    "Non-Compose Evidence Path",
    "Final Handoff Gate",
    "Trial Pass Criteria",
    "Trial Fail Criteria",
    "What The Trial Does Not Prove",
    "http://127.0.0.1:5173",
    "packet redaction scan reports `findings: 0`",
    "enterprise next-review handoff exists",
    "Compose skipped",
]

BLOCKED_PHRASES = [
    "production readiness",
    "sandbox isolation",
    "SIEM custody",
    "compliance automation",
    "production identity",
    "public/security-product positioning",
    "live VM/container control",
    "Mission Control execution",
    "trusted-host promotion",
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
    doc_rel = CHECKLIST_DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    packet_script = (repo_root / "scripts/v1_rc_packet.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)

    if not doc_path.exists():
        failures.append("v1.0 operator trial checklist doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(
                    f"v1.0 operator trial checklist is missing phrase: {phrase}"
                )
        for command in REQUIRED_COMMANDS:
            if command not in text:
                failures.append(
                    f"v1.0 operator trial checklist is missing command: {command}"
                )
        for phrase in BLOCKED_PHRASES:
            if phrase not in text:
                failures.append(
                    f"v1.0 operator trial checklist is missing blocked phrase: {phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                failures.append(
                    f"v1.0 operator trial checklist contains forbidden phrase: {phrase}"
                )

    if tool_surface.get("tool_count") != 24:
        failures.append("tool surface tool count is not 24")
    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 operator trial checklist is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 operator trial checklist is missing from docs-site inputs")
    if doc_rel not in packet_script:
        failures.append("v1.0 RC packet is missing the operator trial checklist")
    if "v1-operator-trial-checklist-check:" not in makefile:
        failures.append("Make target is missing: v1-operator-trial-checklist-check")
    if "v1-operator-trial-checklist-check" not in release_check_body:
        failures.append("v1-operator-trial-checklist-check is missing from release-check")
    if "make v1-operator-trial-checklist-check" not in readme:
        failures.append("README is missing operator trial checklist command")
    if doc_rel not in readme:
        failures.append("README is missing operator trial checklist doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "checklist_doc": doc_rel,
        "tool_count": tool_surface.get("tool_count"),
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "run_control_behavior_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_behavior_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 operator trial checklist check",
        f"valid: {str(report['valid']).lower()}",
        f"checklist_doc: {report['checklist_doc']}",
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

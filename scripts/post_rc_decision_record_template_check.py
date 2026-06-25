"""Validate the post-RC decision record template and release wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import post_rc_decision_gate, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/post-rc-decision-record-template.md"

REQUIRED_PHRASES = [
    "Status: template for post-v1.0 RC boundary decisions.",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "Decision record status: `draft | approved_for_planning | no_go | superseded`.",
    "Decision Header",
    "Decision ID:",
    "Owner:",
    "Reviewer:",
    "Target lane:",
    "Trigger And Requested Change",
    "Current boundary being changed:",
    "Allowed scope:",
    "Explicitly forbidden scope:",
    "Runtime surfaces touched:",
    "Runtime surfaces not touched:",
    "Tool count impact:",
    "Manifest impact:",
    "Policy/rule impact:",
    "API/MCP impact:",
    "UI runtime impact:",
    "Mission Control impact:",
    "Sandbox/VM impact:",
    "Local model impact:",
    "Trusted-host promotion impact:",
    "SIEM/telemetry impact:",
    "Identity/storage/remote impact:",
    "Compliance/public-positioning impact:",
    "Required Evidence",
    "Required source-review or external-review evidence:",
    "Required implementation plan:",
    "Required rollback and stop conditions:",
    "Required tests:",
    "Required gates:",
    "Required packet artifacts:",
    "Required negative transcripts:",
    "Required accepted-risk update:",
    "Required operator warning language:",
    "Risk And Boundary Decision",
    "Accepted-risk impact:",
    "Permission/authority impact:",
    "Audit/evidence impact:",
    "Go/no-go outcome:",
    "Implementation Preconditions",
    "Blocked-by-Default Lanes",
    "make post-rc-decision-record-template-check",
    "make post-rc-decision-gate",
]

FORBIDDEN_PHRASES = [
    "capability expansion allowed now",
    "Mission Control may execute",
    "trusted-host promotion is implemented",
    "compliance automation approved",
    "public security product approved",
    "sandbox orchestration is implemented",
    "local model invocation is implemented",
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
    doc_rel = DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    gate_report = post_rc_decision_gate.build_report(repo_root)

    text = ""
    if not doc_path.exists():
        failures.append("post-RC decision record template doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"post-RC decision record template is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    f"post-RC decision record template contains forbidden phrase: {phrase}"
                )

    failures.extend(f"post-RC decision gate: {failure}" for failure in gate_report["failures"])

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("post-RC decision record template is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("post-RC decision record template is missing from docs-site inputs")
    if "post-rc-decision-record-template-check:" not in makefile:
        failures.append("Make target is missing: post-rc-decision-record-template-check")
    if "post-rc-decision-record-template-check" not in release_check_body:
        failures.append("post-rc-decision-record-template-check is missing from release-check")
    if "make post-rc-decision-record-template-check" not in readme:
        failures.append("README is missing post-RC decision record template command")
    if "post-RC decision record template" not in readme:
        failures.append("README is missing post-RC decision record template reference")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_record_template_doc": doc_rel,
        "tool_count": 24,
        "capability_expansion_allowed": False,
        "mission_control_runtime_allowed": False,
        "sandbox_orchestration_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "production_identity_allowed": False,
        "compliance_claims_allowed": False,
        "runtime_changes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin post-RC decision record template check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_record_template_doc: {report['decision_record_template_doc']}",
        f"tool_count: {report['tool_count']}",
        f"capability_expansion_allowed: {str(report['capability_expansion_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

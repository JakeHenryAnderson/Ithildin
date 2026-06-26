"""Validate the v1.0 progress-assessment snapshot and wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_readiness_gap_matrix_check,
    next_capability_readiness,
    review_docs,
    v1_rc_status_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs/codex/v1.0-progress-assessment.md"

REQUIRED_PHRASES = [
    "Status: conservative progress-assessment snapshot",
    "Governed tool count: `24`",
    "Latest implemented tool: `sandbox.artifact.write_text`",
    "Selected next capability: `not selected`",
    "Capability expansion: blocked",
    "Runtime changes: blocked",
    "Public/security-product positioning: blocked",
    "Enterprise readiness gap count: `10`",
    "Recommended next enterprise review: `ERG-003`",
    "Core governed local tool gateway | `92-96%`",
    "v1.0 local-preview RC foundation | `80-88%`",
    "Operator workbench and local demo experience | `70-80%`",
    "Mission Control plus Ithildin integration path | `50-65%`",
    "Sandbox/VM governed agent workflow | `45-60%`",
    "Enterprise/security-product readiness | `35-50%`",
    "Full long-term governed-agent workbench vision | `55-65%`",
    "same-commit `make release-check` and `make review-candidate`",
    "favorable external/source disposition for `ERG-003`",
    "Mission Control remains a display/import layer",
    "Blocked Claims",
]

BLOCKED_PHRASES = [
    "production deployment readiness",
    "production identity or enterprise RBAC",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP hosting",
    "Ithildin-managed VM/container lifecycle",
    "Mission Control execution authority",
    "trusted-host promotion",
    "SIEM custody",
    "HIPAA/GLBA/SOX/GDPR compliance automation",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "enterprise-ready",
    "production-ready",
    "compliance-grade",
    "tamper-proof",
    "secure sandbox",
    "approved for live VM",
    "Mission Control may execute",
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
    status = v1_rc_status_check.build_report(repo_root)
    gap_matrix = enterprise_readiness_gap_matrix_check.build_report(repo_root)
    capability = next_capability_readiness.build_report(repo_root)

    failures.extend(f"v1-rc-status: {failure}" for failure in status["failures"])
    failures.extend(f"enterprise-gap-matrix: {failure}" for failure in gap_matrix["failures"])
    failures.extend(f"next-capability: {failure}" for failure in capability["failures"])

    doc_rel = DOC_PATH.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if status.get("tool_count") != 24:
        failures.append("v1 status tool count is not 24")
    if gap_matrix.get("gap_count") != 10:
        failures.append("enterprise gap count is not 10")
    if capability.get("next_candidate") != "not selected":
        failures.append("next capability candidate is selected")
    if capability.get("next_candidate_implementation_allowed"):
        failures.append("next capability implementation is allowed")
    if status.get("runtime_changes_allowed"):
        failures.append("runtime changes are allowed")
    if status.get("public_security_product_positioning_allowed"):
        failures.append("public/security-product positioning is allowed")

    if not doc_path.exists():
        failures.append("v1.0 progress assessment doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 progress assessment is missing phrase: {phrase}")
        for phrase in BLOCKED_PHRASES:
            if phrase not in text:
                failures.append(
                    f"v1.0 progress assessment is missing blocked phrase: {phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    f"v1.0 progress assessment contains forbidden phrase: {phrase}"
                )

    if "v1-progress-assessment:" not in makefile:
        failures.append("Make target is missing: v1-progress-assessment")
    if "v1-progress-assessment" not in release_check_body:
        failures.append("v1-progress-assessment is missing from release-check")
    if "make v1-progress-assessment" not in readme:
        failures.append("README is missing v1-progress-assessment command")
    if doc_rel not in readme:
        failures.append("README is missing v1.0 progress assessment doc")
    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 progress assessment is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 progress assessment is missing from docs-site inputs")
    if "Ithildin v1.0 Progress Assessment" not in review_index:
        failures.append("review docs index is missing v1.0 progress assessment")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "assessment_doc": doc_rel,
        "tool_count": status.get("tool_count"),
        "latest_implemented_tool": status.get("latest_implemented_tool"),
        "selected_capability": capability.get("next_candidate"),
        "enterprise_gap_count": gap_matrix.get("gap_count"),
        "recommended_next_enterprise_review": "ERG-003",
        "capability_expansion_allowed": False,
        "runtime_changes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "progress_bands": {
            "core_local_gateway": "92-96%",
            "v1_local_preview_rc": "80-88%",
            "operator_workbench_demo": "70-80%",
            "mission_control_integration": "50-65%",
            "sandbox_vm_governed_workflow": "45-60%",
            "enterprise_security_product_readiness": "35-50%",
            "long_term_vision": "55-65%",
        },
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 progress assessment",
        f"valid: {str(report['valid']).lower()}",
        f"assessment_doc: {report['assessment_doc']}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        f"latest_implemented_tool: {report.get('latest_implemented_tool', 'unknown')}",
        f"selected_capability: {report.get('selected_capability', 'unknown')}",
        f"enterprise_gap_count: {report.get('enterprise_gap_count', 'unknown')}",
        f"recommended_next_enterprise_review: {report['recommended_next_enterprise_review']}",
        "capability_expansion_allowed: "
        f"{str(report['capability_expansion_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        "progress_bands:",
    ]
    lines.extend(
        f"- {name}: {band}" for name, band in report["progress_bands"].items()
    )
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

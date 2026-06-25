"""Validate the compliance mapping architecture packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    control_mapping_design_check,
    incident_reconstruction_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/compliance-mapping-architecture.md"

REQUIRED_PHRASES = [
    "Status: design-only architecture packet for `ERG-009`.",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "`ERG-009`: Compliance mapping support",
    "control-mapping-design.md",
    "incident-reconstruction-guide.md",
    "Future Compliance Mapping Questions",
    "Mapping Template Requirements",
    "Evidence Sources",
    "Evidence Non-Goals",
    "Operator Responsibility Model",
    "Required Before Implementation",
    "external/source review",
    "The current decision is `planning_only`.",
    "Runtime compliance mapping implementation remains blocked",
    "make compliance-mapping-architecture-check",
]

REQUIRED_FRAMEWORK_PHRASES = [
    "target framework or control family",
    "HIPAA",
    "GLBA",
    "SOX",
    "GDPR",
    "NIST",
    "CIS",
    "SOC 2",
    "control objective taxonomy",
    "legal-review boundary",
    "mapping confidence labels",
    "false-assurance warnings",
]

REQUIRED_TEMPLATE_PHRASES = [
    "mapping ID and framework/control reference",
    "control objective label",
    "Ithildin evidence source",
    "safe evidence fields used",
    "what the evidence can support",
    "what the evidence cannot prove",
    "accepted-risk references",
    "verification command or packet pointer",
]

REQUIRED_NON_EXPORT_PHRASES = [
    "prompts",
    "secrets",
    "file contents",
    "diffs",
    "response bodies",
    "package script values",
    "dependency names",
    "raw sensitive paths",
    "raw tool arguments",
    "model output",
    "private key material",
    "bearer tokens",
    "environment variables",
    "connection strings",
    "local database contents",
    "raw sandbox internals",
    "raw IdP claims",
    "raw user-directory data",
    "legal advice",
    "patient/client records",
    "regulated data values",
]

FORBIDDEN_PHRASES = [
    "compliance automation is approved",
    "HIPAA compliant",
    "GLBA compliant",
    "SOX compliant",
    "GDPR compliant",
    "SOC 2 compliant",
    "automated certification is approved",
    "legal advice is implemented",
    "public security product approved",
    "custody-grade audit is implemented",
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
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    runway = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    decision_register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    control_report = control_mapping_design_check.build_report(repo_root)
    incident_report = incident_reconstruction_check.build_report(repo_root)

    text = ""
    if not doc_path.exists():
        failures.append("Compliance mapping architecture doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        normalized_text = " ".join(text.split())
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized_text:
                failures.append(f"Compliance mapping architecture is missing phrase: {phrase}")
        for phrase in REQUIRED_FRAMEWORK_PHRASES:
            if phrase not in normalized_text:
                failures.append(
                    "Compliance mapping architecture is missing framework phrase: "
                    f"{phrase}"
                )
        for phrase in REQUIRED_TEMPLATE_PHRASES:
            if phrase not in normalized_text:
                failures.append(
                    "Compliance mapping architecture is missing template phrase: "
                    f"{phrase}"
                )
        for phrase in REQUIRED_NON_EXPORT_PHRASES:
            if phrase not in normalized_text:
                failures.append(
                    "Compliance mapping architecture is missing non-export phrase: "
                    f"{phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    f"Compliance mapping architecture contains forbidden phrase: {phrase}"
                )

    failures.extend(f"control mapping design: {failure}" for failure in control_report["failures"])
    failures.extend(
        f"incident reconstruction guide: {failure}"
        for failure in incident_report["failures"]
    )

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("Compliance mapping architecture doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("Compliance mapping architecture doc is missing from docs site")
    if "Compliance Mapping Architecture" not in review_index:
        failures.append("review docs index is missing compliance mapping architecture")
    if "compliance-mapping-architecture-check:" not in makefile:
        failures.append("Make target is missing: compliance-mapping-architecture-check")
    if "compliance-mapping-architecture-check" not in release_check_body:
        failures.append("compliance-mapping-architecture-check is missing from release-check")
    if "make compliance-mapping-architecture-check" not in readme:
        failures.append("README is missing compliance mapping architecture command")
    if "docs/codex/compliance-mapping-architecture.md" not in readme:
        failures.append("README is missing compliance mapping architecture doc")
    for container_name, container_text in {
        "enterprise runway": runway,
        "enterprise gap matrix": gap_matrix,
        "post-RC decision register": decision_register,
    }.items():
        if "compliance-mapping-architecture.md" not in container_text:
            failures.append(f"{container_name} is missing compliance mapping architecture pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "architecture_doc": doc_rel,
        "erg_009_status": "planning_only",
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "compliance_mapping_runtime_allowed": False,
        "compliance_claims_allowed": False,
        "legal_advice_allowed": False,
        "automated_certification_allowed": False,
        "custody_grade_audit_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin compliance mapping architecture check",
        f"valid: {str(report['valid']).lower()}",
        f"architecture_doc: {report['architecture_doc']}",
        f"erg_009_status: {report['erg_009_status']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "compliance_mapping_runtime_allowed: "
        f"{str(report['compliance_mapping_runtime_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
        f"legal_advice_allowed: {str(report['legal_advice_allowed']).lower()}",
        "automated_certification_allowed: "
        f"{str(report['automated_certification_allowed']).lower()}",
        f"custody_grade_audit_allowed: {str(report['custody_grade_audit_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

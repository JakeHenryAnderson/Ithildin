"""Validate the SIEM export adapter architecture packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, siem_evidence_design_check

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/siem-export-adapter-architecture.md"

REQUIRED_PHRASES = [
    "Status: design-only architecture packet for `ERG-008`.",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "`ERG-008`: SIEM-shaped export adapter",
    "siem-shaped-evidence-design.md",
    "Future Adapter Architecture Questions",
    "Event Schema Requirements",
    "Delivery Requirements",
    "Export Non-Goals",
    "Required Before Implementation",
    "external/source review",
    "The current decision is `planning_only`.",
    "Runtime adapter implementation remains blocked",
    "make siem-export-adapter-architecture-check",
]

REQUIRED_DELIVERY_PHRASES = [
    "target adapter type",
    "supported event schema version and compatibility policy",
    "field redaction and denylist rules",
    "retry, dead-letter, and backpressure behavior",
    "delivery authentication model",
    "signing and verification story",
    "idempotency and replay handling",
    "operator-visible diagnostics",
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
    "connection strings",
    "local database contents",
    "raw sandbox internals",
]

FORBIDDEN_PHRASES = [
    "SIEM adapter is implemented",
    "hosted telemetry is enabled",
    "remote delivery is approved",
    "custody-grade audit is implemented",
    "compliance automation is approved",
    "security operations control plane is implemented",
    "public security product approved",
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
    evidence_design_report = siem_evidence_design_check.build_report(repo_root)

    text = ""
    if not doc_path.exists():
        failures.append("SIEM export adapter architecture doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        normalized_text = " ".join(text.split())
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized_text:
                failures.append(f"SIEM export adapter architecture is missing phrase: {phrase}")
        for phrase in REQUIRED_DELIVERY_PHRASES:
            if phrase not in normalized_text:
                failures.append(
                    f"SIEM export adapter architecture is missing delivery phrase: {phrase}"
                )
        for phrase in REQUIRED_NON_EXPORT_PHRASES:
            if phrase not in normalized_text:
                failures.append(
                    f"SIEM export adapter architecture is missing non-export phrase: {phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    f"SIEM export adapter architecture contains forbidden phrase: {phrase}"
                )

    failures.extend(
        f"SIEM-shaped evidence design: {failure}"
        for failure in evidence_design_report["failures"]
    )

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("SIEM export adapter architecture doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("SIEM export adapter architecture doc is missing from docs site")
    if "SIEM Export Adapter Architecture" not in review_index:
        failures.append("review docs index is missing SIEM export adapter architecture")
    if "siem-export-adapter-architecture-check:" not in makefile:
        failures.append("Make target is missing: siem-export-adapter-architecture-check")
    if "siem-export-adapter-architecture-check" not in release_check_body:
        failures.append("siem-export-adapter-architecture-check is missing from release-check")
    if "make siem-export-adapter-architecture-check" not in readme:
        failures.append("README is missing SIEM export adapter architecture command")
    if "siem-export-adapter-architecture.md" not in readme:
        failures.append("README is missing SIEM export adapter architecture doc")
    for container_name, container_text in {
        "enterprise runway": runway,
        "enterprise gap matrix": gap_matrix,
        "post-RC decision register": decision_register,
    }.items():
        if "siem-export-adapter-architecture.md" not in container_text:
            failures.append(
                f"{container_name} is missing SIEM export adapter architecture pointer"
            )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "architecture_doc": doc_rel,
        "erg_008_status": "planning_only",
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "siem_adapter_allowed": False,
        "hosted_telemetry_allowed": False,
        "remote_delivery_allowed": False,
        "custody_grade_audit_allowed": False,
        "compliance_claims_allowed": False,
        "security_operations_control_plane_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin SIEM export adapter architecture check",
        f"valid: {str(report['valid']).lower()}",
        f"architecture_doc: {report['architecture_doc']}",
        f"erg_008_status: {report['erg_008_status']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"hosted_telemetry_allowed: {str(report['hosted_telemetry_allowed']).lower()}",
        f"remote_delivery_allowed: {str(report['remote_delivery_allowed']).lower()}",
        f"custody_grade_audit_allowed: {str(report['custody_grade_audit_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
        "security_operations_control_plane_allowed: "
        f"{str(report['security_operations_control_plane_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

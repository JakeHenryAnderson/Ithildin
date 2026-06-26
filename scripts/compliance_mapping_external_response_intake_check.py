"""Validate the compliance mapping external response intake template."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import external_response_normalize, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/compliance-mapping-external-response-intake.md"
DOC_NAME = "compliance-mapping-external-response-intake.md"

REQUIRED_PHRASES = [
    "Status: response-intake template for planning-only `ERG-009`.",
    "Current governed tool count: `24`.",
    "Current `ERG-009` status before reviewer disposition: `planning_only`.",
    "Current selected capability: `not selected`.",
    "Finding namespace: `EXT-COMPLIANCE-MAPPING-###`.",
    "Reviewed area for normalization: `compliance-mapping`.",
    "Required Disposition Answers",
    "Finding Extraction Table",
    "EXT-COMPLIANCE-MAPPING-###",
    "--area compliance-mapping",
    "mutates_findings: false",
    "closes_external_review: false",
    "continue_architecture_planning",
    "revise_before_more_planning",
    "block_runtime_implementation",
    "Only a later committed triage update may move `ERG-009` away",
]

REQUIRED_QUESTIONS = [
    "Did the reviewer inspect the compliance mapping disposition packet",
    "Is the target framework/control-family boundary coherent enough",
    "Are mapping-template shape, required fields, versioning",
    "Are evidence-field allowlists, denylist/non-export expectations",
    "Are operator responsibility language, legal-review boundary",
    "Are accepted-risk impacts for local principals",
    "Are there any critical/high findings",
    "may the lane continue architecture planning",
    "avoid approving runtime compliance mapping",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "implementation planning without a later committed decision record",
    "runtime implementation",
    "compliance mapping runtime behavior",
    "compliance automation",
    "legal advice",
    "automated certification",
    "HIPAA/GLBA/SOX/GDPR/SOC 2/NIST/CIS or other regulated-industry compliance claims",
    "custody-grade audit claims",
    "external notarization",
    "immutable storage",
    "production identity",
    "runtime Postgres",
    "SIEM adapter behavior",
    "hosted telemetry",
    "remote delivery",
    "sandbox orchestration",
    "local model invocation",
    "trusted-host promotion",
    "shell/Docker/Kubernetes/browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "plugin SDK behavior",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "implementation planning is approved",
    "runtime implementation is approved",
    "compliance mapping runtime behavior is approved",
    "compliance automation is approved",
    "legal advice is approved",
    "automated certification is approved",
    "HIPAA compliant",
    "GLBA compliant",
    "SOX compliant",
    "GDPR compliant",
    "SOC 2 compliant",
    "custody-grade audit is implemented",
    "production-ready",
    "secure sandbox",
    "compliance-grade",
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
    doc_path = repo_root / DOC_REL
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    disposition_packet = (
        repo_root / "docs/codex/compliance-mapping-disposition-packet.md"
    ).read_text(encoding="utf-8")
    architecture = (repo_root / "docs/codex/compliance-mapping-architecture.md").read_text(
        encoding="utf-8"
    )
    packet_script = (repo_root / "scripts/compliance_mapping_disposition_packet.py").read_text(
        encoding="utf-8"
    )
    enterprise = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    decision_register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("Compliance mapping external response intake doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"intake doc is missing phrase: {phrase}")
        for phrase in REQUIRED_QUESTIONS:
            if phrase not in text:
                failures.append(f"intake doc is missing disposition question: {phrase}")
        for phrase in REQUIRED_BLOCKED_BOUNDARIES:
            if phrase not in text:
                failures.append(f"intake doc is missing blocked boundary: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"intake doc contains forbidden phrase: {phrase}")

    if "compliance-mapping" not in external_response_normalize.AREA_NAMESPACES:
        failures.append("external response normalizer lacks compliance-mapping area")
    elif external_response_normalize.AREA_NAMESPACES["compliance-mapping"] != "COMPLIANCE-MAPPING":
        failures.append("external response normalizer uses wrong compliance mapping namespace")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("Compliance mapping intake doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("Compliance mapping intake doc is missing from docs-site inputs")
    if DOC_REL not in packet_script:
        failures.append("Compliance mapping disposition packet does not bundle intake doc")
    if DOC_NAME not in disposition_packet:
        failures.append("Compliance mapping disposition packet doc does not point to intake")
    if DOC_NAME not in architecture:
        failures.append("Compliance mapping architecture doc does not point to intake")
    if DOC_NAME not in enterprise:
        failures.append("enterprise runway is missing compliance mapping intake pointer")
    if DOC_NAME not in gap_matrix:
        failures.append("enterprise gap matrix is missing compliance mapping intake pointer")
    if DOC_NAME not in decision_register:
        failures.append("post-RC decision register is missing compliance mapping intake")
    if "Compliance Mapping External Response Intake" not in review_index:
        failures.append("review-docs index is missing compliance mapping intake entry")
    if "compliance-mapping-external-response-intake-check:" not in makefile:
        failures.append("Make target is missing: compliance-mapping-external-response-intake-check")
    if "compliance-mapping-external-response-intake-check" not in release_check_body:
        failures.append(
            "compliance-mapping-external-response-intake-check missing from release-check"
        )
    if "make compliance-mapping-external-response-intake-check" not in readme:
        failures.append("README is missing compliance mapping intake command")
    if DOC_REL not in readme:
        failures.append("README is missing compliance mapping intake doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "intake_doc": DOC_REL,
        "tool_count": 24,
        "area": "compliance-mapping",
        "finding_namespace": "EXT-COMPLIANCE-MAPPING-###",
        "erg_009_status": "planning_only",
        "mutates_findings": False,
        "closes_external_review": False,
        "implementation_planning_allowed": False,
        "runtime_changes_allowed": False,
        "compliance_mapping_runtime_allowed": False,
        "compliance_automation_allowed": False,
        "legal_advice_allowed": False,
        "automated_certification_allowed": False,
        "regulated_industry_compliance_claims_allowed": False,
        "custody_grade_audit_claims_allowed": False,
        "external_notarization_allowed": False,
        "immutable_storage_allowed": False,
        "production_identity_allowed": False,
        "runtime_postgres_allowed": False,
        "siem_adapter_allowed": False,
        "hosted_telemetry_allowed": False,
        "remote_delivery_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin compliance mapping external response intake check",
        f"valid: {str(report['valid']).lower()}",
        f"intake_doc: {report['intake_doc']}",
        f"tool_count: {report['tool_count']}",
        f"area: {report['area']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"erg_009_status: {report['erg_009_status']}",
        f"mutates_findings: {str(report['mutates_findings']).lower()}",
        f"closes_external_review: {str(report['closes_external_review']).lower()}",
        "implementation_planning_allowed: "
        f"{str(report['implementation_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "compliance_mapping_runtime_allowed: "
        f"{str(report['compliance_mapping_runtime_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        f"legal_advice_allowed: {str(report['legal_advice_allowed']).lower()}",
        "automated_certification_allowed: "
        f"{str(report['automated_certification_allowed']).lower()}",
        "regulated_industry_compliance_claims_allowed: "
        f"{str(report['regulated_industry_compliance_claims_allowed']).lower()}",
        "custody_grade_audit_claims_allowed: "
        f"{str(report['custody_grade_audit_claims_allowed']).lower()}",
        f"external_notarization_allowed: {str(report['external_notarization_allowed']).lower()}",
        f"immutable_storage_allowed: {str(report['immutable_storage_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"runtime_postgres_allowed: {str(report['runtime_postgres_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"hosted_telemetry_allowed: {str(report['hosted_telemetry_allowed']).lower()}",
        f"remote_delivery_allowed: {str(report['remote_delivery_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

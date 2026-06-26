"""Validate the fail-closed public/security-product positioning decision closure gate."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/public-security-product-positioning-decision-closure-gate.md"
DOC_NAME = "public-security-product-positioning-decision-closure-gate.md"
INTAKE_NAME = "public-security-product-positioning-decision-intake.md"
NORMALIZED_RESPONSE_REL = (
    "var/review-runs/public-security-product-positioning/normalized-response.json"
)
EXPECTED_AREA = "public-security-product-positioning"
EXPECTED_NAMESPACE = "EXT-PUBLIC-POSITIONING-###"
EXPECTED_OUTCOME = "ready_for_claim_decision_record"
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

REQUIRED_PHRASES = [
    "Status: fail-closed closure gate for blocked `ERG-010` and `PRD-PUBLIC-POSITIONING-001`.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "make public-security-product-positioning-decision-closure-check",
    NORMALIZED_RESPONSE_REL,
    "ithildin.external_review.normalized_response",
    "reviewed area: `public-security-product-positioning`",
    "source-level` or `packet-and-source`",
    "finding namespace: `EXT-PUBLIC-POSITIONING-###`",
    "can_close_source_rows: true",
    "mutates_findings: false",
    "closes_external_review: false",
    "no critical/high findings",
    "disposition_outcome: ready_for_claim_decision_record",
    "closure_ready: false",
    "erg_010_status: blocked",
    "public_security_product_positioning_allowed: false",
    "production_security_compliance_positioning_allowed: false",
    "claim_decision_record_allowed: false",
    "runtime_changes_allowed: false",
    "ready_for_claim_decision_record",
    "separate committed triage update",
    INTAKE_NAME,
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "broader public distribution",
    "production deployment ready wording",
    "security-product positioning",
    "production/security/compliance positioning",
    "sandbox guarantee language",
    "EDR/MDM claims",
    "SIEM custody claims",
    "compliance claims",
    "compliance automation",
    "legal advice",
    "automated certification",
    "regulatory-grade audit claims",
    "custody-grade audit claims",
    "tamper-proof logging",
    "audit immutability claims",
    "production identity",
    "enterprise RBAC",
    "runtime Postgres",
    "hosted telemetry",
    "hosted MCP",
    "remote MCP transport/gateway claims",
    "managed model serving",
    "arbitrary-tool safety wording",
    "broad autonomous execution",
    "HIPAA/GLBA/SOX/GDPR/SOC 2/NIST/CIS compliance",
    "support/deployment/update/incident-response claims",
    "sandbox orchestration",
    "local model invocation",
    "trusted-host promotion",
    "SIEM adapter behavior",
    "compliance mapping runtime behavior",
    "shell/Docker/Kubernetes/browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "plugin SDK behavior",
    "new governed tool powers",
]

FORBIDDEN_PHRASES = [
    "public/security-product positioning is approved",
    "production/security/compliance positioning is approved",
    "production deployment readiness is approved",
    "security-product positioning is approved",
    "sandbox claims are approved",
    "SIEM custody claims are approved",
    "compliance claims are approved",
    "ERG-010 is closed",
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
    normalized_response_path = repo_root / NORMALIZED_RESPONSE_REL
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    intake = _read(repo_root / f"docs/codex/{INTAKE_NAME}")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("public positioning decision closure gate doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"closure gate doc is missing phrase: {phrase}")
        for phrase in REQUIRED_BLOCKED_BOUNDARIES:
            if phrase not in text:
                failures.append(f"closure gate doc is missing blocked boundary: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"closure gate doc contains forbidden phrase: {phrase}")

    response_present = normalized_response_path.exists()
    response_report = _validate_normalized_response(normalized_response_path)
    failures.extend(response_report["failures"])
    closure_ready = response_report["closure_ready"]

    for linked_text, source_name in [
        (readme, "README"),
        (docs_site, "docs site"),
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
        (decision_register, "post-RC decision register"),
        (intake, "public positioning intake"),
    ]:
        if DOC_NAME not in linked_text and DOC_REL not in linked_text:
            failures.append(f"{source_name} is missing {DOC_NAME}")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("review_docs.REVIEW_DOCS is missing public positioning closure gate doc")
    if "public-security-product-positioning-decision-closure-check:" not in makefile:
        failures.append(
            "Make target is missing: public-security-product-positioning-decision-closure-check"
        )
    release_check_additive = (
        "release-check: public-security-product-positioning-decision-closure-check"
    )
    if (
        "public-security-product-positioning-decision-closure-check" not in release_check_body
        and release_check_additive not in makefile
    ):
        failures.append(
            "public-security-product-positioning-decision-closure-check missing from release-check"
        )
    if "public-security-product-positioning-decision-closure-check" not in release_guardrails:
        failures.append("release guardrails do not require public positioning closure-check")

    return {
        "valid": not failures,
        "failures": failures,
        "closure_gate_doc": DOC_REL,
        "normalized_response_path": NORMALIZED_RESPONSE_REL,
        "normalized_response_present": response_present,
        "closure_ready": closure_ready,
        "disposition_outcome": response_report["disposition_outcome"],
        "erg_010_status": (
            "blocked" if not closure_ready else "ready_for_claim_decision_record"
        ),
        "allowed_closure_state": "ready_for_claim_decision_record",
        "tool_count": 24,
        "area": EXPECTED_AREA,
        "finding_namespace": EXPECTED_NAMESPACE,
        "claim_decision_record_allowed": False,
        "public_security_product_positioning_allowed": False,
        "production_security_compliance_positioning_allowed": False,
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "new_tool_powers_allowed": False,
        "broader_public_distribution_allowed": False,
        "production_deployment_ready_wording_allowed": False,
        "sandbox_claims_allowed": False,
        "edr_mdm_claims_allowed": False,
        "siem_custody_claims_allowed": False,
        "compliance_claims_allowed": False,
        "compliance_automation_allowed": False,
        "legal_advice_allowed": False,
        "automated_certification_allowed": False,
        "regulatory_grade_audit_claims_allowed": False,
        "custody_grade_audit_claims_allowed": False,
        "tamper_proof_logging_claims_allowed": False,
        "audit_immutability_claims_allowed": False,
        "production_identity_allowed": False,
        "enterprise_rbac_allowed": False,
        "runtime_postgres_allowed": False,
        "hosted_telemetry_allowed": False,
        "hosted_mcp_allowed": False,
        "remote_mcp_allowed": False,
        "managed_model_serving_allowed": False,
        "support_deployment_incident_claims_allowed": False,
        "sandbox_orchestration_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_mapping_runtime_allowed": False,
        "response": response_report,
    }


def _validate_normalized_response(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "failures": [],
            "closure_ready": False,
            "disposition_outcome": None,
            "reason": "normalized response is absent; ERG-010 remains blocked",
        }
    failures: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "failures": [f"normalized response is invalid JSON: {exc}"],
            "closure_ready": False,
            "disposition_outcome": None,
            "reason": "invalid normalized response",
        }

    if payload.get("response_type") != "ithildin.external_review.normalized_response":
        failures.append("normalized response has unexpected response_type")
    if payload.get("area") != EXPECTED_AREA:
        failures.append("normalized response area is not public-security-product-positioning")
    if payload.get("source_access") not in {"source-level", "packet-and-source"}:
        failures.append("normalized response source_access is not sufficient for closure")
    if payload.get("can_close_source_rows") is not True:
        failures.append("normalized response cannot close source rows")
    if payload.get("mutates_findings") is not False:
        failures.append("normalized response must not mutate findings")
    if payload.get("closes_external_review") is not False:
        failures.append("normalized response must not close external review directly")
    if not SHA256_PATTERN.match(str(payload.get("reviewed_packet_hash", ""))):
        failures.append("normalized response reviewed_packet_hash is not a sha256 digest")
    disposition_outcome = payload.get("disposition_outcome")
    if disposition_outcome != EXPECTED_OUTCOME:
        failures.append("normalized response disposition_outcome does not permit claim decision")

    findings = payload.get("findings", [])
    if not isinstance(findings, list):
        failures.append("normalized response findings must be a list")
        findings = []
    for finding in findings:
        if not isinstance(finding, dict):
            failures.append("normalized response contains a non-object finding")
            continue
        finding_id = str(finding.get("finding_id", ""))
        if not finding_id.startswith("EXT-PUBLIC-POSITIONING-"):
            failures.append(f"finding has wrong namespace: {finding_id}")
        if finding.get("area") != EXPECTED_AREA:
            failures.append(f"{finding_id} has wrong area")
        if str(finding.get("severity", "")).lower() in {"critical", "high"}:
            failures.append(f"{finding_id} is critical/high and blocks closure")

    return {
        "failures": failures,
        "closure_ready": not failures,
        "disposition_outcome": disposition_outcome,
        "reason": "normalized response validates" if not failures else "normalized response failed",
        "finding_count": len(findings),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin public/security-product positioning decision closure check",
        f"valid: {str(report['valid']).lower()}",
        f"closure_gate_doc: {report['closure_gate_doc']}",
        f"normalized_response_path: {report['normalized_response_path']}",
        f"normalized_response_present: {str(report['normalized_response_present']).lower()}",
        f"closure_ready: {str(report['closure_ready']).lower()}",
        f"disposition_outcome: {report['disposition_outcome']}",
        f"erg_010_status: {report['erg_010_status']}",
        f"allowed_closure_state: {report['allowed_closure_state']}",
        f"tool_count: {report['tool_count']}",
        f"claim_decision_record_allowed: {str(report['claim_decision_record_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        "production_security_compliance_positioning_allowed: "
        f"{str(report['production_security_compliance_positioning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"new_tool_powers_allowed: {str(report['new_tool_powers_allowed']).lower()}",
        "broader_public_distribution_allowed: "
        f"{str(report['broader_public_distribution_allowed']).lower()}",
        "production_deployment_ready_wording_allowed: "
        f"{str(report['production_deployment_ready_wording_allowed']).lower()}",
        f"sandbox_claims_allowed: {str(report['sandbox_claims_allowed']).lower()}",
        f"edr_mdm_claims_allowed: {str(report['edr_mdm_claims_allowed']).lower()}",
        f"siem_custody_claims_allowed: {str(report['siem_custody_claims_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        f"legal_advice_allowed: {str(report['legal_advice_allowed']).lower()}",
        "automated_certification_allowed: "
        f"{str(report['automated_certification_allowed']).lower()}",
        "regulatory_grade_audit_claims_allowed: "
        f"{str(report['regulatory_grade_audit_claims_allowed']).lower()}",
        "custody_grade_audit_claims_allowed: "
        f"{str(report['custody_grade_audit_claims_allowed']).lower()}",
        "tamper_proof_logging_claims_allowed: "
        f"{str(report['tamper_proof_logging_claims_allowed']).lower()}",
        "audit_immutability_claims_allowed: "
        f"{str(report['audit_immutability_claims_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"enterprise_rbac_allowed: {str(report['enterprise_rbac_allowed']).lower()}",
        f"runtime_postgres_allowed: {str(report['runtime_postgres_allowed']).lower()}",
        f"hosted_telemetry_allowed: {str(report['hosted_telemetry_allowed']).lower()}",
        f"hosted_mcp_allowed: {str(report['hosted_mcp_allowed']).lower()}",
        f"remote_mcp_allowed: {str(report['remote_mcp_allowed']).lower()}",
        f"managed_model_serving_allowed: {str(report['managed_model_serving_allowed']).lower()}",
        "support_deployment_incident_claims_allowed: "
        f"{str(report['support_deployment_incident_claims_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        "compliance_mapping_runtime_allowed: "
        f"{str(report['compliance_mapping_runtime_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

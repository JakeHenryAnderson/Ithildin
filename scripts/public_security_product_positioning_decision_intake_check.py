"""Validate the public/security-product positioning decision-intake packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, v08_public_preview_decision

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/public-security-product-positioning-decision-intake.md"
DOC_NAME = "public-security-product-positioning-decision-intake.md"

REQUIRED_PHRASES = [
    "Status: decision-intake planning packet for `ERG-010` and `PRD-PUBLIC-POSITIONING-001`.",
    "Current governed tool count: `24`.",
    "Current `ERG-010` status: `blocked`.",
    "Current selected capability: `not selected`.",
    "broad public/security-product positioning: `no_go`",
    "production/security/compliance positioning: `no_go`",
    "Required Preconditions",
    "Required Evidence",
    "Explicitly Forbidden Claim Categories Until A Future Decision Changes This",
    "Allowed Current Wording",
    "Stop Conditions",
    "make public-security-product-positioning-decision-intake-check",
    "make v08-public-preview-decision",
    "make v1-rc-readiness",
    "make v1-assurance-closure-check",
    "make post-rc-decision-register-check",
]

REQUIRED_EVIDENCE = [
    "v0.8-public-preview-risk-review.md",
    "v0.8-final-decision-packet.md",
    "v1.0-rc-final-handoff.md",
    "v1.0-rc-readiness-gate.md",
    "v1.0-assurance-closure.md",
    "enterprise-readiness-gap-matrix.md",
    "post-rc-decision-register.md",
    "accepted-risk-register.json",
]

REQUIRED_BLOCKED_CLAIMS = [
    "production deployment ready wording",
    "sandbox guarantee language",
    "security product",
    "EDR/MDM agent",
    "SIEM custody",
    "compliance tool",
    "regulatory-grade audit",
    "custody-grade audit",
    "tamper-proof logging",
    "audit immutability",
    "production identity",
    "enterprise RBAC",
    "hosted MCP",
    "remote MCP transport/gateway claims",
    "hosted telemetry",
    "runtime Postgres",
    "managed model serving",
    "arbitrary-tool safety wording",
    "broad autonomous execution",
    "HIPAA/GLBA/SOX/GDPR/SOC 2/NIST/CIS compliance",
    "automated certification",
    "legal advice",
    "public/security-product positioning",
]

FORBIDDEN_APPROVAL_PHRASES = [
    "public/security-product positioning is approved",
    "production deployment readiness is approved",
    "security-product positioning is approved",
    "secure sandbox is approved",
    "SIEM custody is approved",
    "compliance claims are approved",
    "production identity is approved",
    "runtime Postgres is approved",
    "hosted telemetry is approved",
    "remote MCP is approved",
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
    register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    runway = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    release_guardrails = (repo_root / "scripts/release_guardrails.py").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    public_preview_report = v08_public_preview_decision.build_report(repo_root)

    if not doc_path.exists():
        failures.append("public/security-product positioning decision intake doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"decision intake doc is missing phrase: {phrase}")
        for phrase in REQUIRED_EVIDENCE:
            if phrase not in text:
                failures.append(f"decision intake doc is missing evidence pointer: {phrase}")
        for phrase in REQUIRED_BLOCKED_CLAIMS:
            if phrase not in text:
                failures.append(f"decision intake doc is missing blocked claim: {phrase}")
        for phrase in FORBIDDEN_APPROVAL_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"decision intake doc contains forbidden phrase: {phrase}")

    if public_preview_report["public_security_product_positioning"] != "no_go":
        failures.append("v0.8 public-preview decision no longer blocks public/security-product")
    if public_preview_report["production_security_compliance_positioning"] != "no_go":
        failures.append("v0.8 public-preview decision no longer blocks production/compliance")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("public positioning decision intake is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("public positioning decision intake is missing from docs-site inputs")
    if DOC_NAME not in register:
        failures.append("post-RC decision register is missing public positioning intake")
    if "PRD-PUBLIC-POSITIONING-001" not in register:
        failures.append("post-RC decision register is missing PRD-PUBLIC-POSITIONING-001")
    if DOC_NAME not in gap_matrix:
        failures.append("enterprise gap matrix is missing public positioning intake")
    if DOC_NAME not in runway:
        failures.append("enterprise runway is missing public positioning intake")
    if "Public/Security-Product Positioning Decision Intake" not in review_index:
        failures.append("review-docs index is missing public positioning intake entry")
    if "public-security-product-positioning-decision-intake-check:" not in makefile:
        failures.append(
            "Make target is missing: public-security-product-positioning-decision-intake-check"
        )
    if "public-security-product-positioning-decision-intake-check" not in release_check_body:
        failures.append(
            "public-security-product-positioning-decision-intake-check missing from release-check"
        )
    if "public-security-product-positioning-decision-intake-check" not in release_guardrails:
        failures.append("release guardrails do not require public positioning intake check")
    if "make public-security-product-positioning-decision-intake-check" not in readme:
        failures.append("README is missing public positioning intake command")
    if DOC_REL not in readme:
        failures.append("README is missing public positioning intake doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_intake_doc": DOC_REL,
        "tool_count": 24,
        "erg_010_status": "blocked",
        "prd_id": "PRD-PUBLIC-POSITIONING-001",
        "continued_local_preview_development": "go",
        "limited_technical_preview_sharing": "conditional_go",
        "public_security_product_positioning": "no_go",
        "production_security_compliance_positioning": "no_go",
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "new_tool_powers_allowed": False,
        "mission_control_runtime_allowed": False,
        "sandbox_claims_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "edr_mdm_claims_allowed": False,
        "siem_custody_claims_allowed": False,
        "production_identity_allowed": False,
        "runtime_postgres_allowed": False,
        "hosted_telemetry_allowed": False,
        "remote_mcp_allowed": False,
        "compliance_claims_allowed": False,
        "compliance_automation_allowed": False,
        "hosted_trust_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin public/security-product positioning decision intake check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_intake_doc: {report['decision_intake_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_010_status: {report['erg_010_status']}",
        f"prd_id: {report['prd_id']}",
        "continued_local_preview_development: go",
        "limited_technical_preview_sharing: conditional_go",
        "public_security_product_positioning: no_go",
        "production_security_compliance_positioning: no_go",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"new_tool_powers_allowed: {str(report['new_tool_powers_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"sandbox_claims_allowed: {str(report['sandbox_claims_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"edr_mdm_claims_allowed: {str(report['edr_mdm_claims_allowed']).lower()}",
        f"siem_custody_claims_allowed: {str(report['siem_custody_claims_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"runtime_postgres_allowed: {str(report['runtime_postgres_allowed']).lower()}",
        f"hosted_telemetry_allowed: {str(report['hosted_telemetry_allowed']).lower()}",
        f"remote_mcp_allowed: {str(report['remote_mcp_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        f"hosted_trust_allowed: {str(report['hosted_trust_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

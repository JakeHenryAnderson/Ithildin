"""Validate the trusted-host promotion external response intake template."""

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
DOC_REL = "docs/codex/trusted-host-promotion-external-response-intake.md"
DOC_NAME = "trusted-host-promotion-external-response-intake.md"

REQUIRED_PHRASES = [
    "Status: response-intake template for blocked `ERG-005`.",
    "Current governed tool count: `24`.",
    "Current `ERG-005` status before reviewer disposition: `blocked`.",
    "Current selected capability: `not selected`.",
    "Finding namespace: `EXT-TRUSTED-HOST-###`.",
    "Reviewed area for normalization: `trusted-host-promotion`.",
    "Required Disposition Answers",
    "Finding Extraction Table",
    "EXT-TRUSTED-HOST-###",
    "--area trusted-host-promotion",
    "mutates_findings: false",
    "closes_external_review: false",
    "continue_design_only",
    "revise_before_more_planning",
    "block_runtime_implementation",
    "Only a later committed triage update may move `ERG-005` away from `blocked`",
]

REQUIRED_QUESTIONS = [
    "Did the reviewer inspect the trusted-host promotion disposition packet",
    "Are the source/staging/approved/evidence zone labels precise enough",
    "Does the implementation-plan contract require exact artifact hash binding",
    "Are the negative fixture and state-machine expectations strong enough",
    "Does the internal review appear sufficient",
    "Are there any critical/high findings",
    "may the lane continue design-only planning",
    "avoid approving host promotion",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "implementation planning without a later committed decision record",
    "runtime implementation",
    "trusted-host promotion",
    "direct host writes",
    "overwrite/delete/move behavior",
    "broad archive extraction",
    "automatic promotion",
    "promotion without exact artifact hash binding",
    "promotion without approval evidence",
    "Mission Control runtime behavior",
    "local model invocation",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "SIEM adapter behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "shell/Docker/Kubernetes/browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "compliance automation",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "implementation planning is approved",
    "runtime implementation is approved",
    "trusted-host promotion is approved",
    "direct host writes are approved",
    "automatic promotion is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "sandbox orchestration is approved",
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
        repo_root / "docs/codex/trusted-host-promotion-disposition-packet.md"
    ).read_text(encoding="utf-8")
    source_review = (repo_root / "docs/codex/trusted-host-promotion-source-review.md").read_text(
        encoding="utf-8"
    )
    packet_script = (repo_root / "scripts/trusted_host_promotion_disposition_packet.py").read_text(
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
        failures.append("trusted-host promotion external response intake doc is missing")
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

    if "trusted-host-promotion" not in external_response_normalize.AREA_NAMESPACES:
        failures.append("external response normalizer lacks trusted-host-promotion area")
    elif external_response_normalize.AREA_NAMESPACES["trusted-host-promotion"] != "TRUSTED-HOST":
        failures.append("external response normalizer uses wrong trusted-host namespace")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("trusted-host promotion intake doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("trusted-host promotion intake doc is missing from docs-site inputs")
    if DOC_REL not in packet_script:
        failures.append("trusted-host disposition packet does not bundle intake doc")
    if DOC_NAME not in disposition_packet:
        failures.append(
            "trusted-host disposition packet doc does not point to external response intake"
        )
    if DOC_NAME not in source_review:
        failures.append("trusted-host source-review doc does not point to external response intake")
    if DOC_NAME not in enterprise:
        failures.append(
            "enterprise runway is missing trusted-host external response intake pointer"
        )
    if DOC_NAME not in gap_matrix:
        failures.append(
            "enterprise gap matrix is missing trusted-host external response intake pointer"
        )
    if DOC_NAME not in decision_register:
        failures.append(
            "post-RC decision register is missing trusted-host external response intake"
        )
    if "Trusted-Host Promotion External Response Intake" not in review_index:
        failures.append("review-docs index is missing trusted-host external response intake entry")
    if "trusted-host-promotion-external-response-intake-check:" not in makefile:
        failures.append(
            "Make target is missing: trusted-host-promotion-external-response-intake-check"
        )
    if "trusted-host-promotion-external-response-intake-check" not in release_check_body:
        failures.append(
            "trusted-host-promotion-external-response-intake-check missing from release-check"
        )
    if "make trusted-host-promotion-external-response-intake-check" not in readme:
        failures.append("README is missing trusted-host promotion intake command")
    if DOC_REL not in readme:
        failures.append("README is missing trusted-host promotion intake doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "intake_doc": DOC_REL,
        "tool_count": 24,
        "area": "trusted-host-promotion",
        "finding_namespace": "EXT-TRUSTED-HOST-###",
        "erg_005_status": "blocked",
        "mutates_findings": False,
        "closes_external_review": False,
        "implementation_planning_allowed": False,
        "runtime_changes_allowed": False,
        "trusted_host_promotion_allowed": False,
        "direct_host_writes_allowed": False,
        "overwrite_delete_move_allowed": False,
        "broad_archive_extraction_allowed": False,
        "automatic_promotion_allowed": False,
        "promotion_without_hash_binding_allowed": False,
        "promotion_without_approval_evidence_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host promotion external response intake check",
        f"valid: {str(report['valid']).lower()}",
        f"intake_doc: {report['intake_doc']}",
        f"tool_count: {report['tool_count']}",
        f"area: {report['area']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"mutates_findings: {str(report['mutates_findings']).lower()}",
        f"closes_external_review: {str(report['closes_external_review']).lower()}",
        "implementation_planning_allowed: "
        f"{str(report['implementation_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"direct_host_writes_allowed: {str(report['direct_host_writes_allowed']).lower()}",
        f"overwrite_delete_move_allowed: {str(report['overwrite_delete_move_allowed']).lower()}",
        "broad_archive_extraction_allowed: "
        f"{str(report['broad_archive_extraction_allowed']).lower()}",
        f"automatic_promotion_allowed: {str(report['automatic_promotion_allowed']).lower()}",
        "promotion_without_hash_binding_allowed: "
        f"{str(report['promotion_without_hash_binding_allowed']).lower()}",
        "promotion_without_approval_evidence_allowed: "
        f"{str(report['promotion_without_approval_evidence_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
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

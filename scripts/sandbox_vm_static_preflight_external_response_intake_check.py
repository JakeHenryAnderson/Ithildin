"""Validate the sandbox/VM static preflight external response intake template."""

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
DOC_REL = "docs/codex/sandbox-vm-static-preflight-external-response-intake.md"
DOC_NAME = "sandbox-vm-static-preflight-external-response-intake.md"
DOC = ROOT / DOC_REL

REQUIRED_PHRASES = [
    "Status: response-intake template for `ERG-003`.",
    "Current governed tool count: `24`.",
    "Current `ERG-003` status before reviewer disposition: `external_review_required`.",
    "Finding namespace: `EXT-SVP-###`.",
    "Reviewed area for normalization: `sandbox-vm-static-preflight`.",
    "Reviewed packet artifact hash: SHA-256 of",
    "sandbox-vm-static-preflight-external-review-artifact-hashes.json",
    "make sandbox-vm-static-preflight-reviewed-packet-hash",
    "Required Disposition Answers",
    "Finding Extraction Table",
    "EXT-SVP-###",
    "--area sandbox-vm-static-preflight",
    'REVIEWED_PACKET_HASH="$(make -s sandbox-vm-static-preflight-reviewed-packet-hash)"',
    '--reviewed-packet-hash "$REVIEWED_PACKET_HASH"',
    "mutates_findings: false",
    "closes_external_review: false",
    "sandbox-vm-static-preflight-response-application-record.md",
    "sandbox-vm-static-preflight-response-application-record-check",
    "closed_local_preview_static_preflight",
    "Only a later committed triage update may move `ERG-003`",
]

REQUIRED_QUESTIONS = [
    "Did the reviewer inspect the static preflight source-review packet",
    "Does the CLI-only fixture runner stay within the approved boundary",
    "Are the static profile fixture contract and negative fixtures sufficient",
    "Are safe-label and safe-error expectations strong enough",
    "Does `XH-SANDBOX-PREFLIGHT-001` appear fixed",
    "Are there any critical/high findings",
    "can `ERG-003` move from `external_review_required`",
    "avoid approving live VM/container control",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "local model invocation",
    "Mission Control runtime behavior",
    "trusted-host promotion",
    "network expansion",
    "API/MCP profile loading",
    "production identity",
    "SIEM delivery",
    "compliance automation",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "live VM control is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
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
    disposition_plan = (
        repo_root / "docs/codex/sandbox-vm-static-preflight-disposition-plan.md"
    ).read_text(encoding="utf-8")
    packet_script = (
        repo_root / "scripts/sandbox_vm_static_preflight_source_review_packet.py"
    ).read_text(encoding="utf-8")
    enterprise = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("sandbox/VM static preflight external response intake doc is missing")
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

    if "sandbox-vm-static-preflight" not in external_response_normalize.AREA_NAMESPACES:
        failures.append("external response normalizer lacks sandbox-vm-static-preflight area")
    elif external_response_normalize.AREA_NAMESPACES["sandbox-vm-static-preflight"] != "SVP":
        failures.append("external response normalizer uses the wrong sandbox preflight namespace")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("sandbox/VM static preflight intake doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("sandbox/VM static preflight intake doc is missing from docs-site inputs")
    if DOC_REL not in packet_script:
        failures.append("static preflight source-review packet does not bundle intake doc")
    if DOC_NAME not in disposition_plan:
        failures.append("disposition plan does not point to the external response intake doc")
    if DOC_NAME not in enterprise:
        failures.append("enterprise runway is missing external response intake pointer")
    if DOC_NAME not in gap_matrix:
        failures.append("enterprise gap matrix is missing external response intake pointer")
    if "sandbox-vm-static-preflight-external-response-intake-check:" not in makefile:
        failures.append(
            "Make target is missing: "
            "sandbox-vm-static-preflight-external-response-intake-check"
        )
    if "sandbox-vm-static-preflight-external-response-intake-check" not in release_check_body:
        failures.append(
            "sandbox-vm-static-preflight-external-response-intake-check missing from release-check"
        )
    if "make sandbox-vm-static-preflight-external-response-intake-check" not in readme:
        failures.append("README is missing sandbox/VM static preflight intake command")
    if "sandbox-vm-static-preflight-external-response-intake.md" not in readme:
        failures.append("README is missing sandbox/VM static preflight intake doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "intake_doc": DOC_REL,
        "tool_count": 24,
        "area": "sandbox-vm-static-preflight",
        "finding_namespace": "EXT-SVP-###",
        "erg_003_status": "external_review_required",
        "mutates_findings": False,
        "closes_external_review": False,
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static preflight external response intake check",
        f"valid: {str(report['valid']).lower()}",
        f"intake_doc: {report['intake_doc']}",
        f"tool_count: {report['tool_count']}",
        f"area: {report['area']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"erg_003_status: {report['erg_003_status']}",
        f"mutates_findings: {str(report['mutates_findings']).lower()}",
        f"closes_external_review: {str(report['closes_external_review']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        "api_mcp_profile_loading_allowed: "
        f"{str(report['api_mcp_profile_loading_allowed']).lower()}",
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

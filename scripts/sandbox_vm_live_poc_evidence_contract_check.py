"""Validate the design-only live sandbox/VM POC evidence contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, review_docs, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-live-poc-evidence-contract.md"
DOC_NAME = "sandbox-vm-live-poc-evidence-contract.md"
DOC = ROOT / DOC_REL

REQUIRED_PHRASES = [
    "Status: design-only evidence contract for a future `ERG-004` live sandbox/VM worker proof of",
    "Current governed tool count: `24`.",
    "Current `ERG-004` status: `blocked`.",
    "Current selected capability: `not selected`.",
    "make sandbox-vm-live-poc-evidence-contract-check",
    "favorable `ERG-003` disposition",
    "PRD-SANDBOX-LIVE-POC-001",
    "operator-managed sandbox evidence",
    "Mission Control display evidence",
    "Ithildin run evidence",
    "Local model/client evidence",
    "decision_record_id",
    "ithildin.sandbox_vm_live_poc",
    "model_request_hash",
    "model_output_hash",
    "ithildin_audit_head",
    "ithildin_evidence_export_hash",
    "sandbox_transcript_hash",
    "cleanup_transcript_hash",
    "failure_transcript_hash",
    "mission_control_packet_hash",
    "promotion_status",
    "implementation_approved",
    "Cross-Source Correlation Requirements",
    "Required Negative Evidence",
    "runtime changes allowed: `false`",
    "live VM/container inspection allowed: `false`",
    "Mission Control runtime allowed: `false`",
    "local model invocation allowed: `false`",
    "sandbox orchestration allowed: `false`",
    "trusted-host promotion allowed: `false`",
    "SIEM adapter allowed: `false`",
    "public/security-product positioning allowed: `false`",
]

FORBIDDEN_PHRASES = [
    "production-ready",
    "compliance-grade",
    "secure sandbox",
    "tamper-proof",
    "live VM control is approved",
    "sandbox orchestration is approved",
    "local model invocation is approved",
    "Mission Control runtime behavior is approved",
    "trusted-host promotion is approved",
    "SIEM adapter is implemented",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    enterprise = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    if not DOC.exists():
        failures.append("sandbox/VM live POC evidence contract doc is missing")
        text = ""
    else:
        text = DOC.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"live POC evidence contract is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    f"live POC evidence contract contains forbidden phrase: {phrase}"
                )

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("sandbox/VM live POC evidence contract is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("sandbox/VM live POC evidence contract is missing from docs-site inputs")
    if DOC_NAME not in readme:
        failures.append("README is missing sandbox/VM live POC evidence contract")
    if "make sandbox-vm-live-poc-evidence-contract-check" not in readme:
        failures.append("README is missing sandbox/VM live POC evidence contract command")
    if "sandbox-vm-live-poc-evidence-contract-check:" not in makefile:
        failures.append("Make target is missing: sandbox-vm-live-poc-evidence-contract-check")
    if "sandbox-vm-live-poc-evidence-contract-check" not in release_check_body:
        failures.append("sandbox-vm-live-poc-evidence-contract-check missing from release-check")
    if DOC_NAME not in enterprise:
        failures.append("enterprise runway is missing live POC evidence contract pointer")
    if DOC_NAME not in gap_matrix:
        failures.append("enterprise gap matrix is missing live POC evidence contract pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "contract_doc": DOC_REL,
        "tool_count": tool_surface.get("tool_count"),
        "erg_004_status": "blocked",
        "scope": "design_only_evidence_contract",
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC evidence contract check",
        f"valid: {str(report['valid']).lower()}",
        f"contract_doc: {report['contract_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"scope: {report['scope']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


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


if __name__ == "__main__":
    raise SystemExit(main())

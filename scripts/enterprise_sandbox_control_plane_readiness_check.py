"""Validate the enterprise sandbox control-plane readiness map."""

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
DOC_REL = "docs/codex/enterprise-sandbox-control-plane-readiness.md"
DOC_NAME = "enterprise-sandbox-control-plane-readiness.md"
DOC = ROOT / DOC_REL

REQUIRED_PHRASES = [
    "Status: design-only readiness map for the post-v1.0 sandbox/control-plane path.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "Mission Control display lane",
    "sandbox/VM static preflight lane",
    "live sandbox/VM proof-of-concept lane",
    "trusted-host promotion lane",
    "`ERG-002` Mission Control display/importer",
    "`ERG-003` Sandbox/VM static preflight",
    "`ERG-004` Live sandbox/VM worker proof of concept",
    "`ERG-005` Trusted-host artifact promotion",
    "sandbox-vm-live-poc-decision-packet.md",
    "sandbox-vm-live-poc-response-dry-run.md",
    "make enterprise-sandbox-control-plane-readiness-check",
    "make sandbox-vm-live-poc-decision-packet-check",
    "does not approve live VM/container inspection",
    "does not approve sandbox orchestration",
    "does not approve local model invocation",
    "Mission Control may be discussed as a display/import planning surface only",
    "Ithildin manages or starts VMs, containers, local models, or sandboxes",
    "`ERG-003` receives favorable external/source disposition",
]

FORBIDDEN_PHRASES = [
    "live VM control is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "implementation approved",
    "production-ready",
    "secure sandbox",
    "compliance-grade",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    if not DOC.exists():
        failures.append("enterprise sandbox control-plane readiness doc is missing")
        text = ""
    else:
        text = DOC.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"readiness doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"readiness doc contains forbidden phrase: {phrase}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append(
            "enterprise sandbox control-plane readiness doc is missing from review docs"
        )
    if DOC_REL not in docs_site:
        failures.append("enterprise sandbox control-plane readiness doc is missing from docs site")
    if DOC_NAME not in readme:
        failures.append("README is missing enterprise sandbox control-plane readiness doc")
    if "make enterprise-sandbox-control-plane-readiness-check" not in readme:
        failures.append("README is missing enterprise sandbox control-plane readiness command")
    if "enterprise-sandbox-control-plane-readiness-check:" not in makefile:
        failures.append("Make target is missing: enterprise-sandbox-control-plane-readiness-check")
    if "enterprise-sandbox-control-plane-readiness-check" not in release_check_body:
        failures.append("enterprise sandbox readiness check missing from release-check")
    if "enterprise-sandbox-control-plane-readiness-check" not in release_guardrails:
        failures.append("release guardrails do not require enterprise sandbox readiness check")
    if DOC_NAME not in gap_matrix:
        failures.append("enterprise gap matrix is missing enterprise sandbox readiness pointer")
    if DOC_NAME not in runway:
        failures.append("enterprise runway is missing enterprise sandbox readiness pointer")
    if DOC_NAME not in register:
        failures.append("post-RC decision register is missing enterprise sandbox readiness pointer")
    if "Enterprise Sandbox Control-Plane Readiness" not in review_index:
        failures.append("review-docs index is missing enterprise sandbox readiness entry")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "readiness_doc": DOC_REL,
        "tool_count": tool_surface.get("tool_count"),
        "erg_002_status": "planning_only",
        "erg_003_status": "external_review_required",
        "erg_004_status": "blocked",
        "erg_005_status": "blocked",
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "closes_enterprise_gap": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise sandbox control-plane readiness check",
        f"valid: {str(report['valid']).lower()}",
        f"readiness_doc: {report['readiness_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_002_status: {report['erg_002_status']}",
        f"erg_003_status: {report['erg_003_status']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"closes_enterprise_gap: {str(report['closes_enterprise_gap']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


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

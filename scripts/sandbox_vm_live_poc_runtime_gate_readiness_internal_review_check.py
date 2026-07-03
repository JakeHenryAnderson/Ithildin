"""Validate the ERG-004 runtime gate-readiness internal High review record."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-internal-review.md"
DOC_TITLE = "Sandbox/VM Live POC Runtime Gate Readiness Internal Review"
TARGET = "sandbox-vm-live-poc-runtime-gate-readiness-internal-review-check"

REQUIRED_PHRASES = [
    "Status: internal High review disposition for the `ERG-004` runtime gate-readiness checkpoint.",
    "Current governed tool count: `24`.",
    "Reviewed commit: `60b644da7d0f647b925cb4127c71d716c8f4e7ed`.",
    "Disposition: `approve_internal_runtime_gate_readiness_review`.",
    "make sandbox-vm-live-poc-runtime-gate-readiness-internal-review-check",
    "Critical/high findings: none.",
    "Medium/low/documentation findings: none.",
    "runtime gate-readiness review bundle",
    "validating operator-supplied runtime descriptors",
    "correlating descriptor evidence with existing Agent Run, approval, audit, signed-export, and",
    "source-labeled as operator supplied, not Ithildin-observed",
    "not an external source-review closure",
    "not a product-readiness approval",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run",
    "The next allowed action is to prepare a committed descriptor-only implementation-planning",
]

REQUIRED_NON_APPROVALS = [
    "runtime implementation",
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation by Ithildin",
    "trusted-host promotion",
    "host writes or artifact promotion",
    "network expansion",
    "API/MCP profile loading",
    "SIEM adapter runtime behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "compliance automation",
    "shell, Docker, Kubernetes, or browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "plugin SDK behavior",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "runtime implementation is approved",
    "live VM/container inspection is approved",
    "VM/container lifecycle management is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "host writes are approved",
    "network expansion is approved",
    "API/MCP profile loading is approved",
    "new governed tool powers are approved",
    "external source-review closure is approved",
    "this review approves product readiness",
    "public security product approved",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    text = _read(doc_path)
    lowered = text.lower()
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    status_now = _read(repo_root / "scripts/status_now.py")
    operator_next = _read(repo_root / "scripts/enterprise_operator_next_action.py")

    if not doc_path.exists():
        failures.append("runtime gate-readiness internal review doc is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"internal review doc is missing phrase: {phrase}")
    for phrase in REQUIRED_NON_APPROVALS:
        if phrase not in text:
            failures.append(f"internal review doc is missing non-approval: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"internal review doc contains forbidden phrase: {phrase}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("internal review doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("internal review doc is missing from docs-site inputs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing runtime gate-readiness internal review")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append("internal review check missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require internal review check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing runtime gate-readiness internal review command")
    if DOC_REL not in readme:
        failures.append("README is missing runtime gate-readiness internal review doc")
    if TARGET not in status_now:
        failures.append("status-now route is missing runtime gate-readiness internal review check")
    if TARGET not in operator_next:
        failures.append(
            "operator next-action route is missing runtime gate-readiness internal "
            "review check"
        )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "internal_review_doc": DOC_REL,
        "tool_count": 24,
        "disposition": "approve_internal_runtime_gate_readiness_review",
        "critical_high_findings": 0,
        "medium_low_findings": 0,
        "external_review_closure": False,
        "product_readiness_approval": False,
        "descriptor_only_planning_next_step_allowed": True,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "host_writes_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC runtime gate-readiness internal review check",
        f"valid: {str(report['valid']).lower()}",
        f"internal_review_doc: {report['internal_review_doc']}",
        f"tool_count: {report['tool_count']}",
        f"disposition: {report['disposition']}",
        f"critical_high_findings: {report['critical_high_findings']}",
        f"medium_low_findings: {report['medium_low_findings']}",
        f"external_review_closure: {str(report['external_review_closure']).lower()}",
        f"product_readiness_approval: {str(report['product_readiness_approval']).lower()}",
        "descriptor_only_planning_next_step_allowed: "
        f"{str(report['descriptor_only_planning_next_step_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "vm_container_lifecycle_allowed: "
        f"{str(report['vm_container_lifecycle_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"host_writes_allowed: {str(report['host_writes_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        "api_mcp_profile_loading_allowed: "
        f"{str(report['api_mcp_profile_loading_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


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

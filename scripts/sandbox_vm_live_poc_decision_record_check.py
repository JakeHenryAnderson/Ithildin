"""Validate the committed ERG-004 live sandbox/VM POC decision record."""

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
DOC_REL = "docs/codex/sandbox-vm-live-poc-decision-record.md"
DOC_NAME = "sandbox-vm-live-poc-decision-record.md"
TARGET = "sandbox-vm-live-poc-decision-record-check"

REQUIRED_PHRASES = [
    "Status: committed decision record for `ERG-004` implementation-planning-only continuation.",
    "Decision ID: `PRD-SANDBOX-LIVE-POC-001`.",
    "Current governed tool count: `24`.",
    "Previous `ERG-004` status: `blocked`.",
    "Recorded `ERG-004` status: `ready_for_implementation_planning_only`.",
    "Current selected capability: `not selected`.",
    "make sandbox-vm-live-poc-decision-record-check",
    "Reviewed commit: `b9ba2a03763496876830b18c9e9e5bc82ed80e96`.",
    (
        "Reviewed packet hash: "
        "`sha256:b12459b7714912d8cfe40ff66a9e64370faa402e3d890add7da6631ca2ff817f`."
    ),
    "source_access: packet-and-source",
    "erg_003_favorable_disposition: true",
    "decision_outcome: approve_limited_operator_managed_poc_planning",
    "finding_count: 0",
    "closure_ready: true",
    "approved_for_implementation_planning_only",
    "ERG-004: blocked -> ready_for_implementation_planning_only",
    "VM-first framing:",
    "Container profiles are deferred",
    "make sandbox-vm-live-poc-implementation-plan-check",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "runtime implementation",
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "network expansion",
    "API/MCP profile loading",
    "SIEM adapter behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "compliance automation",
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
    "new governed tool powers are approved",
    "public security product approved",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    text = _read(doc_path)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    readiness = _read(repo_root / "docs/codex/enterprise-sandbox-control-plane-readiness.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("sandbox/VM live POC decision record is missing")
    lowered = text.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"decision record is missing phrase: {phrase}")
    for phrase in REQUIRED_BLOCKED_BOUNDARIES:
        if phrase not in text:
            failures.append(f"decision record is missing blocked boundary: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"decision record contains forbidden phrase: {phrase}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("decision record is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("decision record is missing from docs-site inputs")
    if "Sandbox/VM Live POC Decision Record" not in review_index:
        failures.append("review-docs index is missing live POC decision record")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append("decision record check missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require decision record check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing live POC decision record command")
    for label, source in [
        ("enterprise runway", runway),
        ("enterprise gap matrix", gap_matrix),
        ("post-RC decision register", decision_register),
        ("enterprise sandbox readiness", readiness),
    ]:
        if DOC_NAME not in source:
            failures.append(f"{label} is missing {DOC_NAME}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_record_doc": DOC_REL,
        "tool_count": 24,
        "erg_004_status": "ready_for_implementation_planning_only",
        "decision_outcome": "approved_for_implementation_planning_only",
        "vm_first": True,
        "container_profiles_deferred": True,
        "implementation_planning_allowed": True,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC decision record check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_record_doc: {report['decision_record_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"decision_outcome: {report['decision_outcome']}",
        f"vm_first: {str(report['vm_first']).lower()}",
        f"container_profiles_deferred: {str(report['container_profiles_deferred']).lower()}",
        "implementation_planning_allowed: "
        f"{str(report['implementation_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
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

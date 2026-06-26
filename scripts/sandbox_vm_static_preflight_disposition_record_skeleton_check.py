"""Validate the sandbox/VM static preflight disposition-record skeleton."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, sandbox_vm_static_preflight_disposition_closure_check

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-static-preflight-disposition-record-skeleton.md"
DOC_NAME = "sandbox-vm-static-preflight-disposition-record-skeleton.md"

REQUIRED_PHRASES = [
    "Status: design-only disposition-record skeleton for `ERG-003`.",
    "Current governed tool count: `24`.",
    "Current `ERG-003` status: `external_review_required`.",
    "Current selected capability: `not selected`.",
    "does not close `ERG-003` by itself",
    "var/review-runs/sandbox-vm-static-preflight/normalized-response.json",
    "make sandbox-vm-static-preflight-disposition-closure-check",
    "can_close_source_rows: true",
    "mutates_findings: false",
    "closes_external_review: false",
    "closed_local_preview_static_preflight",
    "ERG-003: external_review_required -> closed_local_preview_static_preflight",
    "CLI-only static sandbox/VM profile preflight lane has been externally/source reviewed",
    "Runtime surfaces touched: none.",
    "Tool count impact: none; remains `24`.",
    "sandbox-vm-static-preflight-triage-update.md",
    "ERG-004 remains blocked",
    "make sandbox-vm-static-preflight-disposition-record-skeleton-check",
    "make release-check",
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
    "new governed tool powers",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "SIEM adapter behavior",
    "compliance automation",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "runtime implementation is approved",
    "live VM/container inspection is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "SIEM adapter behavior is approved",
    "ERG-003 is closed",
    "ERG-004 is unblocked",
    "live POC planning is approved",
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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    disposition_plan = _read(
        repo_root / "docs/codex/sandbox-vm-static-preflight-disposition-plan.md"
    )
    closure_gate = _read(
        repo_root / "docs/codex/sandbox-vm-static-preflight-disposition-closure-gate.md"
    )
    triage_update = _read(repo_root / "docs/codex/sandbox-vm-static-preflight-triage-update.md")
    reproduction_map = _read(
        repo_root / "docs/codex/sandbox-vm-static-preflight-reviewer-reproduction-map.md"
    )
    response_kit = _read(repo_root / "docs/codex/sandbox-vm-static-preflight-response-kit.md")
    live_preconditions = _read(repo_root / "docs/codex/sandbox-vm-live-poc-preconditions-map.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    closure_report = sandbox_vm_static_preflight_disposition_closure_check.build_report(repo_root)

    if not doc_path.exists():
        failures.append("sandbox/VM static preflight disposition-record skeleton doc is missing")
        text = ""
    else:
        text = _read(doc_path)
        normalized_text = " ".join(text.split())
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized_text:
                failures.append(f"disposition-record skeleton is missing phrase: {phrase}")
        for phrase in REQUIRED_BLOCKED_BOUNDARIES:
            if phrase not in text:
                failures.append(
                    f"disposition-record skeleton is missing blocked boundary: {phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    f"disposition-record skeleton contains forbidden phrase: {phrase}"
                )

    if closure_report["erg_003_status"] != "external_review_required":
        failures.append("static preflight closure gate unexpectedly moved ERG-003")
    if closure_report["closure_ready"] is not False:
        failures.append("static preflight closure gate unexpectedly reports closure readiness")
    if closure_report["runtime_changes_allowed"] is not False:
        failures.append("static preflight closure gate unexpectedly allows runtime changes")
    if closure_report["new_power_classes_allowed"] is not False:
        failures.append("static preflight closure gate unexpectedly allows new power classes")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("static preflight disposition-record skeleton is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("static preflight disposition-record skeleton is missing from docs site")
    target = "sandbox-vm-static-preflight-disposition-record-skeleton-check"
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in release_check_body:
        failures.append(
            "static preflight disposition-record skeleton check missing from release-check"
        )
    if target not in release_guardrails:
        failures.append("release guardrails do not require static preflight skeleton check")
    if f"make {target}" not in readme:
        failures.append("README is missing static preflight skeleton command")
    if "Sandbox/VM Static Preflight Disposition Record Skeleton" not in review_index:
        failures.append("review docs index is missing static preflight skeleton")

    for label, source in [
        ("enterprise runway", runway),
        ("enterprise gap matrix", gap_matrix),
        ("enterprise external-review queue", queue),
        ("post-RC decision register", decision_register),
        ("disposition plan", disposition_plan),
        ("closure gate", closure_gate),
        ("triage update", triage_update),
        ("reviewer reproduction map", reproduction_map),
        ("response kit", response_kit),
        ("live POC preconditions map", live_preconditions),
    ]:
        if DOC_NAME not in source:
            failures.append(f"{label} is missing static preflight skeleton pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "disposition_record_skeleton_doc": DOC_REL,
        "tool_count": 24,
        "erg_003_status": "external_review_required",
        "allowed_future_status": "closed_local_preview_static_preflight",
        "runtime_changes_allowed": False,
        "implementation_planning_allowed_now": False,
        "static_preflight_disposition_after_favorable_review_allowed": True,
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
        "erg_004_unblocked": False,
        "closes_erg_003": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static preflight disposition-record skeleton check",
        f"valid: {str(report['valid']).lower()}",
        f"disposition_record_skeleton_doc: {report['disposition_record_skeleton_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
        f"allowed_future_status: {report['allowed_future_status']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "implementation_planning_allowed_now: "
        f"{str(report['implementation_planning_allowed_now']).lower()}",
        "static_preflight_disposition_after_favorable_review_allowed: "
        f"{str(report['static_preflight_disposition_after_favorable_review_allowed']).lower()}",
        f"runtime_implementation_allowed: {str(report['runtime_implementation_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"vm_container_lifecycle_allowed: {str(report['vm_container_lifecycle_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        "api_mcp_profile_loading_allowed: "
        f"{str(report['api_mcp_profile_loading_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"erg_004_unblocked: {str(report['erg_004_unblocked']).lower()}",
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

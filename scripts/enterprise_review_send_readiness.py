"""Summarize enterprise external-review packet send readiness."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    compliance_mapping_disposition_closure_check,
    compliance_mapping_external_review_bundle,
    compliance_mapping_response_kit,
    enterprise_next_review_ready_check,
    mission_control_display_next_review_ready_check,
    production_identity_storage_disposition_closure_check,
    production_identity_storage_external_review_bundle,
    production_identity_storage_response_kit,
    public_security_product_positioning_decision_closure_check,
    public_security_product_positioning_external_review_bundle,
    public_security_product_positioning_response_kit,
    sandbox_vm_live_poc_decision_closure_check,
    sandbox_vm_live_poc_external_review_bundle,
    sandbox_vm_live_poc_response_kit,
    siem_export_adapter_disposition_closure_check,
    siem_export_adapter_external_review_bundle,
    siem_export_adapter_response_kit,
    trusted_host_promotion_disposition_closure_check,
    trusted_host_promotion_external_review_bundle,
    trusted_host_promotion_response_kit,
)
from scripts.response_dry_run_lock import response_dry_run_lock

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-review-send-readiness.md"
DOC_TITLE = "Enterprise Review Send Readiness"

ReportBuilder = Callable[[Path], dict[str, Any]]


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
    with response_dry_run_lock(repo_root, "__enterprise_response_fixture_state__"):
        return _build_report_locked(repo_root)


def _build_report_locked(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    erg003 = enterprise_next_review_ready_check.build_report(repo_root)
    erg002 = mission_control_display_next_review_ready_check.build_report(repo_root)

    rows = [
        _ready_row(
            gap="ERG-003",
            status="external_review_required",
            packet=erg003,
            recommended_now=True,
            path=erg003.get("recommended_packet"),
            note="current recommended enterprise review",
        ),
        _ready_row(
            gap="ERG-002",
            status="planning_only",
            packet=erg002,
            recommended_now=True,
            path=erg002.get("recommended_packet"),
            note="parallel Mission Control display/import planning review",
        ),
        _bundle_row(
            repo_root,
            gap="ERG-005",
            status="blocked",
            bundle=trusted_host_promotion_external_review_bundle.build_check_report,
            response_kit=trusted_host_promotion_response_kit.build_check_report,
            closure=trusted_host_promotion_disposition_closure_check.build_report,
            recommended_now=False,
            note="blocked trusted-host promotion design review lane",
        ),
        _bundle_row(
            repo_root,
            gap="ERG-006/ERG-007",
            status="planning_only",
            bundle=production_identity_storage_external_review_bundle.build_check_report,
            response_kit=production_identity_storage_response_kit.build_check_report,
            closure=production_identity_storage_disposition_closure_check.build_report,
            recommended_now=False,
            note="architecture review lane for identity and storage",
        ),
        _bundle_row(
            repo_root,
            gap="ERG-008",
            status="planning_only",
            bundle=siem_export_adapter_external_review_bundle.build_check_report,
            response_kit=siem_export_adapter_response_kit.build_check_report,
            closure=siem_export_adapter_disposition_closure_check.build_report,
            recommended_now=False,
            note="architecture review lane for offline/export adapter design",
        ),
        _bundle_row(
            repo_root,
            gap="ERG-009",
            status="planning_only",
            bundle=compliance_mapping_external_review_bundle.build_check_report,
            response_kit=compliance_mapping_response_kit.build_check_report,
            closure=compliance_mapping_disposition_closure_check.build_report,
            recommended_now=False,
            note="architecture review lane for control-mapping support",
        ),
        _bundle_row(
            repo_root,
            gap="ERG-004",
            status="blocked",
            bundle=sandbox_vm_live_poc_external_review_bundle.build_check_report,
            response_kit=sandbox_vm_live_poc_response_kit.build_check_report,
            closure=sandbox_vm_live_poc_decision_closure_check.build_report,
            recommended_now=False,
            note="blocked until favorable ERG-003 disposition",
        ),
        _bundle_row(
            repo_root,
            gap="ERG-010",
            status="blocked",
            bundle=public_security_product_positioning_external_review_bundle.build_check_report,
            response_kit=public_security_product_positioning_response_kit.build_check_report,
            closure=public_security_product_positioning_decision_closure_check.build_report,
            recommended_now=False,
            note="blocked public/security-product positioning claim review",
        ),
    ]

    for row in rows:
        if not row["packet_handoff_ready"]:
            failures.append(f"{row['gap']} packet handoff is not ready")
        if row["implementation_allowed"] is not False:
            failures.append(f"{row['gap']} must not allow implementation from send readiness")
        if row["closure_ready"] is not False:
            failures.append(f"{row['gap']} closure is unexpectedly ready")
        if row["normalized_response_present"] is not False:
            failures.append(f"{row['gap']} has normalized response evidence; intake it first")

    recommended = [row["gap"] for row in rows if row["recommended_to_send_now"]]
    if recommended != ["ERG-003", "ERG-002"]:
        failures.append("recommended send order must remain ERG-003 then ERG-002")

    for phrase in [
        "Status: operator send-readiness summary for enterprise external-review lanes.",
        "Current governed tool count: `24`.",
        "make enterprise-review-send-readiness",
        "packet handoff ready is not implementation approval",
        "`ERG-003`",
        "`ERG-002`",
        "`ERG-004` remains blocked",
        "does not close any ERG lane",
        "does not approve Mission Control runtime behavior",
        "does not approve live VM/container inspection",
        "does not approve trusted-host promotion",
    ]:
        if phrase not in doc:
            failures.append(f"send-readiness doc is missing phrase: {phrase}")

    if "enterprise-review-send-readiness:" not in makefile:
        failures.append("Make target is missing: enterprise-review-send-readiness")
    if "enterprise-review-send-readiness" not in release_check_body:
        failures.append("enterprise-review-send-readiness missing from release-check")
    if "make enterprise-review-send-readiness" not in readme:
        failures.append("README is missing enterprise review send-readiness command")
    if DOC_REL not in docs_site:
        failures.append("enterprise review send-readiness missing from docs-site inputs")
    if DOC_REL not in review_docs:
        failures.append("enterprise review send-readiness missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise review send-readiness")
    if "enterprise-review-send-readiness" not in release_guardrails:
        failures.append("release guardrails do not require enterprise review send-readiness")
    if "enterprise-review-send-readiness.md" not in queue:
        failures.append("enterprise external-review queue does not point to send-readiness summary")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "summary_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": "not selected",
        "lane_count": len(rows),
        "packet_handoff_ready_count": sum(1 for row in rows if row["packet_handoff_ready"]),
        "recommended_now": recommended,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
        "rows": rows,
    }


def _ready_row(
    *,
    gap: str,
    status: str,
    packet: dict[str, Any],
    recommended_now: bool,
    path: object,
    note: str,
) -> dict[str, Any]:
    return {
        "gap": gap,
        "status": status,
        "packet_path": str(path),
        "packet_valid": packet.get("valid") is True,
        "response_kit_valid": True,
        "closure_gate_valid": packet.get("valid") is True,
        "packet_handoff_ready": packet.get("ready_to_send") is True,
        "recommended_to_send_now": recommended_now,
        "normalized_response_present": packet.get("normalized_response_present"),
        "closure_ready": packet.get("closure_ready"),
        "implementation_allowed": False,
        "runtime_changes_allowed": False,
        "note": note,
    }


def _bundle_row(
    repo_root: Path,
    *,
    gap: str,
    status: str,
    bundle: ReportBuilder,
    response_kit: ReportBuilder,
    closure: ReportBuilder,
    recommended_now: bool,
    note: str,
) -> dict[str, Any]:
    bundle_report = bundle(repo_root)
    response_report = response_kit(repo_root)
    closure_report = closure(repo_root)
    packet_ready = (
        bundle_report.get("valid") is True
        and response_report.get("valid") is True
        and closure_report.get("valid") is True
        and closure_report.get("normalized_response_present") is False
        and closure_report.get("closure_ready") is False
    )
    return {
        "gap": gap,
        "status": status,
        "packet_path": bundle_report.get("output_dir"),
        "packet_valid": bundle_report.get("valid") is True,
        "response_kit_valid": response_report.get("valid") is True,
        "closure_gate_valid": closure_report.get("valid") is True,
        "packet_handoff_ready": packet_ready,
        "recommended_to_send_now": recommended_now,
        "normalized_response_present": closure_report.get("normalized_response_present"),
        "closure_ready": closure_report.get("closure_ready"),
        "implementation_allowed": False,
        "runtime_changes_allowed": False,
        "note": note,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review send-readiness",
        f"valid: {str(report['valid']).lower()}",
        f"summary_doc: {report['summary_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        f"lane_count: {report['lane_count']}",
        f"packet_handoff_ready_count: {report['packet_handoff_ready_count']}",
        "recommended_now: " + ", ".join(report["recommended_now"]),
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "lanes:",
    ]
    for row in report["rows"]:
        lines.append(
            "- {gap}: packet_handoff_ready={ready} recommended_now={recommended} "
            "closure_ready={closure_ready} path={path}".format(
                gap=row["gap"],
                ready=str(row["packet_handoff_ready"]).lower(),
                recommended=str(row["recommended_to_send_now"]).lower(),
                closure_ready=str(row["closure_ready"]).lower(),
                path=row["packet_path"],
            )
        )
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())

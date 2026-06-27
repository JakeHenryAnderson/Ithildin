"""Report normalized-response status across enterprise external-review lanes."""

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
    mission_control_display_disposition_closure_check,
    production_identity_storage_disposition_closure_check,
    public_security_product_positioning_decision_closure_check,
    sandbox_vm_live_poc_decision_closure_check,
    sandbox_vm_static_preflight_disposition_closure_check,
    siem_export_adapter_disposition_closure_check,
    trusted_host_promotion_disposition_closure_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-response-status-board.md"
DOC_TITLE = "Enterprise Response Status Board"

ClosureBuilder = Callable[[Path], dict[str, Any]]


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
    rows = [
        _row(
            repo_root,
            gap="ERG-003",
            area="sandbox-vm-static-preflight",
            closure=sandbox_vm_static_preflight_disposition_closure_check.build_report,
            closure_command="make sandbox-vm-static-preflight-disposition-closure-check",
            dry_run_command="make sandbox-vm-static-preflight-response-dry-run",
            intake_doc="docs/codex/sandbox-vm-static-preflight-external-response-intake.md",
        ),
        _row(
            repo_root,
            gap="ERG-002",
            area="mission-control-display",
            closure=mission_control_display_disposition_closure_check.build_report,
            closure_command="make mission-control-display-disposition-closure-check",
            dry_run_command="make mission-control-display-response-dry-run",
            intake_doc="docs/codex/mission-control-display-external-response-intake.md",
        ),
        _row(
            repo_root,
            gap="ERG-005",
            area="trusted-host-promotion",
            closure=trusted_host_promotion_disposition_closure_check.build_report,
            closure_command="make trusted-host-promotion-disposition-closure-check",
            dry_run_command="make trusted-host-promotion-response-dry-run",
            intake_doc="docs/codex/trusted-host-promotion-external-response-intake.md",
        ),
        _row(
            repo_root,
            gap="ERG-006/ERG-007",
            area="production-identity-storage",
            closure=production_identity_storage_disposition_closure_check.build_report,
            closure_command="make production-identity-storage-disposition-closure-check",
            dry_run_command="make production-identity-storage-response-dry-run",
            intake_doc="docs/codex/production-identity-storage-external-response-intake.md",
        ),
        _row(
            repo_root,
            gap="ERG-008",
            area="siem-export-adapter",
            closure=siem_export_adapter_disposition_closure_check.build_report,
            closure_command="make siem-export-adapter-disposition-closure-check",
            dry_run_command="make siem-export-adapter-response-dry-run",
            intake_doc="docs/codex/siem-export-adapter-external-response-intake.md",
        ),
        _row(
            repo_root,
            gap="ERG-009",
            area="compliance-mapping",
            closure=compliance_mapping_disposition_closure_check.build_report,
            closure_command="make compliance-mapping-disposition-closure-check",
            dry_run_command="make compliance-mapping-response-dry-run",
            intake_doc="docs/codex/compliance-mapping-external-response-intake.md",
        ),
        _row(
            repo_root,
            gap="ERG-004",
            area="sandbox-vm-live-poc",
            closure=sandbox_vm_live_poc_decision_closure_check.build_report,
            closure_command="make sandbox-vm-live-poc-decision-closure-check",
            dry_run_command="make sandbox-vm-live-poc-response-dry-run",
            intake_doc="docs/codex/sandbox-vm-live-poc-external-response-intake.md",
        ),
        _row(
            repo_root,
            gap="ERG-010",
            area="public-security-product-positioning",
            closure=public_security_product_positioning_decision_closure_check.build_report,
            closure_command="make public-security-product-positioning-decision-closure-check",
            dry_run_command="make public-security-product-positioning-response-kit",
            intake_doc="docs/codex/public-security-product-positioning-decision-intake.md",
        ),
    ]

    failures: list[str] = []
    for row in rows:
        if row["closure_valid"] is not True:
            failures.append(f"{row['gap']} closure gate is not valid")
        if row["response_present"]:
            failures.append(f"{row['gap']} normalized response is present; run lane intake")
        if row["closure_ready"]:
            failures.append(f"{row['gap']} closure is ready; run lane-specific closure flow")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    dual_response = _read(repo_root / "docs/codex/enterprise-dual-response-readiness.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    for phrase in [
        "Status: read-only status board for enterprise normalized-response paths.",
        "make enterprise-response-status-board",
        "does not normalize raw reviewer text",
        "does not write response files",
        "does not mutate findings",
        "does not close any enterprise lane",
        "does not approve Mission Control runtime behavior",
        "does not approve live VM/container inspection",
        "does not approve trusted-host promotion",
    ]:
        if phrase not in doc:
            failures.append(f"response status board doc is missing phrase: {phrase}")
    if "enterprise-response-status-board:" not in makefile:
        failures.append("Make target is missing: enterprise-response-status-board")
    if "enterprise-response-status-board" not in release_check_body:
        failures.append("enterprise-response-status-board is missing from release-check")
    if "$(MAKE) enterprise-response-status-board" not in review_candidate_body:
        failures.append("enterprise-response-status-board is missing from review-candidate")
    if "make enterprise-response-status-board" not in readme:
        failures.append("README is missing enterprise response status board command")
    if DOC_REL not in docs_site:
        failures.append("enterprise response status board is missing from docs-site inputs")
    if DOC_REL not in review_docs:
        failures.append("enterprise response status board is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise response status board")
    if "enterprise-response-status-board" not in release_guardrails:
        failures.append("release guardrails do not require enterprise response status board")
    if "enterprise-response-status-board" not in queue:
        failures.append("enterprise external-review queue is missing response status board")
    if "enterprise-response-status-board" not in dual_response:
        failures.append("dual-response readiness doc is missing response status board pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "summary_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": "not selected",
        "lane_count": len(rows),
        "response_present_count": sum(1 for row in rows if row["response_present"]),
        "closure_ready_count": sum(1 for row in rows if row["closure_ready"]),
        "committed_findings_mutated": False,
        "external_review_recorded": False,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
        "rows": rows,
    }


def _row(
    repo_root: Path,
    *,
    gap: str,
    area: str,
    closure: ClosureBuilder,
    closure_command: str,
    dry_run_command: str,
    intake_doc: str,
) -> dict[str, Any]:
    closure_report = closure(repo_root)
    response_present = closure_report.get("normalized_response_present") is True
    closure_ready = closure_report.get("closure_ready") is True
    if closure_ready:
        recommended_next = closure_command
    elif response_present:
        recommended_next = dry_run_command
    else:
        recommended_next = "wait_for_external_response"
    return {
        "gap": gap,
        "area": area,
        "normalized_response_path": closure_report.get("normalized_response_path"),
        "response_present": response_present,
        "closure_ready": closure_ready,
        "closure_valid": closure_report.get("valid") is True,
        "recommended_next": recommended_next,
        "intake_doc": intake_doc,
        "mutates_findings": False,
        "closes_external_review": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise response status board",
        f"valid: {str(report['valid']).lower()}",
        f"summary_doc: {report['summary_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        f"lane_count: {report['lane_count']}",
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        f"committed_findings_mutated: {str(report['committed_findings_mutated']).lower()}",
        f"external_review_recorded: {str(report['external_review_recorded']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
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
            "- {gap}: response_present={present} closure_ready={ready} "
            "recommended_next={next_step}".format(
                gap=row["gap"],
                present=str(row["response_present"]).lower(),
                ready=str(row["closure_ready"]).lower(),
                next_step=row["recommended_next"],
            )
        )
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

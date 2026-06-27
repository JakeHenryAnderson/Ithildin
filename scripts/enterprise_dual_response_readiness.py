"""Summarize response-readiness for the current dual enterprise-review handoff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_dual_review_handoff,
    mission_control_display_disposition_closure_check,
    mission_control_display_response_dry_run,
    sandbox_vm_static_preflight_disposition_closure_check,
    sandbox_vm_static_preflight_response_dry_run,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-dual-response-readiness.md"
DOC_TITLE = "Enterprise Dual Response Readiness"


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
    handoff = enterprise_dual_review_handoff.build_check_report(repo_root)
    erg003_closure = sandbox_vm_static_preflight_disposition_closure_check.build_report(repo_root)
    erg003_dry_run = sandbox_vm_static_preflight_response_dry_run.run_dry_run(repo_root)
    erg002_closure = mission_control_display_disposition_closure_check.build_report(repo_root)
    erg002_dry_run = mission_control_display_response_dry_run.run_dry_run(repo_root)

    rows = [
        _row(
            gap="ERG-003",
            area="sandbox-vm-static-preflight",
            normalized_response_path=erg003_closure["normalized_response_path"],
            response_present=erg003_closure["normalized_response_present"],
            closure_ready=erg003_closure["closure_ready"],
            closure_valid=erg003_closure["valid"],
            dry_run_valid=erg003_dry_run["valid"],
            next_when_present="make sandbox-vm-static-preflight-response-dry-run",
            next_when_ready="make sandbox-vm-static-preflight-disposition-closure-check",
            intake_doc="docs/codex/sandbox-vm-static-preflight-external-response-intake.md",
        ),
        _row(
            gap="ERG-002",
            area="mission-control-display",
            normalized_response_path=erg002_closure["normalized_response_path"],
            response_present=erg002_closure["normalized_response_present"],
            closure_ready=erg002_closure["closure_ready"],
            closure_valid=erg002_closure["valid"],
            dry_run_valid=erg002_dry_run["valid"],
            next_when_present="make mission-control-display-response-dry-run",
            next_when_ready="make mission-control-display-disposition-closure-check",
            intake_doc="docs/codex/mission-control-display-external-response-intake.md",
        ),
    ]

    if handoff["valid"] is not True:
        failures.append("enterprise dual-review handoff is not valid")
    for row in rows:
        if row["dry_run_valid"] is not True:
            failures.append(f"{row['gap']} dry-run check failed")
        if row["closure_valid"] is not True and not row["response_present"]:
            failures.append(f"{row['gap']} closure gate failed before response is present")
        if row["closure_ready"] and not row["response_present"]:
            failures.append(f"{row['gap']} cannot be closure-ready without a response")
    if any(row["closure_ready"] for row in rows):
        failures.append("response is closure-ready; process it with the lane-specific intake path")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    dual_handoff_doc = _read(repo_root / "docs/codex/enterprise-dual-review-handoff.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    for phrase in [
        "Status: operator response-readiness summary for the dual enterprise review handoff.",
        "make enterprise-dual-response-readiness",
        "`ERG-003`",
        "`ERG-002`",
        "does not record review",
        "does not mutate findings",
        "does not close either lane",
        "does not approve Mission Control runtime behavior",
        "does not approve live VM/container inspection",
    ]:
        if phrase not in doc:
            failures.append(f"dual response-readiness doc is missing phrase: {phrase}")
    if "enterprise-dual-response-readiness:" not in makefile:
        failures.append("Make target is missing: enterprise-dual-response-readiness")
    if "enterprise-dual-response-readiness" not in release_check_body:
        failures.append("enterprise-dual-response-readiness is missing from release-check")
    if "$(MAKE) enterprise-dual-response-readiness" not in review_candidate_body:
        failures.append("enterprise-dual-response-readiness is missing from review-candidate")
    if "make enterprise-dual-response-readiness" not in readme:
        failures.append("README is missing enterprise dual-response readiness command")
    if DOC_REL not in docs_site:
        failures.append("enterprise dual-response readiness is missing from docs-site inputs")
    if DOC_REL not in review_docs:
        failures.append("enterprise dual-response readiness is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise dual-response readiness")
    if "enterprise-dual-response-readiness" not in release_guardrails:
        failures.append("release guardrails do not require enterprise dual-response readiness")
    if "enterprise-dual-response-readiness" not in dual_handoff_doc:
        failures.append("dual-review handoff doc is missing response-readiness pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "summary_doc": DOC_REL,
        "tool_count": 24,
        "recommended_gaps": ["ERG-003", "ERG-002"],
        "response_present_count": sum(1 for row in rows if row["response_present"]),
        "closure_ready_count": sum(1 for row in rows if row["closure_ready"]),
        "rows": rows,
        "committed_findings_mutated": False,
        "external_review_recorded": False,
        "closes_erg_003": False,
        "closes_erg_002": False,
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
    }


def _row(
    *,
    gap: str,
    area: str,
    normalized_response_path: str,
    response_present: bool,
    closure_ready: bool,
    closure_valid: bool,
    dry_run_valid: bool,
    next_when_present: str,
    next_when_ready: str,
    intake_doc: str,
) -> dict[str, Any]:
    if closure_ready:
        recommended_next = next_when_ready
    elif response_present:
        recommended_next = next_when_present
    else:
        recommended_next = "wait_for_external_response"
    return {
        "gap": gap,
        "area": area,
        "normalized_response_path": normalized_response_path,
        "response_present": response_present,
        "closure_ready": closure_ready,
        "closure_valid": closure_valid,
        "dry_run_valid": dry_run_valid,
        "recommended_next": recommended_next,
        "intake_doc": intake_doc,
        "mutates_findings": False,
        "closes_external_review": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise dual-response readiness",
        f"valid: {str(report['valid']).lower()}",
        f"summary_doc: {report['summary_doc']}",
        f"tool_count: {report['tool_count']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        f"committed_findings_mutated: {str(report['committed_findings_mutated']).lower()}",
        f"external_review_recorded: {str(report['external_review_recorded']).lower()}",
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
        f"closes_erg_002: {str(report['closes_erg_002']).lower()}",
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
        "rows:",
    ]
    for row in report["rows"]:
        lines.append(
            "- {gap}: response_present={present} closure_ready={ready} "
            "dry_run_valid={dry_run} recommended_next={next_step}".format(
                gap=row["gap"],
                present=str(row["response_present"]).lower(),
                ready=str(row["closure_ready"]).lower(),
                dry_run=str(row["dry_run_valid"]).lower(),
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

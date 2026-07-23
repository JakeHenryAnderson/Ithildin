"""Validate the Mission Control enterprise status import contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import enterprise_status_export, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/mission-control-enterprise-status-import-contract.md"
DOC_TITLE = "Mission Control Enterprise Status Import Contract"

ALLOWED_IMPORT_FIELDS = [
    "schema_version",
    "artifact_type",
    "status",
    "git",
    "tool_count",
    "selected_capability",
    "recommended_send_set",
    "recommended_next_enterprise_review",
    "next_action",
    "action_commands",
    "next_after_send_commands",
    "handoff_artifacts",
    "operator_next_action_doc",
    "response_present_count",
    "closure_ready_count",
    "enterprise_gap_count",
    "progress_bands",
    "review_candidate_state",
    "review_lanes",
    "packet_paths",
]

BOUNDARY_FLAGS = {
    "runtime_changes_allowed": False,
    "mission_control_runtime_allowed": False,
    "mission_control_execution_allowed": False,
    "mission_control_policy_authority_allowed": False,
    "mission_control_approval_authority_allowed": False,
    "mission_control_audit_authority_allowed": False,
    "polling_or_mutating_ithildin_apis_allowed": False,
    "local_model_invocation_allowed": False,
    "live_vm_inspection_allowed": False,
    "sandbox_orchestration_allowed": False,
    "trusted_host_promotion_allowed": False,
    "siem_adapter_allowed": False,
    "compliance_automation_allowed": False,
    "public_security_product_positioning_allowed": False,
    "new_power_classes_allowed": False,
    "sol_ultra_user_approval_obtained": False,
    "closure_findings_dispositioned": False,
    "closure_review_dispatch_allowed": False,
    "human_uat_allowed": False,
}

REQUIRED_DOC_PHRASES = [
    "Status: display-only contract for future Mission Control enterprise status imports.",
    "make mission-control-enterprise-status-import-check",
    "make enterprise-status-export",
    "artifact_type: ithildin.enterprise_status_export",
    "status: display_only",
    "Ithildin remains the execution, policy, approval, audit, and lane closure authority",
    "does not approve Mission Control enterprise status importer implementation",
    "Mission Control may display this artifact as non-authoritative status",
    "safe action commands",
    "current_source",
    "latest_recorded",
    "Historical packet evidence must not be converted into current-source readiness",
    "handoff artifact labels",
    "must not use it to execute work",
    "must not use it to poll Ithildin",
    "must not use it to invoke a model",
    "must not use it to inspect a VM/container",
    "must not use it to promote host artifacts",
    "must not use it to close review lanes",
    "must not use it to approve runtime behavior",
    "must not use it to grant new tool powers",
]

FORBIDDEN_DOC_PHRASES = [
    "Mission Control may execute",
    "Mission Control may approve",
    "Mission Control may poll Ithildin",
    "Mission Control may close review lanes",
    "Mission Control runtime authority",
    "runtime importer behavior is approved",
    "production-ready",
    "compliance-grade",
    "secure sandbox",
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
    export = enterprise_status_export.build_report(repo_root)

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    enterprise_doc = _read(repo_root / enterprise_status_export.DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    failures.extend(f"enterprise-status-export: {failure}" for failure in export["failures"])
    if export.get("artifact_type") != "ithildin.enterprise_status_export":
        failures.append("enterprise status export artifact_type drifted")
    if export.get("status") != "display_only":
        failures.append("enterprise status export status must remain display_only")
    if export.get("tool_count") != 24:
        failures.append("enterprise status export tool count is not 24")
    if export.get("response_present_count") != 0:
        failures.append("enterprise status import expects no normalized responses yet")
    if export.get("closure_ready_count") != 0:
        failures.append("enterprise status import expects no closure-ready lanes yet")
    review_candidate_state = export.get("review_candidate_state")
    if not isinstance(review_candidate_state, dict):
        failures.append("enterprise status export review_candidate_state is missing")
        review_candidate_state = {}
    current_source = review_candidate_state.get("current_source")
    latest_recorded = review_candidate_state.get("latest_recorded")
    if not isinstance(current_source, dict):
        failures.append("current_source review-candidate state is missing")
        current_source = {}
    if not isinstance(latest_recorded, dict):
        failures.append("latest_recorded review-candidate state is missing")
        latest_recorded = {}
    if latest_recorded.get("packet_record_ready") is not True:
        failures.append("latest recorded historical packet record is not ready")
    if current_source.get("packet_ready") is True and (
        current_source.get("mcc_006_valid") is not True
        or current_source.get("immutable_packet_valid") is not True
    ):
        failures.append("current-source packet readiness is not supported by current evidence")
    for key in [
        "sol_ultra_user_approval_obtained",
        "closure_findings_dispositioned",
        "closure_review_dispatch_allowed",
        "human_uat_allowed",
    ]:
        if review_candidate_state.get(key) is not False:
            failures.append(f"review-candidate state authority drifted: {key}")

    export_forbidden_true = [
        "runtime_changes_allowed",
        "mission_control_runtime_allowed",
        "live_vm_inspection_allowed",
        "sandbox_orchestration_allowed",
        "trusted_host_promotion_allowed",
        "siem_adapter_allowed",
        "compliance_automation_allowed",
        "public_security_product_positioning_allowed",
        "new_power_classes_allowed",
    ]
    for key in export_forbidden_true:
        if export.get(key) is not False:
            failures.append(f"enterprise status export boundary flag drifted: {key}")

    if not doc:
        failures.append("Mission Control enterprise status import contract doc is missing")
    else:
        lowered = doc.lower()
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in doc:
                failures.append(f"enterprise status import contract is missing phrase: {phrase}")
        for phrase in FORBIDDEN_DOC_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    f"enterprise status import contract contains forbidden phrase: {phrase}"
                )

    if "mission-control-enterprise-status-import-check:" not in makefile:
        failures.append("Make target is missing: mission-control-enterprise-status-import-check")
    if (
        "mission-control-enterprise-status-import-check" not in release_check_body
        and "release-check: mission-control-enterprise-status-import-check" not in makefile
    ):
        failures.append("enterprise status import check is missing from release-check")
    if "$(MAKE) mission-control-enterprise-status-import-check" not in review_candidate_body:
        failures.append("enterprise status import check is missing from review-candidate")
    if "make mission-control-enterprise-status-import-check" not in readme:
        failures.append("README is missing enterprise status import command")
    if DOC_REL not in readme:
        failures.append("README is missing enterprise status import doc")
    if DOC_REL not in docs_site:
        failures.append("enterprise status import contract is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise status import contract is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise status import contract")
    if "mission-control-enterprise-status-import-check" not in release_guardrails:
        failures.append("release guardrails do not require enterprise status import check")
    if "mission-control-enterprise-status-import" not in enterprise_doc:
        failures.append("enterprise status export doc is missing import contract pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "contract_doc": DOC_REL,
        "source_artifact_type": export.get("artifact_type"),
        "source_status": export.get("status"),
        "tool_count": export.get("tool_count"),
        "allowed_import_fields": ALLOWED_IMPORT_FIELDS,
        "recommended_send_set": export.get("recommended_send_set"),
        "recommended_next_enterprise_review": export.get(
            "recommended_next_enterprise_review"
        ),
        "response_present_count": export.get("response_present_count"),
        "closure_ready_count": export.get("closure_ready_count"),
        "review_candidate_state": review_candidate_state,
        **BOUNDARY_FLAGS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control enterprise status import check",
        f"valid: {str(report['valid']).lower()}",
        f"contract_doc: {report['contract_doc']}",
        f"source_artifact_type: {report['source_artifact_type']}",
        f"source_status: {report['source_status']}",
        f"tool_count: {report['tool_count']}",
        "recommended_send_set: " + ", ".join(report["recommended_send_set"]),
        "recommended_next_enterprise_review: "
        f"{report['recommended_next_enterprise_review']}",
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
    ]
    lines.extend(f"{key}: {str(value).lower()}" for key, value in BOUNDARY_FLAGS.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

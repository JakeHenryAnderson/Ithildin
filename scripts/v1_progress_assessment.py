"""Validate the v1.0 progress-assessment snapshot and wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_operator_next_action,
    enterprise_readiness_gap_matrix_check,
    enterprise_review_send_preflight,
    next_capability_readiness,
    review_docs,
    v1_operator_trial_observed,
    v1_rc_status_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs/codex/v1.0-progress-assessment.md"
POST_DISPOSITION_MODE = "post_disposition_next_review"
PIS_002_ENTRY_DECISION_MODE = "pis_002_entry_decision_preparation"
PIS_003_ENTRY_DECISION_MODE = "pis_003_entry_decision_preparation"
PIS_003_EXTERNAL_INPUT_MODE = "pis_003_external_operator_input_wait"

REQUIRED_PHRASES = [
    "Status: conservative progress-assessment snapshot",
    "Governed tool count: `24`",
    "Latest implemented tool: `sandbox.artifact.write_text`",
    "Selected next capability: `not selected`",
    "Capability expansion: blocked",
    "Runtime changes: blocked",
    "Public/security-product positioning: blocked",
    "Enterprise readiness gap count: `10`",
    "Recommended next enterprise work: wait for external target identity and signed receipts",
    "Historical/fallback review route: `ERG-003` and `ERG-002`",
    "Core governed local tool gateway | `92-96%`",
    "v1.0 local-preview RC foundation | `84-90%`",
    "Operator workbench and local demo experience | `78-86%`",
    "Mission Control plus Ithildin integration path | `50-65%`",
    "Sandbox/VM governed agent workflow | `45-60%`",
    "Enterprise/security-product readiness | `35-50%`",
    "Full long-term governed-agent workbench vision | `55-65%`",
    "Technical MVP state: `operator_trial_observed`",
    "Enterprise send package ready: `true`",
    "same-commit `make release-check` and `make review-candidate`",
    "valid `PIS-002` continuation decision",
    "Mission Control remains a display/import layer",
    "Blocked Claims",
]

BLOCKED_PHRASES = [
    "production deployment readiness",
    "production identity or enterprise RBAC",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP hosting",
    "Ithildin-managed VM/container lifecycle",
    "Mission Control execution authority",
    "trusted-host promotion",
    "SIEM custody",
    "HIPAA/GLBA/SOX/GDPR compliance automation",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "enterprise-ready",
    "production-ready",
    "compliance-grade",
    "tamper-proof",
    "secure sandbox",
    "approved for live VM",
    "Mission Control may execute",
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
    status = v1_rc_status_check.build_report(repo_root)
    gap_matrix = enterprise_readiness_gap_matrix_check.build_report(repo_root)
    capability = next_capability_readiness.build_report(repo_root)
    observed_trial = v1_operator_trial_observed.build_observed_record(
        repo_root,
        repo_root / "var/review-packets/v1.0/operator-trial-observed",
        write_artifacts=False,
    )
    enterprise_send = enterprise_review_send_preflight.build_report(repo_root)
    operator_next = enterprise_operator_next_action.build_report(repo_root)

    failures.extend(f"v1-rc-status: {failure}" for failure in status["failures"])
    failures.extend(f"enterprise-gap-matrix: {failure}" for failure in gap_matrix["failures"])
    failures.extend(f"next-capability: {failure}" for failure in capability["failures"])
    failures.extend(
        f"v1-operator-trial-observed: {failure}" for failure in observed_trial["failures"]
    )
    failures.extend(
        f"enterprise-review-send-preflight: {failure}" for failure in enterprise_send["failures"]
    )
    failures.extend(
        f"enterprise-operator-next-action: {failure}" for failure in operator_next["failures"]
    )

    doc_rel = DOC_PATH.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if status.get("tool_count") != 24:
        failures.append("v1 status tool count is not 24")
    if gap_matrix.get("gap_count") != 10:
        failures.append("enterprise gap count is not 10")
    if capability.get("next_candidate") != "not selected":
        failures.append("next capability candidate is selected")
    if capability.get("next_candidate_implementation_allowed"):
        failures.append("next capability implementation is allowed")
    if status.get("runtime_changes_allowed"):
        failures.append("runtime changes are allowed")
    if status.get("public_security_product_positioning_allowed"):
        failures.append("public/security-product positioning is allowed")
    operator_trial_observed = (
        observed_trial.get("valid") is True
        and observed_trial.get("status") == "observed"
        and observed_trial.get("result_present") is True
        and observed_trial.get("observed", {}).get("patch_apply_status") == "completed"
        and observed_trial.get("observed", {}).get("audit_verification_valid") == "true"
    )
    if not operator_trial_observed:
        failures.append("technical MVP state is not operator_trial_observed")
    post_disposition_mode = enterprise_send.get("preflight_mode") in {
        POST_DISPOSITION_MODE,
        PIS_002_ENTRY_DECISION_MODE,
        PIS_003_ENTRY_DECISION_MODE,
        PIS_003_EXTERNAL_INPUT_MODE,
    }
    if enterprise_send.get("valid") is not True:
        failures.append("enterprise send preflight is not valid")
    if operator_next.get("recommended_send_set") != []:
        failures.append("external-input wait must not expose an active send set")
    if (
        operator_next.get("recommended_next_enterprise_review")
        != "external_operator_input_required"
    ):
        failures.append("operator next action is not waiting for external operator input")
    if operator_next.get("next_action") != (
        enterprise_operator_next_action.PIS_003_EXTERNAL_INPUT_ACTION
    ):
        failures.append("operator next action is not the PIS-003 external-input wait")
    if (
        not post_disposition_mode
        and enterprise_send.get("artifact_commits_match_current") is not True
    ):
        failures.append("enterprise send artifacts do not match the current commit")
    if not post_disposition_mode and enterprise_send.get("artifact_hashes_match_files") is not True:
        failures.append("enterprise send artifact hashes do not match files")

    if not doc_path.exists():
        failures.append("v1.0 progress assessment doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 progress assessment is missing phrase: {phrase}")
        for phrase in BLOCKED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 progress assessment is missing blocked phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"v1.0 progress assessment contains forbidden phrase: {phrase}")

    if "v1-progress-assessment:" not in makefile:
        failures.append("Make target is missing: v1-progress-assessment")
    if "v1-progress-assessment" not in release_check_body:
        failures.append("v1-progress-assessment is missing from release-check")
    if "make v1-progress-assessment" not in readme:
        failures.append("README is missing v1-progress-assessment command")
    if doc_rel not in readme:
        failures.append("README is missing v1.0 progress assessment doc")
    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 progress assessment is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 progress assessment is missing from docs-site inputs")
    if "Ithildin v1.0 Progress Assessment" not in review_index:
        failures.append("review docs index is missing v1.0 progress assessment")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "assessment_doc": doc_rel,
        "tool_count": status.get("tool_count"),
        "latest_implemented_tool": status.get("latest_implemented_tool"),
        "selected_capability": capability.get("next_candidate"),
        "technical_mvp_state": (
            "operator_trial_observed" if operator_trial_observed else "ready_for_operator_trial"
        ),
        "operator_trial_observed": operator_trial_observed,
        "enterprise_send_ready": enterprise_send.get("valid"),
        "enterprise_send_preflight_mode": enterprise_send.get("preflight_mode"),
        "enterprise_send_artifact_commits_match_current": enterprise_send.get(
            "artifact_commits_match_current"
        ),
        "enterprise_send_artifact_payloads_clean": enterprise_send.get("artifact_payloads_clean"),
        "enterprise_send_artifact_hashes_match_files": enterprise_send.get(
            "artifact_hashes_match_files"
        ),
        "enterprise_gap_count": gap_matrix.get("gap_count"),
        "recommended_send_set": operator_next.get("recommended_send_set", []),
        "recommended_next_enterprise_review": operator_next.get(
            "recommended_next_enterprise_review"
        ),
        "enterprise_next_action": operator_next.get("next_action"),
        "historical_fallback_review_route": ["ERG-003", "ERG-002"],
        "capability_expansion_allowed": False,
        "runtime_changes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "progress_bands": {
            "core_local_gateway": "92-96%",
            "v1_local_preview_rc": "84-90%",
            "operator_workbench_demo": "78-86%",
            "mission_control_integration": "50-65%",
            "sandbox_vm_governed_workflow": "45-60%",
            "enterprise_security_product_readiness": "35-50%",
            "long_term_vision": "55-65%",
        },
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 progress assessment",
        f"valid: {str(report['valid']).lower()}",
        f"assessment_doc: {report['assessment_doc']}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        f"latest_implemented_tool: {report.get('latest_implemented_tool', 'unknown')}",
        f"selected_capability: {report.get('selected_capability', 'unknown')}",
        f"technical_mvp_state: {report.get('technical_mvp_state', 'unknown')}",
        f"operator_trial_observed: {str(report['operator_trial_observed']).lower()}",
        f"enterprise_send_ready: {str(report['enterprise_send_ready']).lower()}",
        "enterprise_send_preflight_mode: "
        f"{report.get('enterprise_send_preflight_mode', 'unknown')}",
        "enterprise_send_artifacts:",
        "- commits_match_current: "
        f"{str(report['enterprise_send_artifact_commits_match_current']).lower()}",
        f"- payloads_clean: {str(report['enterprise_send_artifact_payloads_clean']).lower()}",
        "- hashes_match_files: "
        f"{str(report['enterprise_send_artifact_hashes_match_files']).lower()}",
        f"enterprise_gap_count: {report.get('enterprise_gap_count', 'unknown')}",
        f"recommended_next_enterprise_review: {report['recommended_next_enterprise_review']}",
        "recommended_send_set: " + ", ".join(report["recommended_send_set"]),
        f"enterprise_next_action: {report['enterprise_next_action']}",
        "historical_fallback_review_route: "
        + ", ".join(report["historical_fallback_review_route"]),
        f"capability_expansion_allowed: {str(report['capability_expansion_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        "progress_bands:",
    ]
    lines.extend(f"- {name}: {band}" for name, band in report["progress_bands"].items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

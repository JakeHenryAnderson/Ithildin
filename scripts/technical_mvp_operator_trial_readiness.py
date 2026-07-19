"""Validate the technical MVP operator-trial readiness surface."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    demo_evidence_readiness,
    demo_flow_readiness,
    enterprise_operator_next_action,
    operator_sandbox_demo_readiness,
    review_docs,
    technical_mvp_ticket_map,
    v1_operator_trial_checklist_check,
    v1_operator_trial_observed,
    v1_operator_trial_record,
    v1_rc_readiness_check,
    workbench_readiness,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/technical-mvp-operator-trial-readiness.md"
DOC_TITLE = "Ithildin Technical MVP Operator Trial Readiness"

READY_STATES = {
    "technical_mvp_ticket_map",
    "v1_operator_trial_checklist",
    "v1_operator_trial_record",
    "v1_rc_readiness",
    "workbench_readiness",
    "demo_flow_readiness",
    "demo_evidence_readiness",
    "operator_sandbox_demo_readiness",
}

REQUIRED_DOC_PHRASES = [
    "Status: checked operator-trial readiness view for the technical MVP.",
    "make technical-mvp-operator-trial-readiness",
    "What Is Ready",
    "What Remains Before A Hands-On Technical MVP Trial",
    "Observed Trial State",
    "What Remains Beyond Technical MVP",
    "make release-check",
    "make review-candidate",
    "make v1-operator-trial-record",
    "make v1-operator-trial-observed-check",
    "make demo-seed",
    "make compose-up",
    "make compose-smoke",
    "make compose-down",
    "make enterprise-review-send-refresh",
    "`ERG-003`",
    "`ERG-002`",
    "local-preview operator trial",
    "does not start services",
    "does not call governed tools",
    "does not approve sandbox/VM lifecycle control",
]

BLOCKED_PHRASES = [
    "production deployment readiness",
    "production identity or enterprise RBAC",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP hosting",
    "Mission Control execution authority",
    "Ithildin-managed VM/container lifecycle",
    "trusted-host promotion",
    "SIEM custody",
    "compliance automation",
    "public/security-product positioning",
    "new governed tool powers",
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

RECOMMENDED_TRIAL_COMMANDS = [
    "make release-check",
    "make review-candidate",
    "make v1-operator-trial-record",
    "make demo-seed",
    "make compose-up",
    "make compose-smoke",
    "make compose-down",
]

RECOMMENDED_REVIEW_COMMANDS = [
    "make enterprise-review-send-refresh",
    "make enterprise-response-waiting-room",
]
ALLOWED_ENTERPRISE_NEXT_ACTIONS = {
    "send_erg_003_and_erg_002",
    "prepare_erg004_runtime_implementation_gate",
    "prepare_erg004_descriptor_only_runtime_planning",
    "prepare_erg005_trusted_host_promotion_review",
    "execute_pis_001_threat_model_dependency_decision",
}


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
    reports = {
        "technical_mvp_ticket_map": technical_mvp_ticket_map.build_report(repo_root),
        "v1_operator_trial_checklist": v1_operator_trial_checklist_check.build_report(repo_root),
        "v1_operator_trial_record": v1_operator_trial_record.build_record(
            repo_root,
            repo_root / "var/review-packets/v1.0/operator-trial",
        ),
        "v1_operator_trial_observed": v1_operator_trial_observed.build_observed_record(
            repo_root,
            repo_root / "var/review-packets/v1.0/operator-trial-observed",
            write_artifacts=False,
        ),
        "v1_rc_readiness": v1_rc_readiness_check.build_report(repo_root),
        "workbench_readiness": workbench_readiness.build_report(repo_root),
        "demo_flow_readiness": demo_flow_readiness.build_report(repo_root),
        "demo_evidence_readiness": demo_evidence_readiness.build_report(repo_root),
        "operator_sandbox_demo_readiness": operator_sandbox_demo_readiness.build_report(repo_root),
        "enterprise_operator_next_action": enterprise_operator_next_action.build_report(repo_root),
    }
    failures = _report_failures(reports)
    failures.extend(_wiring_failures(repo_root))

    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    ticket_map = reports["technical_mvp_ticket_map"]
    observed = reports["v1_operator_trial_observed"]
    next_action = reports["enterprise_operator_next_action"]

    if ticket_map.get("tool_count") != 24:
        failures.append("tool count is not 24")
    if ticket_map.get("selected_capability") != "not selected":
        failures.append("selected capability is not not selected")
    if ticket_map.get("next_action") not in ALLOWED_ENTERPRISE_NEXT_ACTIONS:
        failures.append("technical MVP next action is not an allowed enterprise flow")
    if next_action.get("response_present_count") != 0:
        failures.append("enterprise responses are present; use response intake flow")

    observed_trial_passed = (
        observed.get("valid") is True
        and observed.get("status") == "observed"
        and observed.get("result_present") is True
        and observed.get("observed", {}).get("patch_apply_status") == "completed"
        and observed.get("observed", {}).get("audit_verification_valid") == "true"
    )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "readiness_doc": DOC_REL,
        "commit": commit,
        "dirty": dirty,
        "tool_count": ticket_map.get("tool_count"),
        "latest_implemented_tool": ticket_map.get("latest_implemented_tool"),
        "selected_capability": ticket_map.get("selected_capability"),
        "technical_mvp_state": (
            "operator_trial_observed" if observed_trial_passed else "ready_for_operator_trial"
        ),
        "operator_trial_ready": all(reports[name].get("valid") is True for name in READY_STATES),
        "operator_trial_observed": observed_trial_passed,
        "hands_on_trial_required": not observed_trial_passed,
        "observed_trial": {
            "status": observed.get("status"),
            "result_present": observed.get("result_present"),
            "patch_apply_status": observed.get("observed", {}).get("patch_apply_status"),
            "audit_verification_valid": observed.get("observed", {}).get(
                "audit_verification_valid"
            ),
            "demo_result_path": observed.get("demo_result_path"),
        },
        "recommended_next_enterprise_review": next_action.get("recommended_next_enterprise_review"),
        "recommended_send_set": next_action.get("recommended_send_set"),
        "enterprise_next_action": next_action.get("next_action"),
        "response_present_count": next_action.get("response_present_count"),
        "recommended_trial_commands": RECOMMENDED_TRIAL_COMMANDS,
        "recommended_review_commands": RECOMMENDED_REVIEW_COMMANDS,
        "ready_checks": {name: _summary(report) for name, report in reports.items()},
        "runtime_changes_allowed": False,
        "capability_expansion_allowed": False,
        "new_power_classes_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_behavior_allowed": False,
        "mission_control_execution_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin technical MVP operator-trial readiness",
        f"valid: {str(report['valid']).lower()}",
        f"readiness_doc: {report['readiness_doc']}",
        f"commit: {report['commit']}",
        f"dirty: {str(report['dirty']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"latest_implemented_tool: {report['latest_implemented_tool']}",
        f"selected_capability: {report['selected_capability']}",
        f"technical_mvp_state: {report['technical_mvp_state']}",
        f"operator_trial_ready: {str(report['operator_trial_ready']).lower()}",
        f"operator_trial_observed: {str(report['operator_trial_observed']).lower()}",
        f"hands_on_trial_required: {str(report['hands_on_trial_required']).lower()}",
        f"enterprise_next_action: {report['enterprise_next_action']}",
        "runtime_changes_allowed: false",
        "capability_expansion_allowed: false",
        "sandbox_orchestration_allowed: false",
        "mission_control_execution_allowed: false",
        "public_security_product_positioning_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _report_failures(reports: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for name, report in reports.items():
        if report.get("valid") is not True:
            failures.append(f"{name} is not valid")
            failures.extend(f"{name}: {failure}" for failure in report.get("failures", []))
    return failures


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "valid": report.get("valid") is True,
        "failure_count": len(report.get("failures", [])),
    }
    for key in [
        "tool_count",
        "latest_implemented_tool",
        "selected_capability",
        "next_action",
        "recommended_next_enterprise_review",
        "response_present_count",
    ]:
        if key in report:
            summary[key] = report[key]
    return summary


def _wiring_failures(repo_root: Path) -> list[str]:
    failures: list[str] = []
    doc = repo_root / DOC_REL
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc.exists():
        failures.append("technical MVP operator-trial readiness doc is missing")
        text = ""
    else:
        text = doc.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in text:
                failures.append(
                    f"technical MVP operator-trial readiness doc is missing phrase: {phrase}"
                )
        for phrase in BLOCKED_PHRASES:
            if phrase not in text:
                failures.append(
                    "technical MVP operator-trial readiness doc is missing blocked "
                    f"phrase: {phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    "technical MVP operator-trial readiness doc contains forbidden "
                    f"phrase: {phrase}"
                )

    if "technical-mvp-operator-trial-readiness:" not in makefile:
        failures.append("Make target is missing: technical-mvp-operator-trial-readiness")
    if (
        "technical-mvp-operator-trial-readiness" not in release_check_body
        and "release-check: technical-mvp-operator-trial-readiness" not in makefile
    ):
        failures.append("technical-mvp-operator-trial-readiness is missing from release-check")
    if "make technical-mvp-operator-trial-readiness" not in readme:
        failures.append("README is missing technical MVP operator-trial readiness command")
    if DOC_REL not in readme:
        failures.append("README is missing technical MVP operator-trial readiness doc")
    if DOC_REL not in docs_site:
        failures.append(
            "technical MVP operator-trial readiness doc is missing from docs-site inputs"
        )
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("technical MVP operator-trial readiness doc is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review docs index is missing technical MVP operator-trial readiness")
    if "technical-mvp-operator-trial-readiness" not in release_guardrails:
        failures.append("release guardrails do not require technical MVP operator-trial readiness")
    return failures


def _git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

"""Check that the ERG-002 Mission Control display/import review handoff is ready."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    mission_control_display_disposition_closure_check,
    mission_control_display_external_review_bundle,
    mission_control_display_response_dry_run,
    mission_control_display_response_kit,
    mission_control_integration_readiness_packet,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/mission-control-display-next-review-ready-check.md"


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
    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    external_bundle = mission_control_display_external_review_bundle.build_check_report(
        repo_root
    )
    readiness_packet = mission_control_integration_readiness_packet.build_check_report(
        repo_root
    )
    response_kit = mission_control_display_response_kit.build_check_report(repo_root)
    response_dry_run = mission_control_display_response_dry_run.run_dry_run(repo_root)
    closure_gate = mission_control_display_disposition_closure_check.build_report(repo_root)

    for label, report in [
        ("external-review bundle", external_bundle),
        ("integration readiness packet", readiness_packet),
        ("response kit", response_kit),
        ("response dry run", response_dry_run),
        ("disposition closure gate", closure_gate),
    ]:
        if not report.get("valid"):
            failures.append(f"{label} is not valid")
            failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    if closure_gate.get("closure_ready") is True:
        failures.append("ERG-002 closure is already ready; use the triage-update path instead")
    if closure_gate.get("normalized_response_present") is True:
        failures.append("normalized ERG-002 response already exists; review intake before sending")
    if response_dry_run.get("committed_findings_mutated") is not False:
        failures.append("Mission Control response dry run mutated committed findings")
    if response_dry_run.get("external_review_recorded") is not False:
        failures.append("Mission Control response dry run recorded external review")
    if external_bundle.get("recommended_next_review") != "ERG-002":
        failures.append("external-review bundle does not recommend ERG-002")

    for phrase in [
        "Recommended packet: `var/review-packets/v3/mission-control-display-external-review/`",
        "make mission-control-display-next-review-ready-check",
        "make mission-control-display-external-review-bundle",
        "make mission-control-integration-readiness-packet",
        "make mission-control-display-response-kit",
        "does not close `ERG-002`",
        "does not approve Mission Control runtime importer behavior",
        "does not approve Mission Control execution authority",
        "does not approve local model invocation",
        "does not approve sandbox orchestration",
    ]:
        if phrase not in doc:
            failures.append(f"ready-check doc is missing phrase: {phrase}")

    if "mission-control-display-next-review-ready-check:" not in makefile:
        failures.append(
            "Make target is missing: mission-control-display-next-review-ready-check"
        )
    if "mission-control-display-next-review-ready-check" not in release_check_body:
        failures.append(
            "mission-control-display-next-review-ready-check missing from release-check"
        )
    if "make mission-control-display-next-review-ready-check" not in readme:
        failures.append("README is missing Mission Control next-review ready-check command")
    if DOC_REL not in docs_site:
        failures.append("Mission Control next-review ready-check missing from docs-site inputs")
    if DOC_REL not in review_docs:
        failures.append("Mission Control next-review ready-check missing from review docs")
    if "Mission Control Display Next Review Ready Check" not in review_index:
        failures.append("review-docs index is missing Mission Control next-review ready check")
    if "mission-control-display-next-review-ready-check" not in release_guardrails:
        failures.append("release guardrails do not require Mission Control next-review ready check")

    ready_to_send = (
        not failures
        and external_bundle.get("valid") is True
        and readiness_packet.get("valid") is True
        and response_kit.get("valid") is True
        and response_dry_run.get("valid") is True
        and closure_gate.get("valid") is True
        and closure_gate.get("closure_ready") is False
        and closure_gate.get("normalized_response_present") is False
    )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "ready_to_send": ready_to_send,
        "recommended_gap": "ERG-002",
        "recommended_packet": (
            "var/review-packets/v3/mission-control-display-external-review/"
        ),
        "normalized_response_present": closure_gate.get("normalized_response_present"),
        "closure_ready": closure_gate.get("closure_ready"),
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "mission_control_planning_allowed": True,
        "mission_control_runtime_allowed": False,
        "mission_control_execution_authority_allowed": False,
        "mission_control_policy_authority_allowed": False,
        "mission_control_approval_authority_allowed": False,
        "mission_control_audit_authority_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_002": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control display next-review ready check",
        f"valid: {str(report['valid']).lower()}",
        f"ready_to_send: {str(report['ready_to_send']).lower()}",
        f"recommended_gap: {report['recommended_gap']}",
        f"recommended_packet: {report['recommended_packet']}",
        f"normalized_response_present: {str(report['normalized_response_present']).lower()}",
        f"closure_ready: {str(report['closure_ready']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_planning_allowed: "
        f"{str(report['mission_control_planning_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        "mission_control_execution_authority_allowed: "
        f"{str(report['mission_control_execution_authority_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_002: {str(report['closes_erg_002']).lower()}",
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


if __name__ == "__main__":
    raise SystemExit(main())

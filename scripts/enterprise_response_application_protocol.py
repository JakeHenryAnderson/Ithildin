"""Validate the enterprise response application protocol."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_response_normalization_coverage,
    enterprise_response_status_board,
    next_capability_readiness,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-response-application-protocol.md"
DOC_TITLE = "Enterprise Response Application Protocol"

REQUIRED_PHRASES = [
    "Status: checked operator protocol for applying enterprise external-review responses.",
    "make enterprise-response-application-protocol",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "Current recommended send set: `ERG-003` then `ERG-002`",
    "Enterprise response evidence is not present yet.",
    "Enterprise closure-ready count is `0`.",
    "Do not edit status docs directly.",
    "`ERG-003` may move only to `closed_local_preview_static_preflight`.",
    "`ERG-002` may move only to `ready_for_design_only_decision_record`.",
    "make enterprise-response-inbox",
    "make enterprise-dual-response-inbox",
    "var/review-runs/enterprise-dual-response-inbox/ENTERPRISE_DUAL_RESPONSE_CHEATSHEET.md",
    "make enterprise-response-status-board",
    "make enterprise-response-intake-drill",
    "make enterprise-current-checkpoint",
]

REQUIRED_BOUNDARY_PHRASES = [
    "live VM/container inspection",
    "VM/container lifecycle management",
    "local model invocation",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "Mission Control execution authority",
    "Mission Control policy authority",
    "Mission Control approval authority",
    "Mission Control audit authority",
    "API callbacks",
    "polling or mutating Ithildin APIs",
    "trusted-host promotion",
    "SIEM adapters",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "compliance automation",
    "public/security-product positioning",
    "new governed tool powers",
]

REQUIRED_LANE_ARTIFACTS = [
    "docs/codex/sandbox-vm-static-preflight-response-kit.md",
    "docs/codex/sandbox-vm-static-preflight-response-dry-run.md",
    "docs/codex/sandbox-vm-static-preflight-disposition-closure-gate.md",
    "docs/codex/sandbox-vm-static-preflight-response-application-record.md",
    "docs/codex/sandbox-vm-static-preflight-response-application-playbook.md",
    "docs/codex/mission-control-display-response-kit.md",
    "docs/codex/mission-control-display-response-dry-run.md",
    "docs/codex/mission-control-display-disposition-closure-gate.md",
    "docs/codex/mission-control-display-decision-record-skeleton.md",
    "docs/codex/mission-control-importer-acceptance-matrix.md",
    "docs/codex/mission-control-handoff-reference-validator.md",
]

FORBIDDEN_PHRASES = [
    "runtime expansion is approved",
    "Mission Control runtime is approved",
    "live VM inspection is approved",
    "sandbox orchestration is approved",
    "public security product is approved",
    "enterprise ready",
    "production ready",
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

    capability = next_capability_readiness.build_report(repo_root)
    status_board = enterprise_response_status_board.build_report(repo_root)
    coverage = enterprise_response_normalization_coverage.build_report(repo_root)

    failures.extend(
        f"next-capability-readiness: {failure}" for failure in capability["failures"]
    )
    failures.extend(
        f"enterprise-response-status-board: {failure}"
        for failure in status_board["failures"]
    )
    failures.extend(
        f"enterprise-response-normalization-coverage: {failure}"
        for failure in coverage["failures"]
    )

    doc_path = repo_root / DOC_REL
    doc = _read(doc_path)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    current_checkpoint_doc = _read(repo_root / "docs/codex/enterprise-current-checkpoint.md")
    response_inbox_doc = _read(repo_root / "docs/codex/enterprise-response-inbox.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if capability.get("tool_count") != 24:
        failures.append("next-capability readiness tool count is not 24")
    if capability.get("next_candidate") != "not selected":
        failures.append("selected capability is not blocked/not selected")
    if status_board.get("response_present_count") != 0:
        failures.append("enterprise responses are present; apply the real response workflow")
    if status_board.get("closure_ready_count") != 0:
        failures.append("enterprise closure is ready; apply the lane-specific closure workflow")
    if coverage.get("missing_areas"):
        failures.append("enterprise response normalization coverage has missing areas")

    boundary_flags = {
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
    for key, expected in boundary_flags.items():
        if key in status_board and status_board[key] is not expected:
            failures.append(f"response-status boundary flag drifted: {key}")
        if key in coverage and coverage[key] is not expected:
            failures.append(f"normalization-coverage boundary flag drifted: {key}")

    for phrase in REQUIRED_PHRASES:
        if phrase not in doc:
            failures.append(f"application protocol doc is missing phrase: {phrase}")
    for phrase in REQUIRED_BOUNDARY_PHRASES:
        if phrase not in doc:
            failures.append(f"application protocol doc is missing boundary phrase: {phrase}")
    for rel_path in REQUIRED_LANE_ARTIFACTS:
        if rel_path not in doc:
            failures.append(f"application protocol doc is missing lane artifact: {rel_path}")
        if not (repo_root / rel_path).exists():
            failures.append(f"referenced lane artifact is missing: {rel_path}")
    lowered = doc.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            failures.append(f"application protocol doc contains forbidden phrase: {phrase}")

    if "enterprise-response-application-protocol:" not in makefile:
        failures.append("Make target is missing: enterprise-response-application-protocol")
    if (
        "enterprise-response-application-protocol" not in release_check_body
        and "release-check: enterprise-response-application-protocol" not in makefile
    ):
        failures.append("enterprise-response-application-protocol is missing from release-check")
    if "make enterprise-response-application-protocol" not in readme:
        failures.append("README is missing enterprise-response-application-protocol command")
    if DOC_REL not in readme:
        failures.append("README is missing enterprise response application protocol doc")
    if DOC_REL not in docs_site:
        failures.append("enterprise response application protocol is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise response application protocol is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise response application protocol")
    if "enterprise-response-application-protocol" not in release_guardrails:
        failures.append(
            "release guardrails do not require enterprise response application protocol"
        )
    if "enterprise-response-application-protocol" not in current_checkpoint_doc:
        failures.append("enterprise current checkpoint does not mention the application protocol")
    if "enterprise-response-application-protocol" not in response_inbox_doc:
        failures.append("enterprise response inbox does not mention the application protocol")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "protocol_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": status_board.get("selected_capability", "not selected"),
        "recommended_send_set": ["ERG-003", "ERG-002"],
        "response_present_count": status_board.get("response_present_count"),
        "closure_ready_count": status_board.get("closure_ready_count"),
        "covered_response_area_count": coverage.get("covered_area_count"),
        **boundary_flags,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise response application protocol",
        f"valid: {str(report['valid']).lower()}",
        f"protocol_doc: {report['protocol_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report.get('selected_capability', 'unknown')}",
        "recommended_send_set: " + ", ".join(report.get("recommended_send_set") or []),
        f"response_present_count: {report.get('response_present_count', 'unknown')}",
        f"closure_ready_count: {report.get('closure_ready_count', 'unknown')}",
        f"covered_response_area_count: {report.get('covered_response_area_count', 'unknown')}",
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

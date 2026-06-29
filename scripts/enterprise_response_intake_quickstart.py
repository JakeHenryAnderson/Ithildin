"""Validate the operator quickstart for ERG-003/ERG-002 response intake."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_dual_response_readiness,
    enterprise_response_application_protocol,
    enterprise_response_command_matrix,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-response-intake-quickstart.md"
DOC_TITLE = "Enterprise Response Intake Quickstart"

BOUNDARY_FLAGS = {
    "records_external_review": False,
    "normalizes_real_responses": False,
    "writes_response_files": False,
    "mutates_findings": False,
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
    readiness = enterprise_dual_response_readiness.build_report(repo_root)
    command_matrix = enterprise_response_command_matrix.build_report(repo_root)
    application_protocol = enterprise_response_application_protocol.build_report(repo_root)

    if readiness.get("valid") is not True:
        failures.append("enterprise dual-response readiness is not valid")
    if command_matrix.get("valid") is not True:
        failures.append("enterprise response command matrix is not valid")
    if application_protocol.get("valid") is not True:
        failures.append("enterprise response application protocol is not valid")

    if readiness.get("recommended_gaps") != ["ERG-003", "ERG-002"]:
        failures.append("quickstart expected ERG-003/ERG-002 as the active dual response lanes")
    if readiness.get("response_present_count") != 0:
        failures.append("real response evidence is already present; use lane-specific closure flow")
    if readiness.get("closure_ready_count") != 0:
        failures.append("a response lane is closure-ready; do not treat quickstart as pending")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    dual_handoff = _read(repo_root / "docs/codex/enterprise-dual-review-handoff.md")
    dual_inbox = _read(repo_root / "docs/codex/enterprise-dual-response-inbox.md")
    dual_readiness = _read(repo_root / "docs/codex/enterprise-dual-response-readiness.md")
    status_board = _read(repo_root / "docs/codex/enterprise-response-status-board.md")
    command_matrix_doc = _read(repo_root / "docs/codex/enterprise-response-command-matrix.md")
    application_protocol_doc = _read(
        repo_root / "docs/codex/enterprise-response-application-protocol.md"
    )
    current_checkpoint = _read(repo_root / "docs/codex/enterprise-current-checkpoint.md")
    send_checklist_doc = _read(repo_root / "docs/codex/enterprise-review-send-checklist.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    required_doc_phrases = [
        "Status: operator quickstart for applying `ERG-003` and `ERG-002` reviewer responses.",
        "Current governed tool count: `24`.",
        "make enterprise-response-intake-quickstart",
        "make enterprise-dual-response-inbox",
        "make enterprise-dual-response-readiness",
        "make enterprise-response-status-board",
        "make enterprise-response-command-matrix",
        "make enterprise-response-application-protocol",
        "var/review-packets/v3/enterprise-dual-review-outbox/ERG-003/",
        "var/review-packets/v3/enterprise-dual-review-outbox/ERG-002/",
        "var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md",
        "var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md",
        "var/review-runs/enterprise-dual-response-inbox/ENTERPRISE_DUAL_RESPONSE_CHEATSHEET.md",
        "EXT-SVP-###",
        "EXT-MC-DISPLAY-###",
        "Use the generated cheat sheet for the exact normalization command",
        "--area sandbox-vm-static-preflight",
        "--area mission-control-display",
        "make sandbox-vm-static-preflight-response-dry-run",
        "make sandbox-vm-static-preflight-disposition-closure-check",
        "make mission-control-display-response-dry-run",
        "make mission-control-display-disposition-closure-check",
        "does not send packets",
        "does not record external review",
        "does not normalize real responses",
        "does not approve runtime behavior",
        "does not approve Mission Control runtime importer behavior",
        "does not approve live VM/container inspection",
        "make release-check",
        "make review-candidate",
    ]
    for phrase in required_doc_phrases:
        if phrase not in doc:
            failures.append(f"quickstart doc is missing phrase: {phrase}")
    for phrase in [
        "Status: operator checklist for sending the current enterprise review packets.",
        "make enterprise-review-send-checklist",
        "`ERG-003`",
        "`ERG-002`",
    ]:
        if phrase not in send_checklist_doc:
            failures.append(f"send checklist doc is missing phrase: {phrase}")

    forbidden_doc_phrases = [
        "approve Mission Control runtime importer behavior",
        "approve live VM/container inspection",
        "approve sandbox orchestration",
        "approve public/security-product positioning",
        "approve new governed tool powers",
    ]
    for phrase in forbidden_doc_phrases:
        if phrase in doc and f"does not {phrase}" not in doc:
            failures.append(f"quickstart doc contains unqualified approval phrase: {phrase}")

    wiring_checks = {
        "Make target": "enterprise-response-intake-quickstart:" in makefile,
        "release-check": "enterprise-response-intake-quickstart" in release_check_body
        or "release-check: enterprise-response-intake-quickstart" in makefile,
        "review-candidate": "$(MAKE) enterprise-response-intake-quickstart"
        in review_candidate_body,
        "README command": "make enterprise-response-intake-quickstart" in readme,
        "README doc link": DOC_REL in readme,
        "docs site": DOC_REL in docs_site,
        "review docs": DOC_REL in review_docs.REVIEW_DOCS,
        "review index": DOC_TITLE in review_index,
        "release guardrails fragment": "enterprise-response-intake-quickstart"
        in release_guardrails,
        "dual handoff": "enterprise-response-intake-quickstart" in dual_handoff,
        "dual inbox": "enterprise-response-intake-quickstart" in dual_inbox,
        "dual readiness": "enterprise-response-intake-quickstart" in dual_readiness,
        "status board": "enterprise-response-intake-quickstart" in status_board,
        "command matrix": "enterprise-response-intake-quickstart" in command_matrix_doc,
        "application protocol": "enterprise-response-intake-quickstart"
        in application_protocol_doc,
        "current checkpoint": "enterprise-response-intake-quickstart" in current_checkpoint,
        "send checklist": "enterprise-response-intake-quickstart" in send_checklist_doc,
    }
    for label, ok in wiring_checks.items():
        if not ok:
            failures.append(f"quickstart wiring missing: {label}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "quickstart_doc": DOC_REL,
        "tool_count": 24,
        "recommended_gaps": ["ERG-003", "ERG-002"],
        "response_present_count": readiness.get("response_present_count"),
        "closure_ready_count": readiness.get("closure_ready_count"),
        "send_checklist_valid": bool(send_checklist_doc),
        "dual_response_readiness_valid": readiness.get("valid") is True,
        "command_matrix_valid": command_matrix.get("valid") is True,
        "application_protocol_valid": application_protocol.get("valid") is True,
        **BOUNDARY_FLAGS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise response intake quickstart",
        f"valid: {str(report['valid']).lower()}",
        f"quickstart_doc: {report['quickstart_doc']}",
        f"tool_count: {report['tool_count']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        f"send_checklist_valid: {str(report['send_checklist_valid']).lower()}",
        "dual_response_readiness_valid: "
        f"{str(report['dual_response_readiness_valid']).lower()}",
        f"command_matrix_valid: {str(report['command_matrix_valid']).lower()}",
        f"application_protocol_valid: {str(report['application_protocol_valid']).lower()}",
    ]
    for key in BOUNDARY_FLAGS:
        lines.append(f"{key}: {str(report[key]).lower()}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

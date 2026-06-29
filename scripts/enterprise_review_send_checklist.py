"""Validate the operator checklist for sending enterprise review packets."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_dual_review_outbox,
    enterprise_response_status_board,
    enterprise_review_send_manifest,
    enterprise_review_send_readiness,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-review-send-checklist.md"
DOC_NAME = "enterprise-review-send-checklist.md"
RECOMMENDED_GAPS = ["ERG-003", "ERG-002"]
BOUNDARY_FLAGS = {
    "records_external_review": False,
    "normalizes_responses": False,
    "writes_response_files": False,
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
    report = build_report(ROOT)
    print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    doc = _read(doc_path)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    send_readiness_doc = _read(repo_root / "docs/codex/enterprise-review-send-readiness.md")
    manifest_doc = _read(repo_root / "docs/codex/enterprise-review-send-manifest.md")
    outbox_doc = _read(repo_root / "docs/codex/enterprise-dual-review-outbox.md")
    submission_doc = _read(repo_root / "docs/codex/enterprise-review-submission-prompt.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    readiness = enterprise_review_send_readiness.build_report(repo_root)
    status = enterprise_response_status_board.build_report(repo_root)
    if readiness.get("valid") is not True:
        failures.append("enterprise review send-readiness is not valid")
    if status.get("valid") is not True:
        failures.append("enterprise response status board is not valid")
    if readiness.get("recommended_now") != RECOMMENDED_GAPS:
        failures.append("enterprise review send-readiness recommended set changed")
    if readiness.get("tool_count") != 24:
        failures.append("enterprise review send-readiness tool count is not 24")
    for key, expected in {
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }.items():
        if readiness.get(key) is not expected:
            failures.append(f"enterprise review send-readiness changed {key}")

    outbox_report = enterprise_dual_review_outbox.build_check_report(repo_root)
    manifest_report = enterprise_review_send_manifest.build_check_report(repo_root)
    if outbox_report.get("valid") is not True:
        failures.append("enterprise dual-review outbox check is not valid")
    if manifest_report.get("valid") is not True:
        failures.append("enterprise review send manifest check is not valid")

    outbox_dir = repo_root / enterprise_dual_review_outbox.DEFAULT_OUTPUT_DIR
    manifest_dir = repo_root / enterprise_review_send_manifest.DEFAULT_OUTPUT_DIR
    required_existing_paths = [
        outbox_dir / "ERG-003/01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md",
        outbox_dir / "ERG-002/01_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_PROMPT.md",
        outbox_dir / "ERG-003/sandbox-vm-static-preflight-external-review-artifact-hashes.json",
        outbox_dir / "ERG-002/mission-control-display-external-review-artifact-hashes.json",
        manifest_dir / enterprise_review_send_manifest.MARKDOWN_NAME,
        manifest_dir / enterprise_review_send_manifest.JSON_NAME,
        manifest_dir / enterprise_review_send_manifest.HASH_NAME,
    ]
    for path in required_existing_paths:
        if not path.exists():
            failures.append(f"required send artifact is missing: {path.relative_to(repo_root)}")

    manifest_json = _read(manifest_dir / enterprise_review_send_manifest.JSON_NAME)
    try:
        manifest_payload = json.loads(manifest_json) if manifest_json else {}
    except json.JSONDecodeError:
        manifest_payload = {}
        failures.append("enterprise review send manifest JSON is invalid")
    if manifest_payload.get("recommended_gaps") != RECOMMENDED_GAPS:
        failures.append("send manifest recommended gaps do not match checklist")
    for key, expected in BOUNDARY_FLAGS.items():
        if manifest_payload.get("blocked_boundaries", {}).get(key, expected) is not expected:
            failures.append(f"send manifest blocked boundary changed: {key}")

    _require_phrases(
        failures,
        "send checklist doc",
        doc,
        [
            "Status: operator checklist for sending the current enterprise review packets.",
            "make enterprise-review-send-checklist",
            "`ERG-003`",
            "`ERG-002`",
            "var/review-packets/v3/enterprise-dual-review-outbox/ERG-003/",
            "var/review-packets/v3/enterprise-dual-review-outbox/ERG-002/",
            "01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md",
            "01_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_PROMPT.md",
            "var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md",
            "var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md",
            "make enterprise-review-send-receipt-template",
            "make enterprise-dual-response-inbox",
            "make enterprise-response-paste-preflight",
            "make enterprise-dual-response-readiness",
            "make enterprise-response-intake-drill",
            "make sandbox-vm-static-preflight-disposition-closure-check",
            "make mission-control-display-disposition-closure-check",
            "make packet-redaction-scan",
            "does not record external review",
            "does not normalize responses",
            "does not close `ERG-003` or `ERG-002`",
            "approve Mission Control runtime importer behavior",
            "approve live VM/container inspection",
            "approve new governed tool powers",
        ],
    )
    _require_absent(
        failures,
        "send checklist doc",
        doc,
        [
            "records external review",
            "normalizes reviewer responses",
            "closes ERG-003",
            "closes ERG-002",
            "approves runtime behavior",
        ],
    )

    wiring_checks = {
        "Make target": ("enterprise-review-send-checklist:", makefile),
        "Release check": ("enterprise-review-send-checklist", release_check_body),
        "Review candidate": ("$(MAKE) enterprise-review-send-checklist", review_candidate_body),
        "README command": ("make enterprise-review-send-checklist", readme),
        "Docs site": (DOC_REL, docs_site),
        "Review docs": (DOC_REL, "\n".join(review_docs.REVIEW_DOCS)),
        "Review index": (DOC_NAME, review_index),
        "Release guardrails": ("enterprise-review-send-checklist", release_guardrails),
        "Send readiness pointer": ("enterprise-review-send-checklist", send_readiness_doc),
        "Manifest pointer": ("enterprise-review-send-checklist", manifest_doc),
        "Outbox pointer": ("enterprise-review-send-checklist", outbox_doc),
        "Submission pointer": ("enterprise-review-send-checklist", submission_doc),
    }
    for label, (needle, haystack) in wiring_checks.items():
        if needle not in haystack:
            failures.append(f"{label} is missing {needle}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "checklist_doc": DOC_REL,
        "recommended_gaps": RECOMMENDED_GAPS,
        "tool_count": 24,
        "response_present_count": status.get("response_present_count"),
        "closure_ready_count": status.get("closure_ready_count"),
        "outbox_valid": outbox_report.get("valid") is True,
        "send_manifest_valid": manifest_report.get("valid") is True,
        **BOUNDARY_FLAGS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review send checklist",
        f"valid: {str(report['valid']).lower()}",
        f"checklist_doc: {report['checklist_doc']}",
        f"tool_count: {report['tool_count']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        f"outbox_valid: {str(report['outbox_valid']).lower()}",
        f"send_manifest_valid: {str(report['send_manifest_valid']).lower()}",
    ]
    for key in BOUNDARY_FLAGS:
        lines.append(f"{key}: {str(report[key]).lower()}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _require_phrases(
    failures: list[str], label: str, text: str, phrases: list[str]
) -> None:
    for phrase in phrases:
        if phrase not in text:
            failures.append(f"{label} is missing phrase: {phrase}")


def _require_absent(
    failures: list[str], label: str, text: str, phrases: list[str]
) -> None:
    for phrase in phrases:
        if phrase in text:
            failures.append(f"{label} contains forbidden unqualified phrase: {phrase}")


if __name__ == "__main__":
    raise SystemExit(main())

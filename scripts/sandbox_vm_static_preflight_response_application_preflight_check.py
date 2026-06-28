"""Validate ERG-003 response application preflight wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_response_command_matrix,
    review_docs,
    sandbox_vm_static_preflight_disposition_closure_check,
    sandbox_vm_static_preflight_response_application_playbook_check,
    sandbox_vm_static_preflight_response_application_record_check,
    sandbox_vm_static_preflight_response_dry_run,
    sandbox_vm_static_preflight_triage_update_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-static-preflight-response-application-preflight.md"
DOC_NAME = "sandbox-vm-static-preflight-response-application-preflight.md"
RAW_RESPONSE_PATH = "var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-003.md"
NORMALIZED_RESPONSE_PATH = (
    sandbox_vm_static_preflight_disposition_closure_check.NORMALIZED_RESPONSE_REL
)

REQUIRED_PHRASES = [
    "Status: checked preflight for applying a real `ERG-003` external response.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "Current `ERG-003` status before real reviewer disposition: `external_review_required`.",
    "make sandbox-vm-static-preflight-response-application-preflight-check",
    "make enterprise-response-command-matrix",
    RAW_RESPONSE_PATH,
    NORMALIZED_RESPONSE_PATH,
    "sandbox-vm-static-preflight",
    "EXT-SVP-###",
    "make sandbox-vm-static-preflight-disposition-closure-check",
    "make sandbox-vm-static-preflight-response-dry-run",
    "make sandbox-vm-static-preflight-triage-update-check",
    "make sandbox-vm-static-preflight-response-application-record-check",
    "make sandbox-vm-static-preflight-response-application-playbook-check",
    "closed_local_preview_static_preflight",
    "does not normalize responses",
    "does not write normalized response files",
    "does not close `ERG-003`",
    "ERG-004 remains blocked",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "runtime implementation",
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "network expansion",
    "API/MCP profile loading",
    "new governed tool powers",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "SIEM adapter behavior",
    "compliance automation",
    "public/security-product positioning",
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

    closure = sandbox_vm_static_preflight_disposition_closure_check.build_report(repo_root)
    dry_run = sandbox_vm_static_preflight_response_dry_run.run_dry_run(repo_root)
    triage = sandbox_vm_static_preflight_triage_update_check.build_report(repo_root)
    record = sandbox_vm_static_preflight_response_application_record_check.build_report(repo_root)
    playbook = sandbox_vm_static_preflight_response_application_playbook_check.build_report(
        repo_root
    )
    matrix = enterprise_response_command_matrix.build_report(repo_root)

    for label, report in [
        ("closure gate", closure),
        ("response dry run", dry_run),
        ("triage update", triage),
        ("response application record", record),
        ("response application playbook", playbook),
        ("enterprise response command matrix", matrix),
    ]:
        if report.get("valid") is not True:
            failures.append(f"{label} is not valid")
            failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    erg003_row = next(
        (row for row in matrix.get("command_rows", []) if row.get("gap") == "ERG-003"),
        None,
    )
    if not erg003_row:
        failures.append("enterprise response command matrix is missing ERG-003")
    else:
        expected_values = {
            "raw_response_path": RAW_RESPONSE_PATH,
            "normalized_response_path": NORMALIZED_RESPONSE_PATH,
            "normalization_area": "sandbox-vm-static-preflight",
            "dry_run_command": "make sandbox-vm-static-preflight-response-dry-run",
            "closure_gate": "make sandbox-vm-static-preflight-disposition-closure-check",
            "allowed_next_state": "closed_local_preview_static_preflight",
        }
        for key, expected in expected_values.items():
            if erg003_row.get(key) != expected:
                failures.append(f"ERG-003 command matrix {key} drifted")

    if closure.get("normalized_response_present") is not False:
        failures.append("ERG-003 normalized response is already present")
    if closure.get("closure_ready") is not False:
        failures.append("ERG-003 closure gate is unexpectedly closure-ready")
    if closure.get("erg_003_status") != "external_review_required":
        failures.append("ERG-003 status drifted before real reviewer disposition")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    response_inbox = _read(repo_root / "docs/codex/enterprise-response-inbox.md")
    command_matrix_doc = _read(repo_root / "docs/codex/enterprise-response-command-matrix.md")
    response_record = _read(
        repo_root / "docs/codex/sandbox-vm-static-preflight-response-application-record.md"
    )
    response_playbook = _read(
        repo_root / "docs/codex/sandbox-vm-static-preflight-response-application-playbook.md"
    )
    triage_doc = _read(repo_root / "docs/codex/sandbox-vm-static-preflight-triage-update.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc:
        failures.append("response application preflight doc is missing")
    else:
        lowered = doc.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in doc:
                failures.append(f"response application preflight doc is missing phrase: {phrase}")
        for phrase in REQUIRED_BLOCKED_BOUNDARIES:
            if phrase not in doc:
                failures.append(
                    f"response application preflight doc is missing blocked boundary: {phrase}"
                )
        for forbidden in [
            "runtime implementation is approved",
            "live VM/container inspection is approved",
            "sandbox orchestration is approved",
            "ERG-003 is closed",
            "ERG-004 is unblocked",
        ]:
            if forbidden.lower() in lowered:
                failures.append(f"response application preflight doc contains: {forbidden}")

    target = "sandbox-vm-static-preflight-response-application-preflight-check"
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in release_check_body:
        failures.append("response application preflight check missing from release-check")
    if target not in release_guardrails:
        failures.append("release guardrails do not require response application preflight check")
    if f"make {target}" not in readme:
        failures.append("README is missing response application preflight command")
    if DOC_REL not in readme:
        failures.append("README is missing response application preflight doc")
    if DOC_REL not in docs_site:
        failures.append("response application preflight is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("response application preflight is missing from review docs")
    if "Sandbox/VM Static Preflight Response Application Preflight" not in review_index:
        failures.append("review-docs index is missing response application preflight")
    for label, source in [
        ("response inbox", response_inbox),
        ("enterprise response command matrix", command_matrix_doc),
        ("response application record", response_record),
        ("response application playbook", response_playbook),
        ("triage update", triage_doc),
    ]:
        if DOC_NAME not in source:
            failures.append(f"{label} is missing response application preflight pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "preflight_doc": DOC_REL,
        "tool_count": 24,
        "erg_003_status": "external_review_required",
        "raw_response_path": RAW_RESPONSE_PATH,
        "normalized_response_path": NORMALIZED_RESPONSE_PATH,
        "response_present": closure.get("normalized_response_present"),
        "closure_ready": closure.get("closure_ready"),
        "allowed_future_status": "closed_local_preview_static_preflight",
        "runtime_changes_allowed": False,
        "normalizes_responses": False,
        "writes_response_files": False,
        "committed_findings_mutated": False,
        "external_review_recorded": False,
        "closes_erg_003": False,
        "erg_004_unblocked": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static preflight response application preflight check",
        f"valid: {str(report['valid']).lower()}",
        f"preflight_doc: {report['preflight_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
        f"raw_response_path: {report['raw_response_path']}",
        f"normalized_response_path: {report['normalized_response_path']}",
        f"response_present: {str(report['response_present']).lower()}",
        f"closure_ready: {str(report['closure_ready']).lower()}",
        f"allowed_future_status: {report['allowed_future_status']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"normalizes_responses: {str(report['normalizes_responses']).lower()}",
        f"writes_response_files: {str(report['writes_response_files']).lower()}",
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
        f"erg_004_unblocked: {str(report['erg_004_unblocked']).lower()}",
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

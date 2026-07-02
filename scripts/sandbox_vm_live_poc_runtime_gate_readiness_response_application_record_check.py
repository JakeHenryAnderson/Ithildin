"""Validate ERG-004 runtime gate-readiness response-application record wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    review_docs,
)
from scripts import (
    sandbox_vm_live_poc_runtime_gate_readiness_response_intake_check as intake,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/"
    "sandbox-vm-live-poc-runtime-gate-readiness-response-application-record.md"
)
DOC_NAME = "sandbox-vm-live-poc-runtime-gate-readiness-response-application-record.md"
NORMALIZED_RESPONSE_PATH = (
    "var/review-runs/sandbox-vm-live-poc-runtime-gate-readiness/normalized-response.json"
)
RAW_RESPONSE_PATH = (
    "var/review-runs/sandbox-vm-live-poc-runtime-gate-readiness-response-inbox/"
    "RAW_RESPONSE_ERG-004-RUNTIME-GATE-READINESS.md"
)

REQUIRED_PHRASES = [
    (
        "Status: process-only response-application record for the `ERG-004` runtime "
        "gate-readiness review."
    ),
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "ready_for_runtime_implementation_gate_review",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-record-check",
    RAW_RESPONSE_PATH,
    NORMALIZED_RESPONSE_PATH,
    "sandbox-vm-live-poc-runtime-gate-readiness",
    "EXT-LIVE-GATE-###",
    "ithildin.external_review.normalized_response",
    "source-level` or `packet-and-source`",
    "approved_for_descriptor_only_runtime_implementation_planning",
    "can_close_source_rows: true",
    "mutates_findings: false",
    "closes_external_review: false",
    "no critical/high findings",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-inbox-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-record-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook-check",
    (
        "ERG-004: ready_for_runtime_implementation_gate_review -> "
        "ready_for_descriptor_only_runtime_implementation_planning"
    ),
    "make release-check",
    "make review-candidate",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "runtime implementation",
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "host writes",
    "network expansion",
    "API/MCP profile loading",
    "SIEM adapter runtime behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "compliance automation",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "runtime implementation is approved",
    "live VM/container inspection is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "ERG-004 is closed",
    "public security product approved",
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
    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    skeleton = _read(
        repo_root
        / "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton.md"
    )
    intake_doc = _read(
        repo_root
        / "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-response-intake.md"
    )
    dry_run_doc = _read(
        repo_root
        / "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run.md"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    intake_report = intake.build_report(repo_root)

    if not doc:
        failures.append("ERG-004 gate-readiness response application record doc is missing")
    else:
        normalized = " ".join(doc.split())
        lowered = doc.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized:
                failures.append(f"response application record is missing phrase: {phrase}")
        for boundary in REQUIRED_BLOCKED_BOUNDARIES:
            if boundary not in doc:
                failures.append(
                    f"response application record is missing blocked boundary: {boundary}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"response application record contains: {phrase}")

    if intake_report.get("valid") is not True:
        failures.append("ERG-004 gate-readiness response intake is not valid")
    if intake_report.get("descriptor_only_planning_allowed") is not False:
        failures.append("intake unexpectedly allows descriptor-only planning without response")
    if intake_report.get("runtime_implementation_allowed") is not False:
        failures.append("intake unexpectedly allows runtime implementation")

    target = "sandbox-vm-live-poc-runtime-gate-readiness-response-application-record-check"
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in release_check_body and f"release-check: {target}" not in makefile:
        failures.append("response application record check missing from release-check")
    if target not in release_guardrails:
        failures.append("release guardrails do not require response application record")
    if f"make {target}" not in readme:
        failures.append("README is missing response application record command")
    if DOC_REL not in readme:
        failures.append("README is missing response application record doc")
    if DOC_REL not in docs_site:
        failures.append("response application record is missing from docs site")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("response application record is missing from review docs")
    if "Sandbox/VM Live POC Runtime Gate Readiness Response Application Record" not in review_index:
        failures.append("review-docs index is missing response application record")
    for label, source in [
        ("decision-record skeleton", skeleton),
        ("response intake", intake_doc),
        ("response dry run", dry_run_doc),
    ]:
        if DOC_NAME not in source:
            failures.append(f"{label} is missing response application record pointer")

    return _report(not failures, failures, "response_application_record_doc")


def _report(valid: bool, failures: list[str], doc_key: str) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "valid": valid,
        "failures": failures,
        doc_key: DOC_REL,
        "tool_count": 24,
        "erg_004_status": "ready_for_runtime_implementation_gate_review",
        "allowed_future_status": "ready_for_descriptor_only_runtime_implementation_planning",
        "requires_real_normalized_response": True,
        "descriptor_only_planning_allowed_now": False,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "host_writes_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin ERG-004 runtime gate-readiness response application record check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"allowed_future_status: {report['allowed_future_status']}",
        "requires_real_normalized_response: "
        f"{str(report['requires_real_normalized_response']).lower()}",
        "descriptor_only_planning_allowed_now: "
        f"{str(report['descriptor_only_planning_allowed_now']).lower()}",
        f"runtime_implementation_allowed: {str(report['runtime_implementation_allowed']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
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

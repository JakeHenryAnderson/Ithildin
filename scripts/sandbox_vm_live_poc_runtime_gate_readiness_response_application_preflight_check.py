"""Validate ERG-004 runtime gate-readiness response-application preflight wiring."""

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
    sandbox_vm_live_poc_runtime_descriptor_contract_check,
    sandbox_vm_live_poc_runtime_descriptor_contract_internal_review_check,
    sandbox_vm_live_poc_runtime_gate_readiness_decision_record_skeleton_check,
    sandbox_vm_live_poc_runtime_gate_readiness_response_dry_run,
    sandbox_vm_live_poc_runtime_gate_readiness_response_inbox,
    sandbox_vm_live_poc_runtime_gate_readiness_response_intake_check,
    sandbox_vm_live_poc_runtime_gate_readiness_review_bundle,
    sandbox_vm_live_poc_runtime_implementation_gate_check,
)
from scripts import (
    sandbox_vm_live_poc_runtime_gate_readiness_response_application_playbook_check as playbook,
)
from scripts import (
    sandbox_vm_live_poc_runtime_gate_readiness_response_application_record_check as record,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/"
    "sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight.md"
)
DOC_NAME = "sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight.md"

REQUIRED_PHRASES = [
    "Status: checked preflight for applying a real `ERG-004` runtime gate-readiness response.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "ready_for_runtime_implementation_gate_review",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight-check",
    "sandbox-vm-live-poc-runtime-gate-readiness-response-inbox.md",
    "sandbox-vm-live-poc-runtime-gate-readiness-response-intake.md",
    "sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run.md",
    "sandbox-vm-live-poc-runtime-gate-readiness-response-application-record.md",
    "sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook.md",
    "sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton.md",
    "sandbox-vm-live-poc-runtime-implementation-gate.md",
    "sandbox-vm-live-poc-runtime-descriptor-contract.md",
    (
        "ERG-004: ready_for_runtime_implementation_gate_review -> "
        "ready_for_descriptor_only_runtime_implementation_planning"
    ),
    "does not approve runtime implementation",
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(record.render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    component_reports = [
        (
            "response inbox",
            sandbox_vm_live_poc_runtime_gate_readiness_response_inbox.build_check_report(
                repo_root
            ),
        ),
        (
            "response intake",
            sandbox_vm_live_poc_runtime_gate_readiness_response_intake_check.build_report(
                repo_root
            ),
        ),
        (
            "response dry run",
            sandbox_vm_live_poc_runtime_gate_readiness_response_dry_run.run_dry_run(
                repo_root
            ),
        ),
        (
            "review bundle",
            sandbox_vm_live_poc_runtime_gate_readiness_review_bundle.build_check_report(
                repo_root
            ),
        ),
        (
            "implementation gate",
            sandbox_vm_live_poc_runtime_implementation_gate_check.build_report(
                repo_root
            ),
        ),
        (
            "descriptor contract",
            sandbox_vm_live_poc_runtime_descriptor_contract_check.build_report(repo_root),
        ),
        (
            "descriptor contract internal review",
            sandbox_vm_live_poc_runtime_descriptor_contract_internal_review_check.build_report(repo_root),
        ),
        (
            "decision-record skeleton",
            sandbox_vm_live_poc_runtime_gate_readiness_decision_record_skeleton_check.build_report(repo_root),
        ),
        ("response application record", record.build_report(repo_root)),
        ("response application playbook", playbook.build_report(repo_root)),
    ]
    for label, report in component_reports:
        if report.get("valid") is not True:
            failures.append(f"{label} is not valid")
            failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))
        if report.get("runtime_implementation_allowed") is not False:
            failures.append(f"{label} unexpectedly allows runtime implementation")
        if report.get("closes_erg_004") is not False and "closes_erg_004" in report:
            failures.append(f"{label} unexpectedly closes ERG-004")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    application_record = _read(
        repo_root
        / "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-response-application-record.md"
    )
    application_playbook = _read(
        repo_root
        / "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook.md"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc:
        failures.append("ERG-004 gate-readiness response application preflight doc is missing")
    else:
        normalized = " ".join(doc.split())
        lowered = doc.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized:
                failures.append(f"response application preflight is missing phrase: {phrase}")
        for boundary in REQUIRED_BLOCKED_BOUNDARIES:
            if boundary not in doc:
                failures.append(
                    "response application preflight is missing blocked boundary: "
                    f"{boundary}"
                )
        for forbidden in [
            "runtime implementation is approved",
            "live VM/container inspection is approved",
            "sandbox orchestration is approved",
            "ERG-004 is closed",
        ]:
            if forbidden.lower() in lowered:
                failures.append(f"response application preflight contains: {forbidden}")

    target = "sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight-check"
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in release_check_body and f"release-check: {target}" not in makefile:
        failures.append("response application preflight check missing from release-check")
    if target not in release_guardrails:
        failures.append("release guardrails do not require response application preflight")
    if f"make {target}" not in readme:
        failures.append("README is missing response application preflight command")
    if DOC_REL not in readme:
        failures.append("README is missing response application preflight doc")
    if DOC_REL not in docs_site:
        failures.append("response application preflight is missing from docs site")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("response application preflight is missing from review docs")
    if (
        "Sandbox/VM Live POC Runtime Gate Readiness Response Application Preflight"
        not in review_index
    ):
        failures.append("review-docs index is missing response application preflight")
    for label, source in [
        ("response application record", application_record),
        ("response application playbook", application_playbook),
    ]:
        if DOC_NAME not in source:
            failures.append(f"{label} is missing response application preflight pointer")

    return record._report(not failures, failures, "response_application_preflight_doc")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())

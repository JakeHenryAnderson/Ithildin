"""Validate the sandbox/VM static preflight triage update checklist."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-static-preflight-triage-update.md"
DOC_NAME = "sandbox-vm-static-preflight-triage-update.md"

REQUIRED_PHRASES = [
    "Status: triage-update checklist for `ERG-003` after favorable external evidence.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "Current `ERG-003` status before real reviewer disposition: `external_review_required`.",
    "make sandbox-vm-static-preflight-triage-update-check",
    "var/review-runs/sandbox-vm-static-preflight/normalized-response.json",
    "sandbox-vm-static-preflight-disposition-closure-check",
    "sandbox-vm-static-preflight-response-dry-run",
    "closed_local_preview_static_preflight",
    "source-review-closure-matrix.md",
    "enterprise-readiness-gap-matrix.md",
    "post-rc-decision-register.md",
    "enterprise-external-review-queue.md",
    "sandbox-vm-live-poc-preconditions-map.md",
    "ERG-004 remains blocked",
    "make release-check",
    "make review-candidate",
]

REQUIRED_STEPS = [
    "Save the raw reviewer response transcript",
    "Normalize the response",
    "Run the closure gate",
    "Add or update reviewer finding files",
    "Update status documents",
    "Preserve blocked runtime boundaries",
    "Regenerate evidence",
]

REQUIRED_BLOCKED_BOUNDARIES = [
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
    "SIEM delivery",
    "compliance automation",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "live VM control is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "runtime implementation is approved",
    "production-ready",
    "secure sandbox",
    "compliance-grade",
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
    doc_path = repo_root / DOC_REL
    doc = _read(doc_path)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    preconditions = _read(repo_root / "docs/codex/sandbox-vm-live-poc-preconditions-map.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("sandbox/VM static preflight triage update checklist is missing")
    lowered = doc.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in doc:
            failures.append(f"triage update checklist is missing phrase: {phrase}")
    for step in REQUIRED_STEPS:
        if step not in doc:
            failures.append(f"triage update checklist is missing step: {step}")
    for boundary in REQUIRED_BLOCKED_BOUNDARIES:
        if boundary not in doc:
            failures.append(f"triage update checklist is missing boundary: {boundary}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"triage update checklist contains forbidden phrase: {phrase}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("triage update checklist is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("triage update checklist is missing from docs-site inputs")
    if DOC_NAME not in review_index:
        failures.append("review-docs index is missing triage update checklist")
    target = "sandbox-vm-static-preflight-triage-update-check"
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in release_check_body:
        failures.append("triage update check missing from release-check")
    if target not in release_guardrails:
        failures.append("release guardrails do not require triage update check")
    if f"make {target}" not in readme:
        failures.append("README is missing triage update command")
    for text, source in [
        (readme, "README"),
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
        (decision_register, "post-RC decision register"),
        (preconditions, "live POC preconditions map"),
    ]:
        if DOC_NAME not in text and DOC_REL not in text:
            failures.append(f"{source} is missing {DOC_NAME}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "triage_update_doc": DOC_REL,
        "tool_count": 24,
        "erg_003_status": "external_review_required",
        "allowed_future_status": "closed_local_preview_static_preflight",
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": False,
        "erg_004_unblocked": False,
        "closes_erg_003": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static preflight triage update check",
        f"valid: {str(report['valid']).lower()}",
        f"triage_update_doc: {report['triage_update_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
        f"allowed_future_status: {report['allowed_future_status']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        "api_mcp_profile_loading_allowed: "
        f"{str(report['api_mcp_profile_loading_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"erg_004_unblocked: {str(report['erg_004_unblocked']).lower()}",
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

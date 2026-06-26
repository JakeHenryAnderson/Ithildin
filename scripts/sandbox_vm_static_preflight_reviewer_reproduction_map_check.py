"""Validate the sandbox/VM static preflight reviewer reproduction map."""

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
DOC_REL = "docs/codex/sandbox-vm-static-preflight-reviewer-reproduction-map.md"

REQUIRED_PHRASES = [
    "Status: reviewer reproduction map for `ERG-003`.",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "Current `ERG-003` status before reviewer disposition: `external_review_required`.",
    "Review Goal",
    "Reproduction Commands",
    "Evidence To Inspect",
    "Expected Safe Outcomes",
    "Reviewer Disposition Boundary",
    "What This Map Does Not Prove",
    "make sandbox-vm-static-preflight-reviewer-reproduction-map-check",
    "make review-run-manifest-refresh",
    "make release-check",
    "make review-candidate",
]

REQUIRED_COMMANDS = [
    "make sandbox-vm-static-profile-preflight-plan-check",
    "make sandbox-vm-static-profile-fixture-contract-check",
    "make sandbox-vm-static-profile-negative-fixtures-check",
    "make sandbox-vm-static-preflight",
    "make sandbox-vm-static-preflight-negative-transcripts",
    "make sandbox-vm-static-preflight-implementation-gate",
    "make sandbox-vm-static-preflight-source-review-packet",
    "make sandbox-vm-static-preflight-source-review-packet-check",
    "make sandbox-vm-static-preflight-external-review-bundle",
    "make sandbox-vm-static-preflight-reviewed-packet-hash",
    "make sandbox-vm-static-preflight-disposition-plan-check",
    "make sandbox-vm-static-preflight-external-response-intake-check",
    "make sandbox-vm-static-preflight-response-dry-run",
    "make sandbox-vm-static-preflight-triage-update-check",
    "make sandbox-vm-static-preflight-disposition-packet",
    "make sandbox-vm-static-preflight-disposition-packet-check",
    "make external-findings-intake-dry-run",
    "make no-new-powers-guardrail",
    "make tool-surface-invariant-gate",
]

REQUIRED_ARTIFACTS = [
    "var/review-packets/v3/sandbox-vm-static-preflight-source-review/",
    "var/review-packets/v3/sandbox-vm-static-preflight-disposition/",
    "var/review-packets/v3/sandbox-vm-static-preflight-negative/",
    "var/review-packets/v3/sandbox-vm-poc-review/",
    "docs/codex/sandbox-vm-static-preflight-response-dry-run.md",
    "docs/codex/sandbox-vm-static-preflight-triage-update.md",
]

REQUIRED_BOUNDARIES = [
    "does not close `ERG-003`",
    "does not approve live VM/container inspection",
    "live VM/container inspection remains blocked",
    "local model invocation remains blocked",
    "Mission Control runtime behavior remains blocked",
    "trusted-host promotion remains blocked",
    "network expansion remains blocked",
    "tool count remains `24`",
    "the reviewed-packet hash helper prints the exact hash",
]

FORBIDDEN_PHRASES = [
    "live VM/container inspection allowed",
    "sandbox orchestration allowed",
    "local model invocation allowed",
    "Mission Control runtime behavior allowed",
    "trusted-host promotion allowed",
    "network expansion allowed",
    "ERG-003 is closed",
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
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("sandbox/VM static preflight reviewer reproduction map is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in doc:
            failures.append(f"reproduction map is missing phrase: {phrase}")
    for command in REQUIRED_COMMANDS:
        if command not in doc:
            failures.append(f"reproduction map is missing command: {command}")
    for artifact in REQUIRED_ARTIFACTS:
        if artifact not in doc:
            failures.append(f"reproduction map is missing artifact: {artifact}")
    for phrase in REQUIRED_BOUNDARIES:
        if phrase not in doc:
            failures.append(f"reproduction map is missing boundary phrase: {phrase}")
    lowered = doc.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"reproduction map contains forbidden phrase: {phrase}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("reproduction map is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("reproduction map is missing from docs-site inputs")
    if "Sandbox/VM Static Preflight Reviewer Reproduction Map" not in review_index:
        failures.append("review-docs index is missing reproduction map")
    target = "sandbox-vm-static-preflight-reviewer-reproduction-map-check"
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in release_check_body:
        failures.append("reproduction map check missing from release-check")
    if target not in release_guardrails:
        failures.append("release guardrails do not require reproduction map check")
    if f"make {target}" not in readme:
        failures.append("README is missing reproduction map command")
    if "sandbox-vm-static-preflight-reviewer-reproduction-map.md" not in runway:
        failures.append("enterprise runway is missing reproduction map pointer")
    if "sandbox-vm-static-preflight-reviewer-reproduction-map.md" not in gap_matrix:
        failures.append("enterprise gap matrix is missing reproduction map pointer")
    if "sandbox-vm-static-preflight-reviewer-reproduction-map.md" not in decision_register:
        failures.append("post-RC decision register is missing reproduction map pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "reproduction_map_doc": DOC_REL,
        "tool_count": 24,
        "erg_003_status": "external_review_required",
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_003": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static preflight reviewer reproduction map check",
        f"valid: {str(report['valid']).lower()}",
        f"reproduction_map_doc: {report['reproduction_map_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
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

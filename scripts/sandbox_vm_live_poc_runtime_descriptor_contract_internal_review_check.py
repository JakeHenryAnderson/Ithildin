"""Validate the ERG-004 descriptor-contract internal xhigh review record."""

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
DOC_REL = (
    "docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract-internal-review.md"
)
DOC_TITLE = "Sandbox/VM Live POC Runtime Descriptor Contract Internal Review"
TARGET = "sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check"

REQUIRED_PHRASES = [
    "Status: internal xhigh review disposition for the planning-only `ERG-004`",
    "runtime descriptor/correlation contract pack.",
    "Current governed tool count: `24`.",
    "Reviewed commit: `99d4f54622bd291a74037c6257e6d68be47dbccd`.",
    "Disposition: `approve_internal_descriptor_contract_checkpoint`.",
    f"make {TARGET}",
    "Critical/high findings: none.",
    "Medium/low/documentation findings: none.",
    "operator-supplied descriptor shape",
    "safe descriptor fields and false-authority flags",
    "Agent Run, tool-call, approval, audit, signed-export, cleanup, and failure",
    "negative fixtures for descriptor shape failures",
    "no-new-powers evidence",
    "release/readiness wiring that keeps runtime implementation blocked",
    "make sandbox-vm-live-poc-runtime-descriptor-contract-check",
    "make status-now",
    "release transcript ended with `returncode=0`",
    "The next allowed action is to continue preparing ERG-004 implementation-gate evidence",
]

REQUIRED_NON_APPROVALS = [
    "runtime implementation",
    "API or MCP behavior",
    "profile loading",
    "persisted descriptor state",
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation by Ithildin",
    "trusted-host promotion",
    "host writes or artifact promotion",
    "network expansion",
    "SIEM adapter runtime behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "compliance automation",
    "shell, Docker, Kubernetes, or browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "plugin SDK behavior",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "runtime implementation is approved",
    "API or MCP behavior is approved",
    "profile loading is approved",
    "persisted descriptor state is approved",
    "live VM/container inspection is approved",
    "VM/container lifecycle management is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "host writes are approved",
    "network expansion is approved",
    "new governed tool powers are approved",
    "public security product approved",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    text = _read(doc_path)
    lowered = text.lower()
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("descriptor-contract internal review doc is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"internal review doc is missing phrase: {phrase}")
    for phrase in REQUIRED_NON_APPROVALS:
        if phrase not in text:
            failures.append(f"internal review doc is missing non-approval: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"internal review doc contains forbidden phrase: {phrase}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("internal review doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("internal review doc is missing from docs-site inputs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing descriptor-contract internal review")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append("descriptor-contract internal review check missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require internal review check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing descriptor-contract internal review command")
    if DOC_REL not in readme:
        failures.append("README is missing descriptor-contract internal review doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "internal_review_doc": DOC_REL,
        "tool_count": 24,
        "disposition": "approve_internal_descriptor_contract_checkpoint",
        "critical_high_findings": 0,
        "medium_low_findings": 0,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "api_mcp_behavior_allowed": False,
        "profile_loading_allowed": False,
        "persisted_descriptor_state_allowed": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_004": False,
        "next_gate_preparation_allowed": True,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC descriptor-contract internal review check",
        f"valid: {str(report['valid']).lower()}",
        f"internal_review_doc: {report['internal_review_doc']}",
        f"tool_count: {report['tool_count']}",
        f"disposition: {report['disposition']}",
        f"critical_high_findings: {report['critical_high_findings']}",
        f"medium_low_findings: {report['medium_low_findings']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        f"api_mcp_behavior_allowed: {str(report['api_mcp_behavior_allowed']).lower()}",
        f"profile_loading_allowed: {str(report['profile_loading_allowed']).lower()}",
        "persisted_descriptor_state_allowed: "
        f"{str(report['persisted_descriptor_state_allowed']).lower()}",
        "live_vm_inspection_allowed: "
        f"{str(report['live_vm_inspection_allowed']).lower()}",
        "sandbox_orchestration_allowed: "
        f"{str(report['sandbox_orchestration_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        "local_model_invocation_allowed: "
        f"{str(report['local_model_invocation_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
        "next_gate_preparation_allowed: "
        f"{str(report['next_gate_preparation_allowed']).lower()}",
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


if __name__ == "__main__":
    raise SystemExit(main())

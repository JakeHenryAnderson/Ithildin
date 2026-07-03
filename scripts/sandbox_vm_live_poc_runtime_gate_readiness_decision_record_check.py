"""Validate the committed ERG-004 runtime gate-readiness decision record."""

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
DOC_REL = "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-decision-record.md"
DOC_NAME = "sandbox-vm-live-poc-runtime-gate-readiness-decision-record.md"

REQUIRED_PHRASES = [
    (
        "Status: committed decision record for `ERG-004` descriptor-only runtime "
        "implementation planning."
    ),
    "Current governed tool count: `24`.",
    "Decision ID: `PRD-SANDBOX-LIVE-GATE-001`.",
    "Decision outcome: `approved_for_descriptor_only_runtime_implementation_planning`.",
    "not external validation",
    "not runtime implementation approval",
    "not `ERG-004` closure",
    "Reviewed commit: `7d3ef7c63099266679f2d32bfc258bec515083de`",
    (
        "Reviewed packet hash: "
        "`sha256:e59ea9e93927ae0ef501fa3785cc9c8dd02c01ea2f766a015798243de1989b00`"
    ),
    "Reviewer type: `internal_ai_high_proxy`",
    "Source access: `packet-and-source`",
    "Finding namespace: `EXT-LIVE-GATE-###`",
    "Finding count: `0`",
    "Critical/high findings: `0`",
    (
        "ERG-004: ready_for_runtime_implementation_gate_review -> "
        "ready_for_descriptor_only_runtime_implementation_planning"
    ),
    "The next allowed work is a descriptor-only runtime implementation-planning/decision sprint.",
    "make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-check",
    "make no-new-powers-guardrail",
    "make tool-surface-invariant-gate",
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
    "VM/container lifecycle management is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "host writes are approved",
    "network expansion is approved",
    "API/MCP profile loading is approved",
    "new governed tool powers are approved",
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
    doc_path = repo_root / DOC_REL
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition(
        "\n\n"
    )[0]

    if not doc_path.exists():
        failures.append("runtime gate-readiness decision record doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized:
                failures.append(
                    "runtime gate-readiness decision record is missing phrase: "
                    + phrase
                )
        for phrase in REQUIRED_BLOCKED_BOUNDARIES:
            if phrase not in text:
                failures.append(
                    "runtime gate-readiness decision record is missing blocked boundary: "
                    + phrase
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    "runtime gate-readiness decision record contains forbidden phrase: "
                    + phrase
                )

    target = "sandbox-vm-live-poc-runtime-gate-readiness-decision-record-check"
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in release_check_body and f"release-check: {target}" not in makefile:
        failures.append("runtime gate-readiness decision record check missing from release-check")
    if f"$(MAKE) {target}" not in review_candidate_body:
        failures.append(
            "runtime gate-readiness decision record check missing from review-candidate"
        )
    if f"make {target}" not in readme:
        failures.append("README is missing runtime gate-readiness decision record command")
    if DOC_REL not in readme:
        failures.append("README is missing runtime gate-readiness decision record doc")
    if DOC_REL not in docs_site:
        failures.append("runtime gate-readiness decision record missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("runtime gate-readiness decision record missing from review docs")
    if "Sandbox/VM Live POC Runtime Gate Readiness Decision Record" not in review_index:
        failures.append("review-docs index is missing runtime gate-readiness decision record")
    if target not in release_guardrails:
        failures.append("release guardrails do not require runtime gate-readiness decision record")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_record_doc": DOC_REL,
        "tool_count": 24,
        "decision_id": "PRD-SANDBOX-LIVE-GATE-001",
        "decision_outcome": "approved_for_descriptor_only_runtime_implementation_planning",
        "erg_004_status": "ready_for_descriptor_only_runtime_implementation_planning",
        "internal_proxy_review": True,
        "external_validation": False,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "descriptor_only_planning_allowed": True,
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
        "Ithildin sandbox/VM live POC runtime gate-readiness decision record check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_record_doc: {report['decision_record_doc']}",
        f"tool_count: {report['tool_count']}",
        f"decision_id: {report['decision_id']}",
        f"decision_outcome: {report['decision_outcome']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"internal_proxy_review: {str(report['internal_proxy_review']).lower()}",
        f"external_validation: {str(report['external_validation']).lower()}",
        "descriptor_only_planning_allowed: "
        f"{str(report['descriptor_only_planning_allowed']).lower()}",
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

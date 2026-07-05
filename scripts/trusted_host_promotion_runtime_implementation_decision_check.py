"""Validate the ERG-005 trusted-host runtime implementation decision draft."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    no_new_powers_guardrail,
    review_docs,
    tool_surface_invariant_gate,
    trusted_host_promotion_limited_runtime_ticket_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/trusted-host-promotion-runtime-implementation-decision.md"
DOC_TITLE = "Trusted-Host Promotion Runtime Implementation Decision"
TARGET = "trusted-host-promotion-runtime-implementation-decision-check"

REQUIRED_PHRASES = [
    "Status: implementation-gate decision draft for the future `ERG-005`",
    "Decision ID: `PRD-TRUSTED-HOST-RUNTIME-IMPLEMENTATION-001`.",
    "Current governed tool count: `24`.",
    "Current `ERG-005` status: `ready_for_runtime_implementation_gate_skeleton`.",
    "Current selected capability: `not selected`.",
    "make trusted-host-promotion-runtime-implementation-decision-check",
    "Approved Future Runtime Slice",
    (
        "one stored sandbox artifact -> one operator-approved host staging placement -> "
        "one read-only evidence record"
    ),
    "closed promotion proposal schema",
    "local SQLite-backed promotion proposal records",
    "local SQLite-backed promotion attempt records",
    "one-time approval binding and compare-and-set approval consumption",
    "trusted host staging destination labels",
    "copy-only placement",
    "post-placement SHA-256 verification",
    "read-only diagnostics",
    "source-review handoff packet using `EXT-TRUSTED-HOST-RUNTIME-###`",
    "Required Future Acceptance Evidence",
    "Explicit Non-Approvals",
    "Stop Conditions",
]

REQUIRED_ACCEPTANCE = [
    "schema validation rejects unknown fields",
    "proposal and approval evidence bind exact artifact SHA-256",
    "replayed approvals and concurrent promotion attempts fail closed",
    (
        "stale artifact hash, changed destination label, policy drift, manifest drift, "
        "and schema drift"
    ),
    "destination resolution rejects arbitrary host paths",
    "successful placement verifies the staged file SHA-256",
    "failure after placement records `recovery_required` or `ambiguous` diagnostics",
    "outputs and audit metadata contain no file contents",
    "no MCP tool, new governed tool",
]

REQUIRED_NON_APPROVALS = [
    "runtime implementation in this checkpoint",
    "promotion beyond a staging-only destination",
    "direct arbitrary host writes",
    "overwrite/delete/move behavior",
    "chmod behavior",
    "broad archive extraction",
    "recursive copy or directory merge behavior",
    "automatic promotion",
    "promotion without exact artifact hash binding",
    "promotion without one-time approval evidence",
    "raw host path exposure",
    "Mission Control runtime behavior",
    "local model invocation by Ithildin",
    "VM/container lifecycle management",
    "sandbox orchestration",
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
    "arbitrary host writes are approved",
    "automatic promotion is approved",
    "Mission Control runtime behavior is approved",
    "sandbox orchestration is approved",
    "new governed tool powers are approved",
    "public security product approved",
    "production ready",
    "enterprise ready",
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
    limited_ticket = trusted_host_promotion_limited_runtime_ticket_check.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)

    if not doc_path.exists():
        failures.append("trusted-host runtime implementation decision doc is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"runtime implementation decision is missing phrase: {phrase}")
    for phrase in REQUIRED_ACCEPTANCE:
        if phrase not in text:
            failures.append(f"runtime implementation decision is missing acceptance: {phrase}")
    for phrase in REQUIRED_NON_APPROVALS:
        if phrase not in text:
            failures.append(f"runtime implementation decision is missing non-approval: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"runtime implementation decision contains forbidden phrase: {phrase}")

    for label, report in [
        ("limited-runtime-ticket", limited_ticket),
        ("tool-surface", tool_surface),
        ("no-new-powers", no_new_powers),
    ]:
        failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))
    if limited_ticket.get("erg_005_status") != "ready_for_limited_runtime_ticket_skeleton":
        failures.append("limited runtime ticket status is not ready")
    if limited_ticket.get("runtime_implementation_allowed") is not False:
        failures.append("limited runtime ticket unexpectedly allows runtime implementation")
    if tool_surface.get("tool_count") != 24:
        failures.append("tool surface tool count is not 24")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("runtime implementation decision is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("runtime implementation decision is missing from docs-site inputs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing runtime implementation decision")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append("runtime implementation decision check is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require runtime implementation decision check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing runtime implementation decision command")
    if DOC_REL not in readme:
        failures.append("README is missing runtime implementation decision doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "runtime_implementation_decision_doc": DOC_REL,
        "decision_id": "PRD-TRUSTED-HOST-RUNTIME-IMPLEMENTATION-001",
        "tool_count": 24,
        "erg_005_status": "ready_for_runtime_implementation_gate_skeleton",
        "implementation_slice": "staging_only_single_artifact",
        "runtime_implementation_allowed_next": True,
        "runtime_changes_allowed_now": False,
        "trusted_host_promotion_allowed_now": False,
        "direct_host_writes_allowed": False,
        "overwrite_delete_move_allowed": False,
        "automatic_promotion_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "closes_erg_005": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host promotion runtime implementation decision check",
        f"valid: {str(report['valid']).lower()}",
        f"runtime_implementation_decision_doc: {report['runtime_implementation_decision_doc']}",
        f"decision_id: {report['decision_id']}",
        f"tool_count: {report['tool_count']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"implementation_slice: {report['implementation_slice']}",
        "runtime_implementation_allowed_next: "
        f"{str(report['runtime_implementation_allowed_next']).lower()}",
        f"runtime_changes_allowed_now: {str(report['runtime_changes_allowed_now']).lower()}",
        "trusted_host_promotion_allowed_now: "
        f"{str(report['trusted_host_promotion_allowed_now']).lower()}",
        f"direct_host_writes_allowed: {str(report['direct_host_writes_allowed']).lower()}",
        f"overwrite_delete_move_allowed: {str(report['overwrite_delete_move_allowed']).lower()}",
        f"automatic_promotion_allowed: {str(report['automatic_promotion_allowed']).lower()}",
        (
            "mission_control_runtime_allowed: "
            f"{str(report['mission_control_runtime_allowed']).lower()}"
        ),
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"closes_erg_005: {str(report['closes_erg_005']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


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


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

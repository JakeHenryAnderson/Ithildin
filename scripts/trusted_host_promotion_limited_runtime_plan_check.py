"""Validate the ERG-005 trusted-host limited runtime implementation plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    no_new_powers_guardrail,
    review_docs,
    tool_surface_invariant_gate,
    trusted_host_promotion_implementation_gate_decision_check,
    trusted_host_promotion_implementation_plan_check,
    trusted_host_promotion_negative_fixtures_check,
    trusted_host_promotion_state_machine_check,
    trusted_host_promotion_zone_contract_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/trusted-host-promotion-limited-runtime-plan.md"
DOC_NAME = "trusted-host-promotion-limited-runtime-plan.md"
TARGET = "trusted-host-promotion-limited-runtime-plan-check"

REQUIRED_PHRASES = [
    "Status: limited runtime implementation-plan checkpoint for `ERG-005`.",
    "Decision ID: `PRD-TRUSTED-HOST-LIMITED-RUNTIME-PLAN-001`.",
    "Current governed tool count: `24`.",
    "Current `ERG-005` status: `ready_for_limited_runtime_implementation_plan`.",
    "Current selected capability: `not selected`.",
    "make trusted-host-promotion-limited-runtime-plan-check",
    (
        "one stored sandbox artifact -> one operator-approved host staging placement -> "
        "one read-only evidence record"
    ),
    "The first slice is staging-only.",
    "one generated promotion proposal",
    "one one-time approval",
    "one promotion attempt per approval ID",
    "one artifact hash",
    "stored sandbox artifact",
    "operator-approved host staging placement",
    "read-only diagnostics",
    "If the implementation surface becomes ambiguous",
    "if useful behavior appears to require broader host writes",
    "if a gate fails three times for the same reason",
    "request a focused High/XHigh internal source review",
    "prepare an external review packet for GPT 5.5 Pro or a human reviewer",
    "pivot to a lower-risk enterprise lane",
    "mark the lane `blocked` or `accepted_deferred`",
    "Do not keep adding documentation, gates, or packet polish",
    "Before any future placement attempt, the executor must revalidate",
    "Approval consumption and attempt creation must be compare-and-set guarded",
    "Negative Fixtures Required Before Implementation",
    "Source Review And Pivot Gate",
    "Implementation must not start if:",
    "Choose option 1 if there is any ambiguity.",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "runtime implementation",
    "trusted-host promotion",
    "direct host writes",
    "overwrite/delete/move behavior",
    "broad archive extraction",
    "automatic promotion",
    "Mission Control runtime behavior",
    "local model invocation",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "SIEM adapter behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "shell/Docker/Kubernetes/browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "compliance automation",
    "plugin SDK behavior",
    "new governed tool powers",
    "public/security-product positioning",
]

REQUIRED_REJECTION_CASES = [
    "missing approval",
    "expired approval",
    "replayed approval",
    "approval scope mismatch",
    "wrong tool name",
    "wrong principal",
    "disabled or unknown principal",
    "disabled workspace",
    "stale artifact hash",
    "changed destination label",
    "changed trusted host descriptor hash",
    "policy drift",
    "manifest drift",
    "schema/tool input drift",
    "path traversal",
    "encoded traversal",
    "absolute path",
    "hidden/sensitive destination",
    "`.git` destination",
    "symlink",
    "hardlink",
    "directory target",
    "existing destination conflict",
    "overwrite/delete/move attempt",
    "archive extraction attempt",
    "oversized artifact",
    "binary or unsupported artifact label",
    "raw path leakage attempt",
    "file-content leakage attempt",
]

FORBIDDEN_PHRASES = [
    "runtime implementation is approved",
    "trusted-host promotion is approved",
    "direct host writes are approved",
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
    normalized_text = " ".join(text.split())
    lowered = text.lower()
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    operator_next = _read(repo_root / "docs/codex/enterprise-operator-next-action.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("trusted-host limited runtime plan doc is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text and phrase not in normalized_text:
            failures.append(f"limited runtime plan is missing phrase: {phrase}")
    for phrase in REQUIRED_BLOCKED_BOUNDARIES:
        if phrase not in text:
            failures.append(f"limited runtime plan is missing blocked boundary: {phrase}")
    for phrase in REQUIRED_REJECTION_CASES:
        if phrase not in text:
            failures.append(f"limited runtime plan is missing rejection case: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"limited runtime plan contains forbidden phrase: {phrase}")

    upstream_reports = [
        (
            "implementation-gate-decision",
            trusted_host_promotion_implementation_gate_decision_check.build_report(repo_root),
        ),
        (
            "implementation-plan",
            trusted_host_promotion_implementation_plan_check.build_report(repo_root),
        ),
        ("state-machine", trusted_host_promotion_state_machine_check.build_report(repo_root)),
        (
            "negative-fixtures",
            trusted_host_promotion_negative_fixtures_check.build_report(repo_root),
        ),
        ("zone-contract", trusted_host_promotion_zone_contract_check.build_report(repo_root)),
        ("tool-surface", tool_surface_invariant_gate.build_report(repo_root)),
        ("no-new-powers", no_new_powers_guardrail.build_report(repo_root)),
    ]
    for label, report in upstream_reports:
        failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    decision = dict(upstream_reports[0][1])
    negative_fixtures = dict(upstream_reports[3][1])
    tool_surface = dict(upstream_reports[5][1])

    if decision.get("goal_c_outcome") != "ready_for_limited_runtime_implementation_plan":
        failures.append("Goal C decision does not allow limited runtime implementation planning")
    if decision.get("runtime_implementation_allowed") is not False:
        failures.append("Goal C decision unexpectedly allows runtime implementation")
    if decision.get("trusted_host_promotion_allowed") is not False:
        failures.append("Goal C decision unexpectedly allows trusted-host promotion")
    if negative_fixtures.get("negative_cases_rejected") != 24:
        failures.append("negative fixture rejection count is not 24")
    if tool_surface.get("tool_count") != 24:
        failures.append("tool surface tool count is not 24")

    for source_name, linked_text in [
        ("README", readme),
        ("docs site", docs_site),
        ("enterprise operator next action", operator_next),
    ]:
        if DOC_NAME not in linked_text and DOC_REL not in linked_text:
            failures.append(f"{source_name} is missing {DOC_NAME}")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("limited runtime plan is missing from review docs")
    if "Trusted-Host Promotion Limited Runtime Plan" not in review_index:
        failures.append("review-docs index is missing trusted-host limited runtime plan")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append("limited runtime plan check is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require limited runtime plan check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing limited runtime plan command")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "plan_doc": DOC_REL,
        "decision_id": "PRD-TRUSTED-HOST-LIMITED-RUNTIME-PLAN-001",
        "tool_count": 24,
        "erg_005_status": "ready_for_limited_runtime_implementation_plan",
        "next_allowed_step": "focused_limited_runtime_source_review_or_ticket_skeleton",
        "implementation_planning_allowed": True,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "direct_host_writes_allowed": False,
        "automatic_promotion_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "stop_and_reassess_required_on_ambiguity": True,
        "external_review_break_glass_allowed": True,
        "closes_erg_005": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host promotion limited runtime plan check",
        f"valid: {str(report['valid']).lower()}",
        f"plan_doc: {report['plan_doc']}",
        f"decision_id: {report['decision_id']}",
        f"tool_count: {report['tool_count']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"next_allowed_step: {report['next_allowed_step']}",
        "implementation_planning_allowed: "
        f"{str(report['implementation_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        "trusted_host_promotion_allowed: "
        f"{str(report['trusted_host_promotion_allowed']).lower()}",
        f"direct_host_writes_allowed: {str(report['direct_host_writes_allowed']).lower()}",
        f"automatic_promotion_allowed: {str(report['automatic_promotion_allowed']).lower()}",
        "stop_and_reassess_required_on_ambiguity: "
        f"{str(report['stop_and_reassess_required_on_ambiguity']).lower()}",
        "external_review_break_glass_allowed: "
        f"{str(report['external_review_break_glass_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_005: {str(report['closes_erg_005']).lower()}",
    ]
    failures = report["failures"]
    if isinstance(failures, list) and failures:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in failures)
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


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

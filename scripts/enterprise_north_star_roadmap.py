"""Validate the enterprise north-star roadmap."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_dependency_ladder,
    enterprise_operator_next_action,
    enterprise_readiness_gap_matrix_check,
    enterprise_response_status_board,
    enterprise_transition_map,
    next_capability_readiness,
    review_docs,
    v1_progress_assessment,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-north-star-roadmap.md"
DOC_TITLE = "Enterprise North-Star Roadmap"

REQUIRED_DOC_PHRASES = [
    "Status: checked north-star map",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "make enterprise-north-star-roadmap",
    "v1.0 local-preview RC candidate",
    "Active enterprise route: preparation of the `PIS-003` entry decision record after the "
    "valid `PIS-002` continuation decision; `ERG-006`/`ERG-007` remain planning-only scope.",
    "Historical dual-send route: `ERG-003` then `ERG-002`.",
    "`ERG-003`: static sandbox/VM preflight disposition",
    "`ERG-002`: Mission Control display/import planning review",
    "make release-check",
    "make review-candidate",
    "make production-identity-storage-pis-002-continuation-decision-check",
    "make production-identity-storage-pis-002-sandbox-descriptor-repository-internal-review-check",
    "make no-new-powers-guardrail",
    "make tool-surface-invariant-gate",
    "make enterprise-review-send-refresh",
    "make handoff-dry-run",
    "make enterprise-send-now",
    "make enterprise-review-send-receipt-template",
    "make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json",
    "make enterprise-dual-response-inbox",
    "var/review-runs/enterprise-dual-response-inbox/",
    "make enterprise-response-inbox",
    "make enterprise-response-status-board",
    "make enterprise-response-intake-quickstart",
    "make enterprise-response-paste-preflight",
    "A favorable `ERG-003` response can close static preflight only",
    (
        "A favorable `ERG-002` response can authorize a Mission Control-side "
        "design-only decision record only"
    ),
    "No row in this roadmap approves new governed tool powers",
    "When To Ask For External Roadmap Review",
]

CANONICAL_DOCS = [
    "docs/codex/v1.0-rc-status.md",
    "docs/codex/v1.0-progress-assessment.md",
    "docs/codex/enterprise-current-checkpoint.md",
    "docs/codex/enterprise-dependency-ladder.md",
    "docs/codex/enterprise-transition-map.md",
    "docs/codex/enterprise-readiness-gap-matrix.md",
    "docs/codex/enterprise-response-intake-quickstart.md",
    "docs/codex/enterprise-response-paste-preflight.md",
]

PHASE_ROWS = [
    "v1_local_preview_rc",
    "erg_003_static_preflight",
    "erg_002_mission_control_display",
    "erg_004_live_sandbox_vm_poc",
    "erg_005_trusted_host_promotion",
    "enterprise_architecture_lanes",
]

BLOCKED_PHRASES = [
    "shell execution",
    "Docker socket access",
    "Kubernetes tools",
    "browser automation",
    "arbitrary HTTP methods",
    "broad filesystem writes",
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "SIEM adapter runtime behavior",
    "production identity or enterprise RBAC",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP hosting",
    "compliance automation",
    "public/security-product positioning",
    "new governed tool powers",
]

FORBIDDEN_PHRASES = [
    "enterprise-ready product",
    "production-ready",
    "approved for live VM",
    "Mission Control may execute",
    "sandbox orchestration allowed",
    "public security product approved",
    "compliance certified",
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
    ladder = enterprise_dependency_ladder.build_report(repo_root)
    transition = enterprise_transition_map.build_report(repo_root)
    progress = v1_progress_assessment.build_report(repo_root)
    gap_matrix = enterprise_readiness_gap_matrix_check.build_report(repo_root)
    response_status = enterprise_response_status_board.build_report(repo_root)
    capability = next_capability_readiness.build_report(repo_root)
    operator_next_action = enterprise_operator_next_action.build_report(repo_root)

    for label, report in [
        ("enterprise-dependency-ladder", ladder),
        ("enterprise-transition-map", transition),
        ("v1-progress-assessment", progress),
        ("enterprise-readiness-gap-matrix", gap_matrix),
        ("enterprise-response-status-board", response_status),
        ("next-capability-readiness", capability),
        ("enterprise-operator-next-action", operator_next_action),
    ]:
        if report.get("valid") is not True:
            failures.append(f"{label} is not valid")
            failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    if progress.get("tool_count") != 24:
        failures.append("progress assessment tool count is not 24")
    if capability.get("next_candidate") != "not selected":
        failures.append("next capability candidate is selected")
    if response_status.get("response_present_count") != 0:
        failures.append("enterprise response status reports present responses")
    if response_status.get("closure_ready_count") != 0:
        failures.append("enterprise response status reports closure-ready lanes")
    if gap_matrix.get("gap_count") != 10:
        failures.append("enterprise gap count is not 10")

    boundary_flags = {
        "capability_expansion_allowed": False,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }
    for key, expected in boundary_flags.items():
        for label, report in [
            ("response status", response_status),
            ("progress assessment", progress),
        ]:
            if key in report and report[key] is not expected:
                failures.append(f"{label} boundary flag drifted: {key}")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    if not doc:
        failures.append("enterprise north-star roadmap doc is missing")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            failures.append(f"enterprise north-star roadmap doc is missing phrase: {phrase}")
    for doc_rel in CANONICAL_DOCS:
        if doc_rel not in doc:
            failures.append(f"enterprise north-star roadmap is missing canonical doc: {doc_rel}")
    for phase in PHASE_ROWS:
        if phase not in doc:
            failures.append(f"enterprise north-star roadmap is missing phase row: {phase}")
    for phrase in BLOCKED_PHRASES:
        if phrase not in doc:
            failures.append(f"enterprise north-star roadmap is missing blocked phrase: {phrase}")
    lowered = doc.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"enterprise north-star roadmap contains forbidden phrase: {phrase}")

    if "enterprise-north-star-roadmap:" not in makefile:
        failures.append("Make target is missing: enterprise-north-star-roadmap")
    if (
        "enterprise-north-star-roadmap" not in release_check_body
        and "release-check: enterprise-north-star-roadmap" not in makefile
    ):
        failures.append("enterprise-north-star-roadmap is missing from release-check")
    if "$(MAKE) enterprise-north-star-roadmap" not in review_candidate_body:
        failures.append("enterprise-north-star-roadmap is missing from review-candidate")
    if "make enterprise-north-star-roadmap" not in readme:
        failures.append("README is missing enterprise north-star roadmap command")
    if DOC_REL not in readme:
        failures.append("README is missing enterprise north-star roadmap doc")
    if DOC_REL not in docs_site:
        failures.append("enterprise north-star roadmap is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise north-star roadmap is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise north-star roadmap")
    if "enterprise-north-star-roadmap" not in release_guardrails:
        failures.append("release guardrails do not require enterprise north-star roadmap")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "roadmap_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": capability.get("next_candidate"),
        "recommended_send_set": operator_next_action.get("recommended_send_set", []),
        "recommended_next_enterprise_review": operator_next_action.get(
            "recommended_next_enterprise_review"
        ),
        "historical_dual_send_set": ["ERG-003", "ERG-002"],
        "historical_next_enterprise_review": "ERG-003",
        "enterprise_gap_count": gap_matrix.get("gap_count"),
        "response_present_count": response_status.get("response_present_count"),
        "closure_ready_count": response_status.get("closure_ready_count"),
        "phase_count": len(PHASE_ROWS),
        **boundary_flags,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise north-star roadmap",
        f"valid: {str(report['valid']).lower()}",
        f"roadmap_doc: {report['roadmap_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report.get('selected_capability', 'unknown')}",
        "recommended_send_set: " + ", ".join(report.get("recommended_send_set") or []),
        "recommended_next_enterprise_review: "
        f"{report.get('recommended_next_enterprise_review', 'unknown')}",
        "historical_dual_send_set: " + ", ".join(report.get("historical_dual_send_set") or []),
        "historical_next_enterprise_review: "
        f"{report.get('historical_next_enterprise_review', 'unknown')}",
        f"enterprise_gap_count: {report.get('enterprise_gap_count', 'unknown')}",
        f"response_present_count: {report.get('response_present_count', 'unknown')}",
        f"closure_ready_count: {report.get('closure_ready_count', 'unknown')}",
        f"phase_count: {report['phase_count']}",
    ]
    for key in [
        "runtime_changes_allowed",
        "mission_control_runtime_allowed",
        "live_vm_inspection_allowed",
        "sandbox_orchestration_allowed",
        "trusted_host_promotion_allowed",
        "siem_adapter_allowed",
        "compliance_automation_allowed",
        "public_security_product_positioning_allowed",
        "new_power_classes_allowed",
    ]:
        lines.append(f"{key}: {str(report[key]).lower()}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

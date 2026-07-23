"""Validate the enterprise external-review queue and release-readiness wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import enterprise_operator_next_action, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-external-review-queue.md"
DOC_NAME = "enterprise-external-review-queue.md"

QUEUE_ROWS = [
    ("ERG-003", "PRD-SANDBOX-PREFLIGHT-001", "sandbox-vm-static-preflight-disposition-packet.md"),
    ("ERG-002", "PRD-MC-DISPLAY-001", "mission-control-display-external-review-bundle.md"),
    ("ERG-005", "PRD-TRUSTED-HOST-001", "trusted-host-promotion-external-review-bundle.md"),
    (
        "ERG-006",
        "PRD-PROD-IAM-STORAGE-001",
        "production-identity-storage-external-review-bundle.md",
    ),
    (
        "ERG-007",
        "PRD-PROD-IAM-STORAGE-001",
        "production-identity-storage-external-review-bundle.md",
    ),
    ("ERG-008", "PRD-SIEM-EXPORT-001", "siem-export-adapter-external-review-bundle.md"),
    ("ERG-009", "PRD-COMPLIANCE-MAPPING-001", "compliance-mapping-external-review-bundle.md"),
    ("ERG-004", "PRD-SANDBOX-LIVE-POC-001", "sandbox-vm-live-poc-decision-packet.md"),
    (
        "ERG-010",
        "PRD-PUBLIC-POSITIONING-001",
        "public-positioning-external-review-bundle.md",
    ),
]

REQUIRED_PHRASES = [
    "Status: planning-only queue for post-RC enterprise review lanes.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "make enterprise-external-review-queue-check",
    "Active Route Versus Historical Queue",
    "Current active route: external target and signed-receipt input wait; no review send is "
    "active.",
    "make enterprise-active-route-clarity",
    "Historical Review Queue",
    "Dependency Order",
    "Historical recommended review: `ERG-003` static sandbox/VM preflight disposition.",
    f"`{enterprise_operator_next_action.PIS_003_EXTERNAL_INPUT_ACTION}`",
    "Runtime allowed",
    "public/security-product positioning remains a no-go lane",
]

BLOCKED_BOUNDARIES = [
    "Mission Control runtime behavior",
    "sandbox orchestration",
    "trusted-host promotion",
    "local model invocation",
    "SIEM adapters",
    "compliance automation",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "runtime behavior is approved",
    "Mission Control may execute",
    "live sandbox work is approved",
    "trusted-host promotion is implemented",
    "SIEM adapter is implemented",
    "compliance automation approved",
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
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    runway = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(encoding="utf-8")
    matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(encoding="utf-8")
    release_guardrails = (repo_root / "scripts/release_guardrails.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("enterprise external-review queue doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"queue doc is missing phrase: {phrase}")
        for phrase in BLOCKED_BOUNDARIES:
            if phrase not in text:
                failures.append(f"queue doc is missing blocked boundary: {phrase}")
        for gap_id, prd_id, packet in QUEUE_ROWS:
            if f"`{gap_id}`" not in text:
                failures.append(f"queue doc is missing gap id: {gap_id}")
            if f"`{prd_id}`" not in text:
                failures.append(f"queue doc is missing decision id: {prd_id}")
            if packet not in text:
                failures.append(f"queue doc is missing packet pointer: {packet}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"queue doc contains forbidden phrase: {phrase}")
        if text.count("`false`") < 8:
            failures.append("queue doc must mark every review row runtime_allowed false")

    for path in [
        "docs/codex/sandbox-vm-static-preflight-external-review-bundle.md",
        "docs/codex/sandbox-vm-static-preflight-disposition-packet.md",
        "docs/codex/sandbox-vm-static-preflight-external-response-intake.md",
        "docs/codex/sandbox-vm-static-preflight-triage-update.md",
        "docs/codex/sandbox-vm-static-preflight-response-application-playbook.md",
        "docs/codex/mission-control-display-external-review-bundle.md",
        "docs/codex/mission-control-integration-readiness-packet.md",
        "docs/codex/mission-control-display-external-response-intake.md",
        "docs/codex/trusted-host-promotion-disposition-packet.md",
        "docs/codex/trusted-host-promotion-external-review-bundle.md",
        "docs/codex/trusted-host-promotion-external-response-intake.md",
        "docs/codex/production-identity-storage-disposition-packet.md",
        "docs/codex/production-identity-storage-external-review-bundle.md",
        "docs/codex/production-identity-storage-external-response-intake.md",
        "docs/codex/siem-export-adapter-disposition-packet.md",
        "docs/codex/siem-export-adapter-external-review-bundle.md",
        "docs/codex/siem-export-adapter-external-response-intake.md",
        "docs/codex/compliance-mapping-disposition-packet.md",
        "docs/codex/compliance-mapping-external-response-intake.md",
        "docs/codex/sandbox-vm-live-poc-decision-packet.md",
        "docs/codex/sandbox-vm-live-poc-external-response-intake.md",
        "docs/codex/sandbox-vm-live-poc-response-dry-run.md",
        "docs/codex/public-security-product-positioning-decision-intake.md",
    ]:
        if not (repo_root / path).exists():
            failures.append(f"referenced queue evidence doc is missing: {path}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise external-review queue is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("enterprise external-review queue is missing from docs-site inputs")
    if DOC_NAME not in review_index:
        failures.append("review-docs index is missing enterprise external-review queue")
    if DOC_NAME not in runway:
        failures.append("enterprise runway is missing external-review queue")
    if DOC_NAME not in matrix:
        failures.append("enterprise gap matrix is missing external-review queue")
    if DOC_NAME not in register:
        failures.append("post-RC decision register is missing external-review queue")
    if "enterprise-external-review-queue-check:" not in makefile:
        failures.append("Make target is missing: enterprise-external-review-queue-check")
    if "enterprise-external-review-queue-check" not in release_check_body:
        failures.append("enterprise-external-review-queue-check is missing from release-check")
    if "enterprise-external-review-queue-check" not in release_guardrails:
        failures.append("release guardrails do not require enterprise external-review queue")
    if "make enterprise-external-review-queue-check" not in readme:
        failures.append("README is missing enterprise external-review queue command")
    if DOC_REL not in readme:
        failures.append("README is missing enterprise external-review queue doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "queue_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": "not selected",
        "queue_row_count": 8,
        "active_route": "external_operator_input_wait",
        "recommended_next_review": "external_operator_input_required",
        "historical_recommended_review": "ERG-003",
        "expected_action": enterprise_operator_next_action.PIS_003_EXTERNAL_INPUT_ACTION,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise external-review queue check",
        f"valid: {str(report['valid']).lower()}",
        f"queue_doc: {report['queue_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        f"queue_row_count: {report['queue_row_count']}",
        f"active_route: {report['active_route']}",
        f"recommended_next_review: {report['recommended_next_review']}",
        f"historical_recommended_review: {report['historical_recommended_review']}",
        f"expected_action: {report['expected_action']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

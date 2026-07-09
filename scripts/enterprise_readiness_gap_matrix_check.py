"""Validate the enterprise-readiness gap matrix and its release-readiness wiring."""

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
MATRIX_DOC = ROOT / "docs/codex/enterprise-readiness-gap-matrix.md"

REQUIRED_GAPS = [
    "ERG-001",
    "ERG-002",
    "ERG-003",
    "ERG-004",
    "ERG-005",
    "ERG-006",
    "ERG-007",
    "ERG-008",
    "ERG-009",
    "ERG-010",
]

REQUIRED_PHRASES = [
    "Status: design-only enterprise gap matrix beyond the v1.0 local-preview RC.",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "`closed_local_preview`",
    "`planning_only`",
    "`blocked`",
    "`external_review_required`",
    "Mission Control display/importer",
    "Sandbox/VM static preflight",
    "Live sandbox/VM worker proof of concept",
    "descriptor_only_local_preview_disposition_ready",
    "sandbox-vm-live-poc-runtime-descriptor-only-implementation.md",
    "sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle.md",
    "sandbox-vm-live-poc-runtime-descriptor-only-response-inbox.md",
    "sandbox-vm-live-poc-runtime-descriptor-only-send-receipt.md",
    "Trusted-host artifact promotion",
    "Production identity and multi-user authorization",
    "Durable runtime storage and retention",
    "SIEM-shaped export adapter",
    "Compliance mapping support",
    "Public/security-product positioning",
    "public-security-product-positioning-decision-intake.md",
    "sandbox-vm-static-preflight-response-application-playbook.md",
    "Allowed current claims",
    "Blocked current claims",
    "post-RC decision record",
    "Mission Control outside execution, policy, approval, audit authority",
    "Current active route: `ERG-005` trusted-host promotion review.",
    "Historical/fallback route: `ERG-003` static sandbox/VM preflight",
    "prepare_erg005_trusted_host_promotion_review",
]

REQUIRED_BLOCKED_PHRASES = [
    "production deployment readiness",
    "organization identity/RBAC",
    "OS-isolated sandbox guarantee",
    "SIEM custody",
    "custody-grade or regulatory audit guarantee",
    "HIPAA/GLBA/SOX/GDPR compliance automation",
    "Mission Control execution authority",
    "Ithildin-managed VM/container lifecycle",
    "trusted-host promotion",
]

FORBIDDEN_PHRASES = [
    "runtime behavior is approved",
    "Mission Control may execute",
    "Ithildin starts containers",
    "trusted-host promotion is implemented",
    "production identity is implemented",
    "runtime Postgres is enabled",
    "SIEM custody is implemented",
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
    operator_next = enterprise_operator_next_action.build_report(repo_root)
    doc_rel = MATRIX_DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    runway = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    text = ""
    if not doc_path.exists():
        failures.append("enterprise-readiness gap matrix doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for gap_id in REQUIRED_GAPS:
            if f"`{gap_id}`" not in text:
                failures.append(f"enterprise-readiness gap matrix is missing gap: {gap_id}")
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"enterprise-readiness gap matrix is missing phrase: {phrase}")
        for phrase in REQUIRED_BLOCKED_PHRASES:
            if phrase not in text:
                failures.append(
                    "enterprise-readiness gap matrix is missing blocked phrase: "
                    f"{phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    "enterprise-readiness gap matrix contains forbidden phrase: "
                    f"{phrase}"
                )

    failures.extend(_active_route_failures(operator_next))

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("enterprise-readiness gap matrix doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("enterprise-readiness gap matrix doc is missing from docs-site inputs")
    if "enterprise-readiness-gap-matrix-check:" not in makefile:
        failures.append("Make target is missing: enterprise-readiness-gap-matrix-check")
    if "enterprise-readiness-gap-matrix-check" not in release_check_body:
        failures.append("enterprise-readiness-gap-matrix-check is missing from release-check")
    if "make enterprise-readiness-gap-matrix-check" not in readme:
        failures.append("README is missing enterprise-readiness gap matrix command")
    if "enterprise-readiness-gap-matrix.md" not in readme:
        failures.append("README is missing enterprise-readiness gap matrix doc")
    if "enterprise-readiness-gap-matrix.md" not in runway:
        failures.append("enterprise runway is missing gap matrix pointer")
    if "enterprise-readiness-gap-matrix.md" not in register:
        failures.append("post-RC decision register is missing gap matrix pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "matrix_doc": doc_rel,
        "gap_count": sum(1 for gap_id in REQUIRED_GAPS if f"`{gap_id}`" in text),
        "tool_count": 24,
        "selected_capability": "not selected",
        "active_route_source": "enterprise-operator-next-action",
        "active_send_set": operator_next.get("recommended_send_set", []),
        "recommended_next_enterprise_review": operator_next.get(
            "recommended_next_enterprise_review"
        ),
        "next_action": operator_next.get("next_action"),
        "historical_fallback_route": ["ERG-003", "ERG-002"],
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "production_identity_allowed": False,
        "compliance_claims_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise readiness gap matrix check",
        f"valid: {str(report['valid']).lower()}",
        f"matrix_doc: {report['matrix_doc']}",
        f"gap_count: {report['gap_count']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        f"active_route_source: {report['active_route_source']}",
        "active_send_set: " + ", ".join(report["active_send_set"]),
        "recommended_next_enterprise_review: "
        f"{report['recommended_next_enterprise_review']}",
        f"next_action: {report['next_action']}",
        "historical_fallback_route: "
        + ", ".join(report["historical_fallback_route"]),
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _active_route_failures(operator_next: dict[str, Any]) -> list[str]:
    failures = [
        f"enterprise-operator-next-action: {failure}"
        for failure in operator_next.get("failures", [])
    ]
    if operator_next.get("valid") is not True:
        failures.append("enterprise operator next action is not valid")
    if operator_next.get("recommended_send_set") != ["ERG-005"]:
        failures.append("active enterprise send set is not ERG-005")
    if operator_next.get("recommended_next_enterprise_review") != "ERG-005":
        failures.append("active enterprise review is not ERG-005")
    if operator_next.get("next_action") != "prepare_erg005_trusted_host_promotion_review":
        failures.append("active enterprise action is not ERG-005 trusted-host review")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate the Mission Control integration implementation ticket."""

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
DOC_REL = "docs/codex/mission-control-integration-implementation-ticket.md"

REQUIRED_PHRASES = [
    "Status: planning-only cross-repo implementation ticket",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "Runtime importer implementation remains blocked",
    "Mission Control Implementation Slices",
    "Allowed Mission Control Files",
    "Validation Commands",
    "Required Mission Control Tests",
    "Required Mission Control Evidence",
    "Explicit Non-Goals",
    "Stop Conditions",
    "Done When",
    "make mission-control-integration-implementation-ticket-check",
    "node scripts/check-ithildin-integration-docs.mjs",
    "npm test",
]

REQUIRED_INPUTS = [
    "mission-control-display-integration-proposal.md",
    "mission-control-display-importer-plan.md",
    "mission-control-side-handoff-plan.md",
    "mission-control-handoff-schema-contract.md",
    "mission-control-handoff-negative-fixtures.md",
    "mission-control-enterprise-status-import-contract.md",
    "mission-control-enterprise-status-fixtures.md",
    "mission-control-enterprise-status-acceptance-matrix.md",
    "mission-control-enterprise-status-reference-validator.md",
    "hello-world-mission-control-handoff.md",
    "var/review-packets/v3/mission-control-display/",
    "mission-control-handoff.json",
    "docs/ithildin-integration-roadmap.md",
    "scripts/check-ithildin-integration-docs.mjs",
    "apps/desktop/src/App.tsx",
    "apps/desktop/src/App.test.ts",
]

REQUIRED_TESTS = [
    "valid metadata-only handoff import",
    "valid enterprise status fixture accepted as display-only status evidence",
    "all `MC-STATUS-NEG-001` through `MC-STATUS-NEG-012` fixtures rejected with safe reason labels",
    "`MC-STATUS-NEG-011` unsafe action command rejection with `unsupported_action_command`",
    "`MC-STATUS-NEG-012` unsafe handoff artifact rejection with `unsafe_handoff_artifact`",
    "unsupported schema rejection",
    "non-`metadata_only` status rejection",
    "missing display allowlist rejection",
    "missing hidden-field denylist rejection",
    "missing warning chips rejection",
    "absolute attachment path rejection",
    "parent-traversal attachment path rejection",
    "URL attachment rejection",
    "hash mismatch warning or rejection",
    "stale packet warning",
    "Mission Control execution-authority overclaim rejection",
    "Mission Control policy/approval/audit-authority overclaim rejection",
    "raw prompt, file content, diff, response-body",
]

REQUIRED_NON_GOALS = [
    "Mission Control execution authority",
    "Mission Control policy authority",
    "Mission Control approval authority",
    "Mission Control audit authority",
    "Mission Control callbacks into Ithildin",
    "Mission Control polling or mutating Ithildin APIs",
    "Mission Control-created approvals",
    "Mission Control execution of imported `action_commands`",
    "local model invocation",
    "VM/container lifecycle control",
    "sandbox orchestration",
    "trusted-host promotion",
    "shell execution",
    "remote MCP",
    "SIEM adapters",
    "production IAM",
    "runtime Postgres",
    "hosted telemetry",
    "compliance automation",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "Mission Control may execute",
    "Mission Control may approve",
    "Mission Control is the policy authority",
    "Mission Control is the audit authority",
    "runtime importer is approved",
    "trusted-host promotion is implemented",
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
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    packet_script = _read(repo_root / "scripts/mission_control_display_review_packet.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    enterprise = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("Mission Control integration implementation ticket is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"ticket is missing phrase: {phrase}")
        for phrase in REQUIRED_INPUTS:
            if phrase not in text:
                failures.append(f"ticket is missing input reference: {phrase}")
        for phrase in REQUIRED_TESTS:
            if phrase not in text:
                failures.append(f"ticket is missing test family: {phrase}")
        for phrase in REQUIRED_NON_GOALS:
            if phrase not in text:
                failures.append(f"ticket is missing non-goal: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"ticket contains forbidden phrase: {phrase}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("ticket is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("ticket is missing from docs-site inputs")
    if DOC_REL not in packet_script:
        failures.append("Mission Control display review packet does not bundle ticket")
    if "Mission Control Integration Implementation Ticket" not in review_index:
        failures.append("review-docs index is missing ticket")
    if "mission-control-integration-implementation-ticket-check:" not in makefile:
        failures.append(
            "Make target is missing: mission-control-integration-implementation-ticket-check"
        )
    if "mission-control-integration-implementation-ticket-check" not in release_check_body:
        failures.append(
            "mission-control-integration-implementation-ticket-check missing from release-check"
        )
    if "mission-control-integration-implementation-ticket-check" not in release_guardrails:
        failures.append("release guardrails do not require the ticket check")
    if "make mission-control-integration-implementation-ticket-check" not in readme:
        failures.append("README is missing ticket check command")
    if "mission-control-integration-implementation-ticket.md" not in readme:
        failures.append("README is missing ticket doc")
    if "mission-control-integration-implementation-ticket.md" not in enterprise:
        failures.append("enterprise runway is missing ticket doc")
    if "mission-control-integration-implementation-ticket.md" not in gap_matrix:
        failures.append("enterprise gap matrix is missing ticket doc")
    if "mission-control-integration-implementation-ticket.md" not in decision_register:
        failures.append("post-RC decision register is missing ticket doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "ticket_doc": DOC_REL,
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "mission_control_execution_allowed": False,
        "mission_control_policy_authority_allowed": False,
        "mission_control_approval_authority_allowed": False,
        "mission_control_audit_authority_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "new_power_classes_allowed": False,
        "mission_control_implementation_ticket_ready": True,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control integration implementation ticket check",
        f"valid: {str(report['valid']).lower()}",
        f"ticket_doc: {report['ticket_doc']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        "mission_control_execution_allowed: "
        f"{str(report['mission_control_execution_allowed']).lower()}",
        "mission_control_policy_authority_allowed: "
        f"{str(report['mission_control_policy_authority_allowed']).lower()}",
        "mission_control_approval_authority_allowed: "
        f"{str(report['mission_control_approval_authority_allowed']).lower()}",
        "mission_control_audit_authority_allowed: "
        f"{str(report['mission_control_audit_authority_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "mission_control_implementation_ticket_ready: "
        f"{str(report['mission_control_implementation_ticket_ready']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

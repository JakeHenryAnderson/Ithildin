"""Validate the enterprise reviewer-response command matrix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_current_checkpoint,
    enterprise_response_inbox,
    enterprise_response_status_board,
    enterprise_transition_map,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-response-command-matrix.md"
DOC_TITLE = "Enterprise Response Command Matrix"
INBOX_DIR = "var/review-runs/enterprise-response-inbox"

ALLOWED_NEXT_STATES = {
    "ERG-003": "closed_local_preview_static_preflight",
    "ERG-002": "ready_for_design_only_decision_record",
    "ERG-005": "ready_for_design_only_decision_record",
    "ERG-006-ERG-007": "architecture_continuation_only",
    "ERG-008": "architecture_continuation_only",
    "ERG-009": "architecture_continuation_only",
    "ERG-004": "ready_for_decision_record",
    "ERG-010": "positioning_decision_record_only",
}

STILL_BLOCKED = {
    "ERG-003": (
        "live VM/container inspection, lifecycle management, local model invocation, "
        "sandbox orchestration"
    ),
    "ERG-002": (
        "Mission Control runtime importer behavior, execution authority, polling or "
        "mutating APIs"
    ),
    "ERG-005": "direct host writes, overwrite/delete/move behavior, automatic promotion",
    "ERG-006-ERG-007": (
        "production identity, enterprise RBAC, runtime Postgres, migrations, retention "
        "enforcement"
    ),
    "ERG-008": (
        "SIEM adapter runtime behavior, hosted telemetry, remote delivery, custody-grade "
        "audit claims"
    ),
    "ERG-009": (
        "compliance automation, legal conclusions, certification claims, regulated-industry "
        "compliance claims"
    ),
    "ERG-004": (
        "live implementation until ERG-003 and an ERG-004 decision record explicitly approve it"
    ),
    "ERG-010": (
        "public/security-product positioning unless a later decision explicitly narrows and "
        "approves claims"
    ),
}

REQUIRED_DOC_PHRASES = [
    "Status: checked command matrix for applying enterprise external-review responses.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "make enterprise-response-command-matrix",
    "This matrix does not normalize responses",
    "does not write normalized response files",
    "does not mutate findings",
    "does not record external review",
    "does not close any enterprise lane",
    "Use the generated inbox for exact reviewed-packet hashes",
    "For the current `ERG-003`/`ERG-002` receive path, prefer the generated dual-response inbox",
    "make enterprise-response-waiting-room",
    "make enterprise-response-paste-preflight",
    "var/review-runs/enterprise-dual-response-inbox/ENTERPRISE_DUAL_RESPONSE_CHEATSHEET.md",
    "`ERG-003`",
    "`ERG-010`",
    "runtime_changes_allowed: `false`",
    "new_power_classes_allowed: `false`",
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

    checkpoint = enterprise_current_checkpoint.build_report(repo_root)
    transition = enterprise_transition_map.build_report(repo_root)
    status_board = enterprise_response_status_board.build_report(repo_root)
    try:
        lanes = enterprise_response_inbox._lanes(repo_root)  # noqa: SLF001
    except enterprise_response_inbox.EnterpriseResponseInboxError as exc:
        lanes = []
        failures.append(f"enterprise response inbox lane inventory failed: {exc}")

    for label, report in [
        ("enterprise-current-checkpoint", checkpoint),
        ("enterprise-transition-map", transition),
        ("enterprise-response-status-board", status_board),
    ]:
        if report.get("valid") is not True:
            failures.append(f"{label} is not valid")
            failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    rows = [_row(lane) for lane in lanes]

    if checkpoint.get("tool_count") != 24:
        failures.append("enterprise checkpoint tool count is not 24")
    if checkpoint.get("selected_capability") != "not selected":
        failures.append("selected capability must remain not selected")
    if status_board.get("response_present_count") != 0:
        failures.append("enterprise responses are present; use lane-specific response handling")
    if status_board.get("closure_ready_count") != 0:
        failures.append("enterprise closure-ready lanes exist; use lane-specific closure flow")
    if len(rows) != 8:
        failures.append("enterprise response command matrix must cover 8 lanes")
    if [row["gap"] for row in rows[:2]] != ["ERG-003", "ERG-002"]:
        failures.append("enterprise response command matrix must keep ERG-003 then ERG-002 first")
    for row in rows:
        if row["allowed_next_state"] != ALLOWED_NEXT_STATES[row["gap"]]:
            failures.append(f"{row['gap']} allowed next state drifted")
        if not row["raw_response_path"].startswith(INBOX_DIR):
            failures.append(f"{row['gap']} raw response path must live under {INBOX_DIR}")
        if "external_response_normalize.py" not in row["normalizer_command"]:
            failures.append(f"{row['gap']} normalizer command is missing")
        if row["closure_gate"] == "none":
            failures.append(f"{row['gap']} closure gate is missing")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    response_inbox_doc = _read(repo_root / "docs/codex/enterprise-response-inbox.md")
    response_protocol_doc = _read(
        repo_root / "docs/codex/enterprise-response-application-protocol.md"
    )
    transition_doc = _read(repo_root / "docs/codex/enterprise-transition-map.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    if not doc:
        failures.append("enterprise response command matrix doc is missing")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            failures.append(f"enterprise response command matrix doc is missing phrase: {phrase}")
    for row in rows:
        for value in [
            row["gap"],
            row["raw_response_path"],
            "uv run python scripts/external_response_normalize.py",
            f"--area {row['normalization_area']}",
            '--reviewed-packet-hash "sha256:<from generated inbox>"',
            row["normalized_response_path"],
            row["closure_gate"],
            row["response_kit"],
            row["allowed_next_state"],
            row["still_blocked"],
        ]:
            if value not in doc:
                failures.append(
                    f"enterprise response command matrix doc is missing row value: {value}"
                )
        if row["dry_run_command"] != "none" and row["dry_run_command"] not in doc:
            failures.append(
                f"enterprise response command matrix doc is missing dry run: {row['gap']}"
            )

    if "enterprise-response-command-matrix:" not in makefile:
        failures.append("Make target is missing: enterprise-response-command-matrix")
    if (
        "enterprise-response-command-matrix" not in release_check_body
        and "release-check: enterprise-response-command-matrix" not in makefile
    ):
        failures.append("enterprise-response-command-matrix is missing from release-check")
    if "$(MAKE) enterprise-response-command-matrix" not in review_candidate_body:
        failures.append("enterprise-response-command-matrix is missing from review-candidate")
    if "make enterprise-response-command-matrix" not in readme:
        failures.append("README is missing enterprise response command matrix command")
    if DOC_REL not in readme:
        failures.append("README is missing enterprise response command matrix doc")
    if DOC_REL not in docs_site:
        failures.append("enterprise response command matrix is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise response command matrix is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise response command matrix")
    if "enterprise-response-command-matrix" not in release_guardrails:
        failures.append("release guardrails do not require enterprise response command matrix")
    for label, content in [
        ("response inbox", response_inbox_doc),
        ("response application protocol", response_protocol_doc),
        ("transition map", transition_doc),
    ]:
        if "enterprise-response-command-matrix" not in content:
            failures.append(f"{label} does not mention enterprise response command matrix")

    boundary_flags = {
        "normalizes_responses": False,
        "writes_response_files": False,
        "committed_findings_mutated": False,
        "external_review_recorded": False,
        "closes_enterprise_lanes": False,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_runtime_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "matrix_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": checkpoint.get("selected_capability"),
        "lane_count": len(rows),
        "response_present_count": status_board.get("response_present_count"),
        "closure_ready_count": status_board.get("closure_ready_count"),
        "command_rows": rows,
        **boundary_flags,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise response command matrix",
        f"valid: {str(report['valid']).lower()}",
        f"matrix_doc: {report['matrix_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report.get('selected_capability', 'unknown')}",
        f"lane_count: {report['lane_count']}",
        f"response_present_count: {report.get('response_present_count', 'unknown')}",
        f"closure_ready_count: {report.get('closure_ready_count', 'unknown')}",
        f"normalizes_responses: {str(report['normalizes_responses']).lower()}",
        f"writes_response_files: {str(report['writes_response_files']).lower()}",
        f"committed_findings_mutated: {str(report['committed_findings_mutated']).lower()}",
        f"external_review_recorded: {str(report['external_review_recorded']).lower()}",
        f"closes_enterprise_lanes: {str(report['closes_enterprise_lanes']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "lanes:",
    ]
    for row in report["command_rows"]:
        lines.append(
            "- {gap}: raw={raw} normalize_area={area} closure={closure} next={next_state}".format(
                gap=row["gap"],
                raw=row["raw_response_path"],
                area=row["normalization_area"],
                closure=row["closure_gate"],
                next_state=row["allowed_next_state"],
            )
        )
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _row(lane: dict[str, Any]) -> dict[str, str]:
    gap = str(lane["gap"])
    raw_response_path = f"{INBOX_DIR}/{lane['raw_response_file']}"
    normalizer = (
        "uv run python scripts/external_response_normalize.py "
        f"{raw_response_path} "
        '--reviewer "REVIEWER NAME" '
        '--reviewer-type "ai_external" '
        f"--source-access {lane['source_access']} "
        '--reviewed-commit "$(git rev-parse HEAD)" '
        f"--reviewed-packet-hash \"{lane['reviewed_packet_hash']}\" "
        f"--area {lane['normalization_area']} "
        f"--output {lane['normalized_response_path']}"
    )
    return {
        "gap": gap,
        "name": str(lane["name"]),
        "normalization_area": str(lane["normalization_area"]),
        "finding_namespace": str(lane["finding_namespace"]),
        "raw_response_path": raw_response_path,
        "normalizer_command": normalizer,
        "normalized_response_path": str(lane["normalized_response_path"]),
        "dry_run_command": str(lane["dry_run"] or "none"),
        "closure_gate": str(lane["closure_gate"]),
        "response_kit": str(lane["response_kit"]),
        "allowed_next_state": ALLOWED_NEXT_STATES[gap],
        "still_blocked": STILL_BLOCKED[gap],
    }


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())

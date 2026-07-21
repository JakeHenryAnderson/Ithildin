"""Validate the technical MVP execution board and batch-validation strategy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, status_now  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TECHNICAL_DOC = "docs/codex/technical-mvp-execution-board.md"
ENTERPRISE_DOC = "docs/codex/enterprise-roadmap-control-board.md"
BATCH_DOC = "docs/codex/batch-validation-strategy.md"
SEND_MANIFEST_JSON = Path(
    "var/review-packets/v3/enterprise-review-send-manifest/"
    "enterprise-review-send-manifest.json"
)
POST_DISPOSITION_ACTION = "prepare_pis_003_entry_decision_record"

REQUIRED_DOCS = [TECHNICAL_DOC, ENTERPRISE_DOC, BATCH_DOC]
TECHNICAL_IDS = [f"MVP-{index:03d}" for index in range(1, 11)]
ENTERPRISE_IDS = [f"ENT-{index:03d}" for index in range(1, 13)]
REQUIRED_COMMANDS = [
    "make validation-decision-run",
    "make status-now",
    "make enterprise-status-slice",
    "make handoff-dry-run",
    "make release-check",
    "make review-candidate",
    "make artifact-freshness-check",
    "make production-identity-storage-external-review-bundle-check",
    "make enterprise-response-waiting-room",
]
REQUIRED_PHRASES = {
    TECHNICAL_DOC: [
        "Status: checked technical-MVP execution board and batch-control map.",
        "Current governed tool count: `24`",
        "Current selected capability: `not selected`",
        "Latest implemented tool: `sandbox.artifact.write_text`",
        "Technical MVP state: `operator_trial_observed`",
        "Current enterprise next action: "
        "`prepare_pis_003_entry_decision_record`",
        "Active resume checkpoint: `ENT-001`",
        "The paused umbrella goal resumes through preparation of the separate `PIS-003` "
        "entry decision",
        "Development Validation Ladder",
        "Stop Conditions",
        "no sandbox orchestration",
        "no Mission Control execution",
    ],
    ENTERPRISE_DOC: [
        "Status: checked enterprise roadmap control board for the v1.0 enterprise-grade target.",
        "Current governed tool count: `24`",
        "Current selected capability: `not selected`",
        "Current send set: `ERG-006`, `ERG-007`",
        "Current response count: `0`",
        "Current closure-ready count: `0`",
        "Active resume checkpoint: `ENT-001`",
        "The current resumed goal is limited to post-`ENT-001` PIS-003 entry-decision record "
        "preparation",
        "Enterprise Target Definition",
        "Non-Negotiable Gates",
        "No new governed power class",
    ],
    BATCH_DOC: [
        "Status: checked batch validation strategy for controlled, lane-bounded development.",
        "Tier 1: inner loop",
        "Tier 2: batch checkpoint",
        "Tier 3: handoff freeze",
        "Safe Batch Shapes",
        "Unsafe Batch Shapes",
        "Batch Done Criteria",
        "Recommended Current Batches",
    ],
}
FORBIDDEN_PHRASES = [
    "production-ready",
    "compliance-grade",
    "tamper-proof",
    "secure sandbox",
    "Mission Control may execute",
    "sandbox orchestration allowed",
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
    docs = {doc: _read(repo_root / doc) for doc in REQUIRED_DOCS}
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    status = status_now.build_report(repo_root)
    current_send_set = status.get("recommended_send_set") or _current_send_set(repo_root)

    if status.get("valid") is not True:
        failures.append("status-now is not valid")
        failures.extend(f"status-now: {failure}" for failure in status.get("failures", []))

    for doc, text in docs.items():
        if not text:
            failures.append(f"roadmap doc is missing: {doc}")
            continue
        normalized = " ".join(text.split())
        lowered = normalized.lower()
        for phrase in REQUIRED_PHRASES[doc]:
            if " ".join(phrase.split()) not in normalized:
                failures.append(f"{doc} is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"{doc} contains forbidden phrase: {phrase}")

    for milestone_id in TECHNICAL_IDS:
        if milestone_id not in docs[TECHNICAL_DOC]:
            failures.append(f"technical execution board missing milestone: {milestone_id}")
    for milestone_id in ENTERPRISE_IDS:
        if milestone_id not in docs[ENTERPRISE_DOC]:
            failures.append(f"enterprise roadmap board missing milestone: {milestone_id}")
    for command in REQUIRED_COMMANDS:
        if not any(command in text for text in docs.values()):
            failures.append(f"roadmap docs missing command: {command}")

    if status.get("tool_count") != 24:
        failures.append("status-now tool_count is not 24")
    if status.get("latest_implemented_tool") != "sandbox.artifact.write_text":
        failures.append("latest implemented tool drifted")
    if status.get("selected_capability") != "not selected":
        failures.append("selected capability is not blocked")
    if status.get("technical_mvp_state") != "operator_trial_observed":
        failures.append("technical MVP state is not operator_trial_observed")
    if status.get("enterprise_next_action") != POST_DISPOSITION_ACTION:
        failures.append(
            "enterprise next action is not bounded PIS-001 planning"
        )
    if status.get("response_present_count") != 0:
        failures.append("response evidence is present; response intake flow should take over")
    if status.get("closure_ready_count") != 0:
        failures.append("closure-ready lanes are present; closure flow should take over")
    if current_send_set != ["ERG-006", "ERG-007"]:
        failures.append("current send set is not ERG-006/ERG-007")

    if "technical-mvp-execution-board:" not in makefile:
        failures.append("Make target is missing: technical-mvp-execution-board")
    if "roadmap-status:" not in makefile:
        failures.append("Make target is missing: roadmap-status")
    if (
        "technical-mvp-execution-board" not in release_check_body
        and "release-check: technical-mvp-execution-board" not in makefile
    ):
        failures.append("technical-mvp-execution-board is missing from release-check")
    if "make technical-mvp-execution-board" not in readme:
        failures.append("README is missing technical-mvp-execution-board command")
    if "make roadmap-status" not in readme:
        failures.append("README is missing roadmap-status command")
    for doc in REQUIRED_DOCS:
        if doc not in readme:
            failures.append(f"README is missing {doc}")
        if doc not in docs_site:
            failures.append(f"docs-site inputs missing {doc}")
        if doc not in review_docs.REVIEW_DOCS:
            failures.append(f"review docs missing {doc}")
    for title in [
        "Ithildin Technical MVP Execution Board",
        "Ithildin Enterprise Roadmap Control Board",
        "Ithildin Batch Validation Strategy",
    ]:
        if title not in review_index:
            failures.append(f"review-docs index missing title: {title}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "technical_doc": TECHNICAL_DOC,
        "enterprise_doc": ENTERPRISE_DOC,
        "batch_strategy_doc": BATCH_DOC,
        "tool_count": status.get("tool_count"),
        "latest_implemented_tool": status.get("latest_implemented_tool"),
        "selected_capability": status.get("selected_capability"),
        "technical_mvp_state": status.get("technical_mvp_state"),
        "enterprise_next_action": status.get("enterprise_next_action"),
        "active_resume_checkpoint": "ENT-001",
        "response_present_count": status.get("response_present_count"),
        "closure_ready_count": status.get("closure_ready_count"),
        "technical_milestone_count": len(TECHNICAL_IDS),
        "enterprise_milestone_count": len(ENTERPRISE_IDS),
        "current_send_set": current_send_set,
        "runtime_changes_allowed": False,
        "capability_expansion_allowed": False,
        "mission_control_runtime_allowed": False,
        "sandbox_orchestration_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin technical MVP execution board",
        f"valid: {str(report['valid']).lower()}",
        f"technical_doc: {report['technical_doc']}",
        f"enterprise_doc: {report['enterprise_doc']}",
        f"batch_strategy_doc: {report['batch_strategy_doc']}",
        f"tool_count: {report['tool_count']}",
        f"latest_implemented_tool: {report['latest_implemented_tool']}",
        f"selected_capability: {report['selected_capability']}",
        f"technical_mvp_state: {report['technical_mvp_state']}",
        f"enterprise_next_action: {report['enterprise_next_action']}",
        f"active_resume_checkpoint: {report['active_resume_checkpoint']}",
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        f"technical_milestone_count: {report['technical_milestone_count']}",
        f"enterprise_milestone_count: {report['enterprise_milestone_count']}",
        "current_send_set: " + ", ".join(report.get("current_send_set") or []),
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "capability_expansion_allowed: "
        f"{str(report['capability_expansion_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _current_send_set(repo_root: Path) -> list[str]:
    path = repo_root / SEND_MANIFEST_JSON
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data.get("recommended_gaps")
    return value if isinstance(value, list) and all(isinstance(item, str) for item in value) else []


if __name__ == "__main__":
    raise SystemExit(main())

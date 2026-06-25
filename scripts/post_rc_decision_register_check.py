"""Validate the post-RC decision register and release wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    post_rc_decision_gate,
    post_rc_decision_record_examples_check,
    post_rc_decision_record_template_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/post-rc-decision-register.md"

REQUIRED_PHRASES = [
    "Status: current register for post-v1.0 RC boundary decisions.",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "approved_for_planning",
    "no_go",
    "Runtime allowed",
    "PRD-MC-DISPLAY-001",
    "Mission Control display importer continuation",
    "Prepare display-only schema, packet, static fixtures, and source-review handoff",
    "runtime behavior remains blocked",
    "PRD-SANDBOX-PREFLIGHT-001",
    "Live sandbox/VM preflight",
    "Continue static fixture evidence and source-review disposition only",
    "live runtime behavior remains blocked",
    "PRD-SANDBOX-LIVE-POC-001",
    "Live sandbox/VM worker proof of concept",
    "Maintain the decision-intake packet and wait for favorable `ERG-003` disposition",
    "live worker runtime behavior remains blocked",
    "PRD-CAPABILITY-001",
    "New governed tool after RC freeze",
    "Candidate selection and design packet only",
    "no new governed tool is approved by this register",
    "PRD-TRUSTED-HOST-001",
    "Trusted-host promotion lane",
    "Promotion state-machine design and evidence contract discussion only",
    "trusted-host promotion remains blocked",
    "PRD-SIEM-EXPORT-001",
    "SIEM-shaped export adapter lane",
    "Stable schema and offline export design only",
    "SIEM adapter work remains blocked",
    "make post-rc-decision-register-check",
    "make post-rc-decision-record-examples-check",
    "make post-rc-decision-gate",
]

FORBIDDEN_PHRASES = [
    "capability expansion allowed now",
    "Mission Control may execute",
    "trusted-host promotion is implemented",
    "compliance automation approved",
    "public security product approved",
    "sandbox orchestration is implemented",
    "local model invocation is implemented",
    "SIEM adapter is implemented",
]

DECISION_IDS = [
    "PRD-MC-DISPLAY-001",
    "PRD-SANDBOX-PREFLIGHT-001",
    "PRD-SANDBOX-LIVE-POC-001",
    "PRD-CAPABILITY-001",
    "PRD-TRUSTED-HOST-001",
    "PRD-SIEM-EXPORT-001",
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
    doc_rel = DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    gate_report = post_rc_decision_gate.build_report(repo_root)
    template_report = post_rc_decision_record_template_check.build_report(repo_root)
    examples_report = post_rc_decision_record_examples_check.build_report(repo_root)

    text = ""
    if not doc_path.exists():
        failures.append("post-RC decision register doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        normalized_text = " ".join(text.split())
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized_text:
                failures.append(f"post-RC decision register is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"post-RC decision register contains forbidden phrase: {phrase}")
        for decision_id in DECISION_IDS:
            if text.count(decision_id) < 2:
                failures.append(f"post-RC decision register is missing detail for: {decision_id}")

    failures.extend(f"post-RC decision gate: {failure}" for failure in gate_report["failures"])
    failures.extend(
        f"post-RC decision record template: {failure}"
        for failure in template_report["failures"]
    )
    failures.extend(
        f"post-RC decision record examples: {failure}"
        for failure in examples_report["failures"]
    )

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("post-RC decision register is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("post-RC decision register is missing from docs-site inputs")
    if "post-rc-decision-register-check:" not in makefile:
        failures.append("Make target is missing: post-rc-decision-register-check")
    if "post-rc-decision-register-check" not in release_check_body:
        failures.append("post-rc-decision-register-check is missing from release-check")
    if "make post-rc-decision-register-check" not in readme:
        failures.append("README is missing post-RC decision register command")
    if "post-RC decision register" not in readme:
        failures.append("README is missing post-RC decision register reference")
    if "Post-RC Decision Register" not in review_index:
        failures.append("review docs index is missing post-RC decision register")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_register_doc": doc_rel,
        "tool_count": 24,
        "registered_decision_count": len(DECISION_IDS),
        "mission_control_planning_allowed": True,
        "mission_control_runtime_allowed": False,
        "sandbox_live_preflight_allowed": False,
        "sandbox_live_worker_poc_allowed": False,
        "new_capability_runtime_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_claims_allowed": False,
        "runtime_changes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin post-RC decision register check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_register_doc: {report['decision_register_doc']}",
        f"tool_count: {report['tool_count']}",
        f"registered_decision_count: {report['registered_decision_count']}",
        "mission_control_planning_allowed: "
        f"{str(report['mission_control_planning_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"sandbox_live_preflight_allowed: {str(report['sandbox_live_preflight_allowed']).lower()}",
        "sandbox_live_worker_poc_allowed: "
        f"{str(report['sandbox_live_worker_poc_allowed']).lower()}",
        f"new_capability_runtime_allowed: {str(report['new_capability_runtime_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

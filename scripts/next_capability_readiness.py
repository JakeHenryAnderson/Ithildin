"""Validate readiness gates before selecting or implementing another capability."""

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
    read_only_capability_inventory_gate,
    read_only_metadata_capability_check,
    review_docs,
    v3_next_capability_candidate_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs/codex/next-capability-readiness.md"
REQUIRED_DOC_PHRASES = [
    "Status: capability-expansion readiness checkpoint",
    "does not add runtime behavior",
    "git.show.commit_metadata",
    "git.show.ref_summary",
    "git.show.tag_metadata",
    "project.dependency.summary",
    "project.manifest.summary",
    "project.structure.summary",
    "project.test.summary",
    "project.docs.summary",
    "project.language.summary",
    "project.config.summary",
    "project.ci.summary",
    "project.release.summary",
    "Current tool count: `22`",
    "Selected candidate: `project.risk.summary`",
    "Selected candidate status: design-only selected; implementation blocked",
    "Selected candidate proposal: complete for `project.risk.summary`",
    "Selected candidate implementation plan: complete for `project.risk.summary`",
    "Most recent implemented candidate: `project.release.summary`",
    "Most recent implementation: approved bounded read-only runtime implementation complete",
    "Fixture/test contract: retained for `project.release.summary`",
    "Implementation transition checklist: completed for `project.release.summary`",
    "Source-review handoff: recorded for `project.release.summary`",
    "Source-review bundle: recorded for `project.release.summary`",
    "Broader capability expansion: blocked",
    "New powerful tool classes: blocked",
    "Required Preflight Before Another Capability",
    "design-only candidate evaluation",
    "complete capability proposal",
    "implementation-planning packet",
    "explicit implementation decision",
    "focused source-review handoff bundle",
    "preimplementation fixture/test contract and check",
    "policy fixtures and parity evidence",
    "negative transcript coverage",
    "no-new-powers evidence",
    "make next-capability-readiness",
    "make project-risk-summary-proposal-check",
    "make project-risk-summary-implementation-plan-check",
    "make project-risk-summary-design-review-packet",
    "make project-release-summary-proposal-check",
    "make project-release-summary-implementation-plan-check",
    "make project-release-summary-implementation-gate",
    "make project-release-summary-transition-check",
    "make project-release-summary-review-handoff-check",
    "make project-release-summary-design-review-packet",
    "make project-release-summary-source-review-bundle",
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
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    metadata = read_only_metadata_capability_check.build_report(repo_root)
    inventory = read_only_capability_inventory_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    historical_candidate = v3_next_capability_candidate_check.build_report(repo_root)
    failures.extend(f"metadata-capability-check: {failure}" for failure in metadata["failures"])
    failures.extend(f"inventory: {failure}" for failure in inventory["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(
        f"historical-candidate: {failure}" for failure in historical_candidate["failures"]
    )

    doc_rel = DOC_PATH.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    if not doc_path.exists():
        failures.append("next capability readiness doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in text:
                failures.append(f"next capability readiness doc is missing phrase: {phrase}")
    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("next capability readiness doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("next capability readiness doc is missing from docs-site inputs")
    if "next-capability-readiness:" not in makefile:
        failures.append("Make target is missing: next-capability-readiness")
    if "next-capability-readiness" not in release_check_body:
        failures.append("next-capability-readiness is missing from release-check")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "current_approved_read_only_capabilities": inventory.get("capability_count"),
        "tool_count": inventory.get("tool_count"),
        "next_candidate": "project.risk.summary",
        "next_candidate_status": "design_only_selected",
        "next_candidate_proposal_complete": True,
        "next_candidate_plan_complete": True,
        "next_candidate_implementation_allowed": False,
        "broader_capability_expansion_allowed": False,
        "new_power_classes_allowed": False,
        "historical_candidate": historical_candidate.get("candidate"),
        "historical_candidate_status": "implemented_after_reviewed_lanes",
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin next capability readiness check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        f"next_candidate: {report['next_candidate']}",
        f"next_candidate_status: {report.get('next_candidate_status', 'unknown')}",
        "next_candidate_proposal_complete: "
        f"{str(report.get('next_candidate_proposal_complete', False)).lower()}",
        "next_candidate_plan_complete: "
        f"{str(report.get('next_candidate_plan_complete', False)).lower()}",
        "next_candidate_implementation_allowed: false",
        "broader_capability_expansion_allowed: false",
        "new_power_classes_allowed: false",
        f"historical_candidate: {report.get('historical_candidate', 'unknown')}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

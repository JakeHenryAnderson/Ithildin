"""Generate the v0.5 capability decision posture report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    accepted_risk_register,
    capability_expansion_gate,
    external_review_closure_gate,
    review_findings_collect,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]


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
    capability = capability_expansion_gate.build_report(repo_root)
    closure = external_review_closure_gate.build_report(repo_root)
    accepted_risks = accepted_risk_register.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    findings = review_findings_collect.collect_findings_summary(
        repo_root / "docs/codex/findings",
        repo_root,
    )
    manifest = json.loads(
        (repo_root / "docs/codex/v0.5-milestone-manifest.json").read_text(
            encoding="utf-8"
        )
    )

    hard_failures: list[str] = []
    hard_failures.extend(capability["hard_failures"])
    hard_failures.extend(closure["hard_failures"])
    hard_failures.extend(accepted_risks["failures"])
    hard_failures.extend(tool_surface["failures"])

    planned_range = str(manifest.get("planned_range", ""))
    blockers: list[str] = []
    if not capability["capability_expansion_allowed"]:
        blockers.extend(capability["blockers"])
    if not closure["external_closure_complete"]:
        blockers.extend(closure["blockers"])
    if accepted_risks["open_external_review_ids"]:
        blockers.append(
            "accepted risks remain external-review-pending: "
            f"{len(accepted_risks['open_external_review_ids'])}"
        )
    if planned_range not in {"", "none"}:
        blockers.append(f"v0.5 planned tasks remain: {planned_range}")

    decision = "blocked"
    if not blockers and not hard_failures:
        decision = "candidate_allowed_after_external_review"

    return {
        "schema_version": "1",
        "valid": not hard_failures,
        "decision": decision,
        "capability_expansion_allowed": False,
        "runtime_boundary": manifest["runtime_boundary"],
        "completed_range": manifest["completed_range"],
        "planned_range": planned_range,
        "tool_count": tool_surface["tool_count"],
        "accepted_risk_count": accepted_risks["risk_count"],
        "open_accepted_risks": len(accepted_risks["open_external_review_ids"]),
        "accepted_deferred_risks": len(accepted_risks["accepted_deferred_ids"]),
        "accepted_risks_blocking_public_preview": len(
            accepted_risks["blocks_public_preview_ids"]
        ),
        "accepted_risks_blocking_capability_design": len(
            accepted_risks["blocks_capability_design_ids"]
        ),
        "finding_count": findings["total"],
        "open_critical_high_findings": findings["open_critical_high"],
        "external_closure_complete": closure["external_closure_complete"],
        "hard_failures": hard_failures,
        "blockers": sorted(set(blockers)),
        "recommended_next_step": _recommended_next_step(blockers, planned_range),
    }


def _recommended_next_step(blockers: list[str], planned_range: str) -> str:
    if planned_range not in {"", "none"}:
        return "continue v0.5 review-closure tasks before requesting capability expansion"
    if blockers:
        return (
            "continue source-review closure and keep further capability implementation blocked "
            "unless a separate explicit implementation decision is recorded"
        )
    return "prepare a separate explicit capability-decision proposal"


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin capability decision report",
        f"decision: {report['decision']}",
        "capability_expansion_allowed: false",
        f"runtime_boundary: {report['runtime_boundary']}",
        f"completed_range: {report['completed_range']}",
        f"planned_range: {report['planned_range']}",
        f"tool_count: {report['tool_count']}",
        f"accepted_risk_count: {report['accepted_risk_count']}",
        f"open_accepted_risks: {report['open_accepted_risks']}",
        f"accepted_deferred_risks: {report['accepted_deferred_risks']}",
        "accepted_risks_blocking_public_preview: "
        f"{report['accepted_risks_blocking_public_preview']}",
        "accepted_risks_blocking_capability_design: "
        f"{report['accepted_risks_blocking_capability_design']}",
        f"finding_count: {report['finding_count']}",
        f"open_critical_high_findings: {report['open_critical_high_findings']}",
        f"external_closure_complete: {str(report['external_closure_complete']).lower()}",
        f"recommended_next_step: {report['recommended_next_step']}",
    ]
    if report["blockers"]:
        lines.append("blockers:")
        lines.extend(f"- {blocker}" for blocker in report["blockers"])
    if report["hard_failures"]:
        lines.append("hard_failures:")
        lines.extend(f"- {failure}" for failure in report["hard_failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

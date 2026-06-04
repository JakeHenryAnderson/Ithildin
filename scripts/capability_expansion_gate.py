"""Report whether Ithildin is allowed to plan a new powerful tool capability."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import reviewer_findings

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOL_NAMES = [
    "fs.list",
    "fs.patch.apply",
    "fs.patch.propose",
    "fs.read",
    "fs.search",
    "fs.stat",
    "git.diff",
    "git.log",
    "git.show.commit_metadata",
    "git.status",
    "http.fetch",
]
EXPECTED_DEFERRED_BOUNDARIES = [
    "shell execution",
    "Docker socket access",
    "Kubernetes tools",
    "browser automation",
    "arbitrary HTTP methods, caller-supplied headers, request bodies, cookies, "
    "or broad network access",
    "broad filesystem writes, deletes, moves, chmod, archive extraction, or secrets-manager tools",
    "plugin SDK or marketplace",
    "remote hosted MCP gateway",
    "production identity integrations",
    "runtime Postgres",
    "hosted telemetry collectors",
    "managed model serving or LLM proxy workflows",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--require-allowed",
        action="store_true",
        help="exit nonzero unless capability expansion is currently allowed",
    )
    args = parser.parse_args()

    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))

    if report["hard_failures"]:
        return 1
    if args.require_allowed and not report["capability_expansion_allowed"]:
        return 1
    return 0


def build_report(repo_root: Path) -> dict[str, Any]:
    tool_names = _tool_names(repo_root)
    v05_manifest = json.loads(
        (repo_root / "docs/codex/v0.5-milestone-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    closure_matrix = (
        repo_root / "docs/codex/source-review-closure-matrix.md"
    ).read_text(encoding="utf-8")
    finding_records = reviewer_findings.validate_findings(
        findings_dir=repo_root / "docs/codex/findings",
        repo_root=repo_root,
    )

    hard_failures: list[str] = []
    blockers: list[str] = []

    if tool_names != EXPECTED_TOOL_NAMES:
        hard_failures.append("tool list changed without a capability boundary decision")
    if v05_manifest.get("deferred_boundaries") != EXPECTED_DEFERRED_BOUNDARIES:
        hard_failures.append("deferred boundary list changed")
    if v05_manifest.get("runtime_boundary") != "v0.1 local-preview":
        hard_failures.append("runtime boundary changed")

    if "external_pending" in closure_matrix:
        blockers.append("source-review closure matrix still has external_pending rows")
    if v05_manifest.get("planned_range") not in {"none", ""}:
        blockers.append(f"v0.5 planned tasks remain: {v05_manifest.get('planned_range')}")

    return {
        "schema_version": "1",
        "capability_expansion_allowed": not hard_failures and not blockers,
        "hard_failures": hard_failures,
        "blockers": blockers,
        "tool_count": len(tool_names),
        "tool_names": tool_names,
        "finding_count": len(finding_records),
        "runtime_boundary": v05_manifest.get("runtime_boundary"),
        "deferred_boundaries_unchanged": (
            v05_manifest.get("deferred_boundaries") == EXPECTED_DEFERRED_BOUNDARIES
        ),
        "decision": "blocked" if blockers or hard_failures else "allowed",
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin capability expansion gate",
        f"decision: {report['decision']}",
        f"capability_expansion_allowed: {str(report['capability_expansion_allowed']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"runtime_boundary: {report['runtime_boundary']}",
        f"deferred_boundaries_unchanged: {str(report['deferred_boundaries_unchanged']).lower()}",
    ]
    if report["hard_failures"]:
        lines.append("hard_failures:")
        lines.extend(f"- {failure}" for failure in report["hard_failures"])
    if report["blockers"]:
        lines.append("blockers:")
        lines.extend(f"- {blocker}" for blocker in report["blockers"])
    return "\n".join(lines)


def _tool_names(repo_root: Path) -> list[str]:
    lock = json.loads((repo_root / "tool-manifests.lock.json").read_text(encoding="utf-8"))
    return [record["name"] for record in lock["manifests"]]


if __name__ == "__main__":
    raise SystemExit(main())

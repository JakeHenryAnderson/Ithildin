"""Validate the bounded Track B Node manual-rollback decision packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = "track-b-node-manual-rollback-decision-check"
DOCS = (
    "docs/codex/track-b-node-manual-rollback-capability-decision.md",
    "docs/codex/track-b-node-manual-rollback-architecture.md",
    "docs/codex/track-b-node-manual-rollback-implementation-plan.md",
    "docs/codex/track-b-node-manual-rollback-observed-results.md",
)
REQUIRED_PHRASES = (
    "Current governed tool count: `24`.",
    "fresh signed generation",
    "expected_current_generation",
    "stored_not_enforced",
    "BEGIN IMMEDIATE",
    "does not rewrite or close",
    "automatic rollback",
    "group rollout",
    "runner enforcement",
)
FORBIDDEN_APPROVALS = (
    "automatic rollback is approved",
    "group rollout is approved",
    "runner enforcement is approved",
    "node self-update is approved",
    "production identity is approved",
)


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    texts: list[str] = []
    for relative in DOCS:
        path = repo_root / relative
        if not path.is_file():
            failures.append(f"missing Node rollback document: {relative}")
            texts.append("")
        else:
            texts.append(path.read_text(encoding="utf-8"))
    combined = "\n".join(texts)
    lowered = combined.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in combined:
            failures.append(f"Node rollback packet is missing required phrase: {phrase}")
    for phrase in FORBIDDEN_APPROVALS:
        if phrase in lowered:
            failures.append(f"Node rollback packet contains forbidden approval: {phrase}")

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("Node rollback decision check is missing from release-check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing the Node rollback decision check")
    for relative in DOCS:
        if relative not in readme:
            failures.append(f"README is missing: {relative}")
        if relative not in docs_site:
            failures.append(f"docs site is missing: {relative}")
        if relative not in review_docs:
            failures.append(f"review docs are missing: {relative}")
    if "Track B Node Manual Rollback" not in review_index:
        failures.append("review docs index is missing the manual-rollback section")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "documents": list(DOCS),
        "tool_count": 24,
        "manual_single_node_rollback_allowed": True,
        "old_signature_reactivation_allowed": False,
        "automatic_rollback_allowed": False,
        "group_rollout_allowed": False,
        "runner_enforcement_claim_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Track B Node manual-rollback decision check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        "manual_single_node_rollback_allowed: "
        f"{str(report['manual_single_node_rollback_allowed']).lower()}",
        "old_signature_reactivation_allowed: "
        f"{str(report['old_signature_reactivation_allowed']).lower()}",
        f"automatic_rollback_allowed: {str(report['automatic_rollback_allowed']).lower()}",
        f"group_rollout_allowed: {str(report['group_rollout_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(args.repo_root.resolve())
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

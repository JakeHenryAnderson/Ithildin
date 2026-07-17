"""Validate the bounded Node version-posture decision packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = "track-b-node-version-posture-decision-check"
DOCS = (
    "docs/codex/track-b-node-version-posture-capability-decision.md",
    "docs/codex/track-b-node-version-posture-architecture.md",
    "docs/codex/track-b-node-version-posture-implementation-plan.md",
)
REQUIRED_PHRASES = (
    "Current governed tool count: `24`.",
    "MAJOR.MINOR.PATCH",
    "last_node_version",
    "below_minimum",
    "operator-managed",
    "does not rewrite or close",
    "Node self-update",
    "runner lifecycle control",
    "new governed tool",
)
FORBIDDEN_APPROVALS = (
    "node self-update is approved",
    "package download is approved",
    "process restart is approved",
    "automatic rollback is approved",
    "fleet rollout is approved",
    "runner lifecycle control is approved",
)


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    texts: list[str] = []
    for relative in DOCS:
        path = repo_root / relative
        if not path.is_file():
            failures.append(f"missing version-posture document: {relative}")
            texts.append("")
        else:
            texts.append(path.read_text(encoding="utf-8"))
    combined = "\n".join(texts)
    lowered = combined.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in combined:
            failures.append(f"version-posture packet is missing required phrase: {phrase}")
    for phrase in FORBIDDEN_APPROVALS:
        if phrase in lowered:
            failures.append(f"version-posture packet contains forbidden approval: {phrase}")

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("version-posture decision check is missing from release-check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing the version-posture decision check")
    for relative in DOCS:
        if relative not in readme:
            failures.append(f"README is missing: {relative}")
        if relative not in docs_site:
            failures.append(f"docs site is missing: {relative}")
        if relative not in review_docs:
            failures.append(f"review docs are missing: {relative}")
    if "Track B Node Version Posture" not in review_index:
        failures.append("review docs index is missing the version-posture section")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "documents": list(DOCS),
        "tool_count": 24,
        "version_posture_allowed": True,
        "operator_managed_maintenance_observation_allowed": True,
        "node_self_update_allowed": False,
        "package_transfer_allowed": False,
        "runner_lifecycle_control_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Track B Node version-posture decision check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"version_posture_allowed: {str(report['version_posture_allowed']).lower()}",
        "operator_managed_maintenance_observation_allowed: "
        f"{str(report['operator_managed_maintenance_observation_allowed']).lower()}",
        f"node_self_update_allowed: {str(report['node_self_update_allowed']).lower()}",
        f"package_transfer_allowed: {str(report['package_transfer_allowed']).lower()}",
        "runner_lifecycle_control_allowed: "
        f"{str(report['runner_lifecycle_control_allowed']).lower()}",
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

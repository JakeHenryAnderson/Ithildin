"""Validate the bounded Track B Node governed-access decision packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = "track-b-node-governed-access-decision-check"
EVIDENCE_TARGET = "track-b-node-governed-access-evidence-check"
OBSERVED_RESULTS = "docs/codex/track-b-node-governed-access-observed-results.md"
DOCS = (
    "docs/codex/track-b-node-governed-access-capability-decision.md",
    "docs/codex/track-b-node-governed-access-architecture.md",
    "docs/codex/track-b-node-governed-access-implementation-plan.md",
)
REQUIRED_PHRASES = (
    "Current governed tool count: `24`.",
    "AgentReadOnly",
    "server-derived agent identity",
    "stored_not_enforced",
    "deny_governed_actions",
    "durable replay rejection",
    "Gateway is unavailable",
    "does not rewrite",
    "remote MCP",
    "no arbitrary host control",
)
FORBIDDEN_APPROVALS = (
    "node write authority is approved",
    "node network authority is approved",
    "offline execution is approved",
    "runner control is approved",
    "remote mcp is approved",
    "production identity is approved",
    "arbitrary host control is approved",
)


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    texts: list[str] = []
    for relative in DOCS:
        path = repo_root / relative
        if not path.is_file():
            failures.append(f"missing Node governed-access document: {relative}")
            texts.append("")
        else:
            texts.append(path.read_text(encoding="utf-8"))
    combined = "\n".join(texts)
    lowered = combined.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in combined:
            failures.append(f"Node governed-access packet is missing required phrase: {phrase}")
    for phrase in FORBIDDEN_APPROVALS:
        if phrase in lowered:
            failures.append(f"Node governed-access packet contains forbidden approval: {phrase}")

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("Node governed-access decision check is missing from release-check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing the Node governed-access decision check")
    if f"{EVIDENCE_TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {EVIDENCE_TARGET}")
    if f"make {EVIDENCE_TARGET}" not in readme:
        failures.append("README is missing the Node governed-access evidence check")
    for relative in DOCS:
        if relative not in readme:
            failures.append(f"README is missing: {relative}")
        if relative not in docs_site:
            failures.append(f"docs site is missing: {relative}")
        if relative not in review_docs:
            failures.append(f"review docs are missing: {relative}")
    if "Track B Node Governed Access" not in review_index:
        failures.append("review docs index is missing the governed-access section")
    for source, label in (
        (readme, "README"),
        (docs_site, "docs site"),
        (review_docs, "review docs"),
    ):
        if OBSERVED_RESULTS not in source:
            failures.append(f"{label} is missing: {OBSERVED_RESULTS}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "documents": list(DOCS),
        "tool_count": 24,
        "node_read_only_governed_access_allowed": True,
        "node_write_access_allowed": False,
        "node_network_access_allowed": False,
        "offline_execution_allowed": False,
        "runner_control_allowed": False,
        "remote_mcp_allowed": False,
        "historical_external_review_mutated": False,
        "observed_evidence_check_available": True,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Track B Node governed-access decision check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        "node_read_only_governed_access_allowed: "
        f"{str(report['node_read_only_governed_access_allowed']).lower()}",
        f"node_write_access_allowed: {str(report['node_write_access_allowed']).lower()}",
        f"node_network_access_allowed: {str(report['node_network_access_allowed']).lower()}",
        f"offline_execution_allowed: {str(report['offline_execution_allowed']).lower()}",
        f"runner_control_allowed: {str(report['runner_control_allowed']).lower()}",
        f"remote_mcp_allowed: {str(report['remote_mcp_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(args.repo_root.resolve())
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


if __name__ == "__main__":
    raise SystemExit(main())

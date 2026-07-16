"""Validate the bounded Track B Node signed-configuration decision packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = "track-b-node-configuration-decision-check"
DOCS = (
    "docs/codex/track-b-node-configuration-capability-decision.md",
    "docs/codex/track-b-node-configuration-architecture.md",
    "docs/codex/track-b-node-configuration-implementation-plan.md",
)
REQUIRED_PHRASES = (
    "Current governed tool count: `24`.",
    "dedicated Gateway Ed25519 keypair",
    "ITHILDIN-NODE-CONFIG-V1",
    "stored_not_enforced",
    "manifest-lock digest",
    "configuration_drift",
    "does not rewrite or close",
    "remote MCP",
    "runner health",
)
FORBIDDEN_APPROVALS = (
    "node tool execution is approved",
    "remote mcp is approved",
    "runner control is approved",
    "production identity is approved",
    "stored configuration proves enforcement",
    "automatic rollout is approved",
)


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    texts: list[str] = []
    for relative in DOCS:
        path = repo_root / relative
        if not path.is_file():
            failures.append(f"missing Node configuration document: {relative}")
            texts.append("")
        else:
            texts.append(path.read_text(encoding="utf-8"))
    combined = "\n".join(texts)
    lowered = combined.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in combined:
            failures.append(f"Node configuration packet is missing required phrase: {phrase}")
    for phrase in FORBIDDEN_APPROVALS:
        if phrase in lowered:
            failures.append(f"Node configuration packet contains forbidden approval: {phrase}")

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("Node configuration decision check is missing from release-check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing the Node configuration decision check")
    for relative in DOCS:
        if relative not in readme:
            failures.append(f"README is missing: {relative}")
        if relative not in docs_site:
            failures.append(f"docs site is missing: {relative}")
        if relative not in review_docs:
            failures.append(f"review docs are missing: {relative}")
    if "Track B Node Signed Configuration" not in review_index:
        failures.append("review docs index is missing the signed-configuration section")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "documents": list(DOCS),
        "tool_count": 24,
        "signed_configuration_distribution_allowed": True,
        "stored_configuration_enforcement_claim_allowed": False,
        "node_tool_execution_allowed": False,
        "remote_mcp_allowed": False,
        "production_identity_allowed": False,
        "historical_external_review_mutated": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Track B Node signed-configuration decision check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        "signed_configuration_distribution_allowed: "
        f"{str(report['signed_configuration_distribution_allowed']).lower()}",
        "stored_configuration_enforcement_claim_allowed: "
        f"{str(report['stored_configuration_enforcement_claim_allowed']).lower()}",
        f"node_tool_execution_allowed: {str(report['node_tool_execution_allowed']).lower()}",
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

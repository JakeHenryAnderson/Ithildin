"""Validate the limited Track B Ithildin Node decision packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = "track-b-node-decision-check"
DOCS = (
    "docs/codex/track-b-node-capability-decision.md",
    "docs/codex/track-b-node-architecture.md",
    "docs/codex/track-b-node-implementation-plan.md",
)
REQUIRED_PHRASES = (
    "Current governed tool count: `24`.",
    "approved for the limited local-preview enrollment and identity vertical slice",
    "does not rewrite or close",
    "server-derived",
    "Ed25519",
    "replay",
    "revocation",
    "synthetic",
    "Command Center",
    "remote MCP",
    "runner health",
)
FORBIDDEN_APPROVALS = (
    "remote mcp is approved",
    "shell execution is approved",
    "docker socket access is approved",
    "mission orchestration is approved",
    "production identity is approved",
    "filesystem non-bypass is proven",
    "runner lifecycle control is approved",
)


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    texts: list[str] = []
    for relative in DOCS:
        path = repo_root / relative
        if not path.is_file():
            failures.append(f"missing Track B Node document: {relative}")
            texts.append("")
        else:
            texts.append(path.read_text(encoding="utf-8"))
    combined = "\n".join(texts)
    lowered = combined.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in combined:
            failures.append(f"Track B Node packet is missing required phrase: {phrase}")
    for phrase in FORBIDDEN_APPROVALS:
        if phrase in lowered:
            failures.append(f"Track B Node packet contains forbidden approval claim: {phrase}")

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("Track B Node decision check is missing from release-check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing the Track B Node decision check")
    for relative in DOCS:
        if relative not in readme:
            failures.append(f"README is missing: {relative}")
        if relative not in docs_site:
            failures.append(f"docs site is missing: {relative}")
        if relative not in review_docs:
            failures.append(f"review docs are missing: {relative}")
    if "Track B Ithildin Node" not in review_index:
        failures.append("review docs index is missing the Track B Ithildin Node section")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "documents": list(DOCS),
        "tool_count": 24,
        "limited_enrollment_identity_slice_allowed": True,
        "node_tool_execution_allowed": False,
        "remote_mcp_allowed": False,
        "runner_lifecycle_allowed": False,
        "production_identity_allowed": False,
        "historical_external_review_mutated": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Track B Ithildin Node decision check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        "limited_enrollment_identity_slice_allowed: "
        f"{str(report['limited_enrollment_identity_slice_allowed']).lower()}",
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

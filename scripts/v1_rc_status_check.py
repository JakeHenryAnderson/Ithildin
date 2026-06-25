"""Validate the canonical v1.0 RC status document and wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
STATUS_DOC = ROOT / "docs/codex/v1.0-rc-status.md"

REQUIRED_PHRASES = [
    "Status: canonical local-preview release-candidate status.",
    "Current Truth Table",
    "Governed tool count | `24`",
    "Latest implemented tool | `project.risk.summary`",
    "Capability expansion | Blocked",
    "Public/security-product positioning | Blocked",
    "Implemented Local-Preview Surface",
    "Still Blocked Or Deferred",
    "v1.0 RC Exit Criteria",
    "`make release-check` passes from a clean tree",
    "`make review-candidate` passes",
    "`make v1-rc-status-check`",
    "tool count remains `24`",
    "public/security-product positioning remains blocked",
    "install, demo, workbench, evidence, and shutdown instructions",
]

DEFERRED_PHRASES = [
    "shell execution",
    "Docker socket access",
    "Kubernetes tools",
    "browser automation",
    "arbitrary HTTP",
    "broad filesystem writes",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "sandbox orchestration",
    "SIEM adapters",
    "compliance automation",
    "plugin SDK",
]

FORBIDDEN_PHRASES = [
    "production-ready",
    "compliance-grade audit",
    "tamper-proof audit",
    "secure sandbox",
    "safe arbitrary tool use",
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
    doc_rel = STATUS_DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)

    text = ""
    if not doc_path.exists():
        failures.append("v1.0 RC status doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 RC status doc is missing phrase: {phrase}")
        for phrase in DEFERRED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 RC status doc is missing deferred phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                failures.append(f"v1.0 RC status doc contains forbidden phrase: {phrase}")

    if tool_surface.get("tool_count") != 24:
        failures.append("tool surface tool count is not 24")
    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 RC status doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 RC status doc is missing from docs-site inputs")
    if "v1-rc-status-check:" not in makefile:
        failures.append("Make target is missing: v1-rc-status-check")
    if "v1-rc-status-check" not in release_check_body:
        failures.append("v1-rc-status-check is missing from release-check")
    if "v1.0 RC status" not in readme:
        failures.append("README is missing v1.0 RC status reference")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "status_doc": doc_rel,
        "tool_count": tool_surface.get("tool_count"),
        "latest_implemented_tool": "project.risk.summary",
        "selected_capability": "not selected",
        "capability_expansion_allowed": False,
        "public_security_product_positioning_allowed": False,
        "runtime_changes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 RC status check",
        f"valid: {str(report['valid']).lower()}",
        f"status_doc: {report['status_doc']}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        f"latest_implemented_tool: {report['latest_implemented_tool']}",
        f"selected_capability: {report['selected_capability']}",
        "capability_expansion_allowed: "
        f"{str(report['capability_expansion_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

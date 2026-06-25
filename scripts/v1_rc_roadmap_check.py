"""Validate the v1.0 RC roadmap and its release-readiness wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
ROADMAP_DOC = ROOT / "docs/codex/v1.0-rc-roadmap.md"

REQUIRED_PHRASES = [
    "Status: roadmap and sequencing target only.",
    "Ithildin v1.0 RC is a local-first governed MCP workbench",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "Most recent capability state: `sandbox.artifact.write_text` is implemented",
    "The most recent read-only metadata candidate remains",
    "Phase 1: Finish The Read-Only Metadata Surface",
    "Phase 2: Prove The Local Workbench Loop",
    "Phase 3: Polish The Operator Console",
    "Phase 4: Freeze Capability Expansion",
    "Phase 5: Final Assurance And Handoff",
    "one worker ticket at a time",
    "production identity",
    "runtime Postgres",
    "remote MCP hosting",
    "sandbox orchestration",
    "SIEM adapters or custody-grade audit",
    "compliance automation",
    "public/security-product positioning",
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
    doc_rel = ROADMAP_DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    text = ""
    if not doc_path.exists():
        failures.append("v1.0 RC roadmap doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 RC roadmap doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                failures.append(f"v1.0 RC roadmap doc contains forbidden phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 RC roadmap doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 RC roadmap doc is missing from docs-site inputs")
    if "v1-rc-roadmap-check:" not in makefile:
        failures.append("Make target is missing: v1-rc-roadmap-check")
    if "v1-rc-roadmap-check" not in release_check_body:
        failures.append("v1-rc-roadmap-check is missing from release-check")
    if "v1.0 RC roadmap" not in readme:
        failures.append("README is missing v1.0 RC roadmap reference")

    phases = [line for line in text.splitlines() if line.startswith("## Phase ")]
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "roadmap_doc": doc_rel,
        "phase_count": len(phases),
        "tool_count": 24,
        "selected_capability": "not selected",
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 RC roadmap check",
        f"valid: {str(report['valid']).lower()}",
        f"roadmap_doc: {report['roadmap_doc']}",
        f"phase_count: {report['phase_count']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

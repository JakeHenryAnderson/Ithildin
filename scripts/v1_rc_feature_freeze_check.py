"""Validate the v1.0 RC feature-freeze boundary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    capability_decision_report,
    next_capability_readiness,
    no_new_powers_guardrail,
    review_docs,
    tool_surface_invariant_gate,
    v1_rc_readiness_check,
    v1_rc_roadmap_check,
    v1_rc_status_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/v1.0-rc-feature-freeze.md"

REQUIRED_PHRASES = [
    "Status: v1.0 local-preview feature-freeze gate.",
    "Freeze Decision",
    "governed tool count remains `24`",
    "latest implemented governed tool remains `sandbox.artifact.write_text`",
    "no next capability is selected",
    "capability expansion remains blocked",
    "public/security-product positioning remains blocked",
    "runtime changes are allowed only for blocking release fixes",
    "Allowed During Freeze",
    "Blocked During Freeze",
    "Unfreeze Conditions",
    "make v1-rc-feature-freeze",
    "Stop Conditions",
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
    doc_rel = DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    reports = {
        "tool_surface": tool_surface_invariant_gate.build_report(repo_root),
        "no_new_powers": no_new_powers_guardrail.build_report(repo_root),
        "next_capability": next_capability_readiness.build_report(repo_root),
        "capability_decision": capability_decision_report.build_report(repo_root),
        "v1_status": v1_rc_status_check.build_report(repo_root),
        "v1_roadmap": v1_rc_roadmap_check.build_report(repo_root),
        "v1_readiness": v1_rc_readiness_check.build_report(repo_root),
    }
    for name, report in reports.items():
        failures.extend(f"{name}: {failure}" for failure in report.get("failures", []))
        failures.extend(f"{name}: {failure}" for failure in report.get("hard_failures", []))

    tool_surface = reports["tool_surface"]
    next_capability = reports["next_capability"]
    capability_decision = reports["capability_decision"]
    v1_status = reports["v1_status"]
    v1_readiness = reports["v1_readiness"]

    if tool_surface.get("tool_count") != 24:
        failures.append("feature freeze requires governed tool count 24")
    if next_capability.get("next_candidate") != "not selected":
        failures.append("feature freeze requires no selected next capability")
    if next_capability.get("next_candidate_status") != "pending_selection":
        failures.append("feature freeze requires next capability status pending_selection")
    if capability_decision.get("capability_expansion_allowed") is not False:
        failures.append("feature freeze requires capability expansion blocked")
    if capability_decision.get("decision") != "blocked":
        failures.append("feature freeze requires capability decision blocked")
    if v1_status.get("latest_implemented_tool") != "sandbox.artifact.write_text":
        failures.append("feature freeze requires sandbox.artifact.write_text as latest tool")
    if v1_status.get("public_security_product_positioning_allowed") is not False:
        failures.append("feature freeze requires public/security-product positioning blocked")
    if v1_readiness.get("runtime_changes_allowed") is not False:
        failures.append("feature freeze requires v1 readiness runtime_changes_allowed false")

    text = ""
    if not doc_path.exists():
        failures.append("v1.0 RC feature-freeze doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 RC feature-freeze doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                failures.append(f"v1.0 RC feature-freeze doc contains forbidden phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 RC feature-freeze doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 RC feature-freeze doc is missing from docs-site inputs")
    if "v1-rc-feature-freeze:" not in makefile:
        failures.append("Make target is missing: v1-rc-feature-freeze")
    if "v1-rc-feature-freeze" not in release_check_body:
        failures.append("v1-rc-feature-freeze is missing from release-check")
    if "make v1-rc-feature-freeze" not in readme:
        failures.append("README is missing v1.0 RC feature-freeze command reference")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "freeze_doc": doc_rel,
        "tool_count": tool_surface.get("tool_count"),
        "latest_implemented_tool": v1_status.get("latest_implemented_tool"),
        "selected_capability": next_capability.get("next_candidate"),
        "capability_decision": capability_decision.get("decision"),
        "capability_expansion_allowed": False,
        "public_security_product_positioning_allowed": False,
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 RC feature-freeze check",
        f"valid: {str(report['valid']).lower()}",
        f"freeze_doc: {report['freeze_doc']}",
        f"tool_count: {report['tool_count']}",
        f"latest_implemented_tool: {report['latest_implemented_tool']}",
        f"selected_capability: {report['selected_capability']}",
        f"capability_decision: {report['capability_decision']}",
        "capability_expansion_allowed: false",
        "public_security_product_positioning_allowed: false",
        "runtime_changes_allowed: false",
        "new_power_classes_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

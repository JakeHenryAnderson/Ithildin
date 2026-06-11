"""Validate observability/control mapping readiness without adding runtime powers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    control_mapping_design_check,
    data_classification_design_check,
    incident_reconstruction_check,
    no_new_powers_guardrail,
    observability_readiness,
    review_docs,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
GATE_DOC = ROOT / "docs/codex/control-mapping-readiness-gate.md"
REQUIRED_GATE_PHRASES = [
    "Status: release-readiness gate",
    "does not add runtime behavior",
    "make control-mapping-readiness",
    "observability-readiness",
    "data-classification-design-check",
    "control-mapping-design-check",
    "incident-reconstruction-check",
    "no-new-powers-guardrail",
    "tool-surface-invariant-gate",
    "tool count remains `14`",
    "control mapping support",
    "mediated actions only",
    "no new powerful tool classes",
    "runtime changes are not allowed",
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
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    observability = observability_readiness.build_report(repo_root)
    classification = data_classification_design_check.build_report(repo_root)
    mapping = control_mapping_design_check.build_report(repo_root)
    reconstruction = incident_reconstruction_check.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)

    failures.extend(f"observability-readiness: {failure}" for failure in observability["failures"])
    failures.extend(f"data-classification: {failure}" for failure in classification["failures"])
    failures.extend(f"control-mapping: {failure}" for failure in mapping["failures"])
    failures.extend(f"incident-reconstruction: {failure}" for failure in reconstruction["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(
        _validate_doc(
            repo_root=repo_root,
            docs_site=docs_site,
            readme=readme,
        )
    )

    if "control-mapping-readiness:" not in makefile:
        failures.append("Make target is missing: control-mapping-readiness")
    if "control-mapping-readiness" not in release_check_body:
        failures.append("control-mapping-readiness is missing from release-check")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "observability_readiness_valid": observability["valid"],
        "data_classification_design_valid": classification["valid"],
        "control_mapping_design_valid": mapping["valid"],
        "incident_reconstruction_valid": reconstruction["valid"],
        "broader_capability_expansion_allowed": False,
        "new_power_classes_allowed": False,
        "runtime_changes_allowed": False,
    }


def _validate_doc(*, repo_root: Path, docs_site: str, readme: str) -> list[str]:
    failures: list[str] = []
    rel_path = GATE_DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / rel_path
    if not doc_path.exists():
        failures.append("control mapping readiness gate doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
    for phrase in REQUIRED_GATE_PHRASES:
        if phrase not in text:
            failures.append(f"control mapping readiness gate is missing phrase: {phrase}")
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("control mapping readiness gate is missing from review docs")
    if rel_path not in docs_site:
        failures.append("control mapping readiness gate is missing from docs-site inputs")
    if "control-mapping-readiness-gate.md" not in readme:
        failures.append("README is missing control-mapping-readiness-gate.md")
    return failures


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin control mapping readiness gate",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "broader_capability_expansion_allowed: false",
        "runtime_changes_allowed: false",
        "new_power_classes_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

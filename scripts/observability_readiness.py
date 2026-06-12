"""Validate observability evidence/design readiness without adding runtime powers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    agent_run_evidence_contract_check,
    next_capability_readiness,
    no_new_powers_guardrail,
    review_docs,
    siem_evidence_design_check,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
GATE_DOC = ROOT / "docs/codex/observability-readiness-gate.md"
SANDBOX_DOC = ROOT / "docs/codex/sandbox-workspace-boundary-contract.md"
REQUIRED_GATE_PHRASES = [
    "Status: release-readiness gate",
    "does not add runtime behavior",
    "make observability-readiness",
    "agent-run-evidence-contract-check",
    "siem-evidence-design-check",
    "next-capability-readiness",
    "no-new-powers-guardrail",
    "tool-surface-invariant-gate",
    "tool count remains `16`",
    "operator-managed",
    "export-design-only",
    "no new powerful tool classes",
]
REQUIRED_SANDBOX_PHRASES = [
    "Status: design/evidence contract",
    "operator-managed sandbox",
    "`sandbox_id`",
    "`workspace_id`",
    "trusted config source",
    "support status",
    "warning state",
    "does not",
    "start containers",
    "mount the Docker socket",
    "run shell commands",
    "manage Kubernetes",
    "kernel isolation",
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

    agent = agent_run_evidence_contract_check.build_report(repo_root)
    siem = siem_evidence_design_check.build_report(repo_root)
    next_capability = next_capability_readiness.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    failures.extend(f"agent-run-evidence: {failure}" for failure in agent["failures"])
    failures.extend(f"siem-evidence: {failure}" for failure in siem["failures"])
    failures.extend(f"next-capability: {failure}" for failure in next_capability["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])

    failures.extend(
        _validate_doc(
            repo_root=repo_root,
            path=GATE_DOC,
            required_phrases=REQUIRED_GATE_PHRASES,
            label="observability readiness gate",
            docs_site=docs_site,
            readme=readme,
        )
    )
    failures.extend(
        _validate_doc(
            repo_root=repo_root,
            path=SANDBOX_DOC,
            required_phrases=REQUIRED_SANDBOX_PHRASES,
            label="sandbox workspace boundary contract",
            docs_site=docs_site,
            readme=readme,
        )
    )
    if "observability-readiness:" not in makefile:
        failures.append("Make target is missing: observability-readiness")
    if "observability-readiness" not in release_check_body:
        failures.append("observability-readiness is missing from release-check")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "agent_run_evidence_contract_valid": agent["valid"],
        "siem_evidence_design_valid": siem["valid"],
        "next_capability_candidate": next_capability.get("next_candidate"),
        "next_candidate_implementation_allowed": False,
        "broader_capability_expansion_allowed": False,
        "new_power_classes_allowed": False,
        "runtime_changes_allowed": False,
    }


def _validate_doc(
    *,
    repo_root: Path,
    path: Path,
    required_phrases: list[str],
    label: str,
    docs_site: str,
    readme: str,
) -> list[str]:
    failures: list[str] = []
    rel_path = path.relative_to(ROOT).as_posix()
    doc_path = repo_root / rel_path
    if not doc_path.exists():
        failures.append(f"{label} is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
    for phrase in required_phrases:
        if phrase not in text:
            failures.append(f"{label} is missing phrase: {phrase}")
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append(f"{label} is missing from review docs")
    if rel_path not in docs_site:
        failures.append(f"{label} is missing from docs-site inputs")
    if Path(rel_path).name not in readme:
        failures.append(f"README is missing {Path(rel_path).name}")
    return failures


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin observability readiness gate",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        f"next_capability_candidate: {report.get('next_capability_candidate')}",
        "next_candidate_implementation_allowed: false",
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

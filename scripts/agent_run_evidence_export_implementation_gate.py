"""Validate the bounded Agent Run evidence export endpoint implementation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import agent_run_evidence_export_plan_check, no_new_powers_guardrail, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs/codex/agent-run-evidence-export-implementation.md"
REQUIRED_PHRASES = [
    "Status: approved bounded read-only implementation",
    "GET /runs/{run_id}/evidence-export",
    "Admin bearer token required",
    "Unknown query parameters are rejected",
    "`timeline_limit`",
    "`evidence_hashes`",
    "`redaction_summary`",
    "`warnings`",
    "Missing correlations are represented as warnings",
    "excludes prompts",
    "raw tool arguments",
    "file contents",
    "diffs",
    "response bodies",
    "secrets",
    "Path-like values are omitted or represented as hashes",
    "does not return raw audit `resource` objects",
    "Ithildin-mediated actions only",
    "make agent-run-evidence-export-implementation-gate",
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
    rel_path = DOC_PATH.relative_to(ROOT).as_posix()
    doc_path = repo_root / rel_path
    app = (repo_root / "apps/api/src/ithildin_api/app.py").read_text(encoding="utf-8")
    agent_runs = (repo_root / "apps/api/src/ithildin_api/agent_runs.py").read_text(
        encoding="utf-8"
    )
    api_tests = (repo_root / "tests/test_api_service.py").read_text(encoding="utf-8")
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("Agent Run evidence export implementation doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"implementation doc is missing phrase: {phrase}")
    required_source = [
        ("API route", '"/runs/{run_id}/evidence-export"', app),
        ("run ID validation", "_valid_agent_run_id", app),
        ("export assembly", "def evidence_export", agent_runs),
        ("safe timeline metadata", "_safe_timeline_metadata", agent_runs),
        ("path hashing", "path_hash", agent_runs),
        ("API auth test", "test_run_evidence_export_requires_auth", api_tests),
        ("bad input test", "test_run_evidence_export_denies_bad_inputs_safely", api_tests),
    ]
    for label, phrase, source in required_source:
        if phrase not in source:
            failures.append(f"missing implementation evidence: {label}")
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("Agent Run evidence export implementation doc is missing from review docs")
    if rel_path not in docs_site:
        failures.append(
            "Agent Run evidence export implementation doc is missing from docs-site inputs"
        )
    if "agent-run-evidence-export-implementation-gate:" not in makefile:
        failures.append("Make target is missing: agent-run-evidence-export-implementation-gate")
    if "agent-run-evidence-export-implementation-gate" not in release_check_body:
        failures.append(
            "agent-run-evidence-export-implementation-gate is missing from release-check"
        )
    if "make agent-run-evidence-export-implementation-gate" not in readme:
        failures.append("README is missing agent-run-evidence-export-implementation-gate")

    plan = agent_run_evidence_export_plan_check.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"agent-run-evidence-export-plan: {failure}" for failure in plan["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "endpoint": "GET /runs/{run_id}/evidence-export",
        "implementation_status": "approved_limited_read_only",
        "runtime_implemented": True,
        "new_power_classes_allowed": False,
        "tool_count": no_new_powers.get("tool_count"),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Agent Run evidence export implementation gate",
        f"valid: {str(report['valid']).lower()}",
        f"endpoint: {report['endpoint']}",
        f"implementation_status: {report['implementation_status']}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "new_power_classes_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

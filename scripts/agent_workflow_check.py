"""Validate Ithildin's AGENTS.md planner-implementer workflow guidance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = Path("AGENTS.md")
WORKFLOW_DOC = Path("docs/codex/agent-workflow-instruction-layer.md")

REQUIRED_AGENTS_PHRASES = [
    "coordination guidance, not a security boundary",
    "local-preview governed MCP/tool gateway",
    "Current governed tool count is 19",
    "Low Codex implementers are the preferred mechanical delegation path",
    "Use `gpt-5.4-mini` with low",
    "Use one Low Codex implementer at a time by default",
    "should remain disabled until several read-only trials",
    "Gemma/local-model output is advisory only",
    "must not decide safety boundaries",
    "Do not add shell execution",
    "Docker socket access",
    "Kubernetes tools",
    "browser automation",
    "arbitrary HTTP methods/headers/bodies",
    "broad filesystem writes",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP hosting",
    "plugin SDK behavior",
    "make agent-workflow-check",
    "Stop and report status",
]

REQUIRED_WORKFLOW_PHRASES = [
    "planner-implementer workflow",
    "not a policy engine, sandbox, approval workflow, or security boundary",
    "Low Codex implementer",
    "report-first",
    "Use one at a time by default",
    "Direct edits should remain disabled",
    "Gemma/local-model suggester",
    "Delegation Packet Shape",
    "Forbidden changes",
    "The current governed tool count is 19",
    "make agent-workflow-check",
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
    agents = _read_required(repo_root / AGENTS_PATH, failures)
    workflow = _read_required(repo_root / WORKFLOW_DOC, failures)
    readme = _read_required(repo_root / "README.md", failures)
    makefile = _read_required(repo_root / "Makefile", failures)
    review_docs = _read_required(repo_root / "scripts/review_docs.py", failures)
    docs_site = _read_required(repo_root / "scripts/build_docs_site.py", failures)

    failures.extend(_missing_phrases(AGENTS_PATH.as_posix(), agents, REQUIRED_AGENTS_PHRASES))
    failures.extend(_missing_phrases(WORKFLOW_DOC.as_posix(), workflow, REQUIRED_WORKFLOW_PHRASES))
    if "agent-workflow-check:" not in makefile:
        failures.append("Makefile is missing agent-workflow-check target")
    if "make agent-workflow-check" not in readme:
        failures.append("README.md does not document make agent-workflow-check")
    if AGENTS_PATH.as_posix() not in review_docs:
        failures.append("AGENTS.md is missing from review docs")
    if WORKFLOW_DOC.as_posix() not in review_docs:
        failures.append("agent workflow doc is missing from review docs")
    if AGENTS_PATH.as_posix() not in docs_site:
        failures.append("AGENTS.md is missing from docs-site inputs")
    if WORKFLOW_DOC.as_posix() not in docs_site:
        failures.append("agent workflow doc is missing from docs-site inputs")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "agents_path": AGENTS_PATH.as_posix(),
        "workflow_doc": WORKFLOW_DOC.as_posix(),
        "tool_count": 19,
        "low_implementer_runtime_changes_allowed": False,
        "low_codex_preferred_mechanical_path": True,
        "gemma_output_advisory_only": True,
        "guidance_is_security_boundary": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin agent workflow instruction check",
        f"valid: {str(report['valid']).lower()}",
        f"agents_path: {report['agents_path']}",
        f"workflow_doc: {report['workflow_doc']}",
        f"tool_count: {report['tool_count']}",
        "low_implementer_runtime_changes_allowed: false",
        "low_codex_preferred_mechanical_path: true",
        "gemma_output_advisory_only: true",
        "guidance_is_security_boundary: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read_required(path: Path, failures: list[str]) -> str:
    if not path.exists():
        failures.append(f"{path.relative_to(ROOT).as_posix()} is missing")
        return ""
    return path.read_text(encoding="utf-8")


def _missing_phrases(path: str, text: str, phrases: list[str]) -> list[str]:
    return [f"{path} missing required phrase: {phrase}" for phrase in phrases if phrase not in text]


if __name__ == "__main__":
    raise SystemExit(main())

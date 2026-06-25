"""Validate sandbox.artifact.write_text implementation-boundary decision."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    no_new_powers_guardrail,
    sandbox_artifact_write_text_preimplementation_check,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
DECISION_DOC = ROOT / "docs/codex/sandbox-artifact-write-text-implementation-decision.md"
MANIFEST_PATH = ROOT / "tool-manifests/sandbox-artifact-write-text.yaml"
REQUIRED_PHRASES = [
    "Status: implementation boundary approved",
    "Runtime implementation remains absent",
    "tool name: `sandbox.artifact.write_text`",
    "resource type: `sandbox_artifact`",
    "first demo target: `hello-demo/hello.txt` containing `Hello World`",
    "deny direct trusted-host writes",
    "require approval",
    "approval and audit evidence",
    "manifest and manifest-lock update",
    "policy preview/runtime parity for `sandbox_artifact`",
    "source-review handoff bundle",
    "This decision does not approve shell execution",
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
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    preimplementation = sandbox_artifact_write_text_preimplementation_check.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"preimplementation: {failure}" for failure in preimplementation["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    decision_path = repo_root / DECISION_DOC.relative_to(ROOT)
    if not decision_path.exists():
        failures.append("sandbox.artifact.write_text implementation decision doc is missing")
    else:
        text = decision_path.read_text(encoding="utf-8")
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"implementation decision is missing phrase: {phrase}")
    rel_path = DECISION_DOC.relative_to(repo_root).as_posix()
    review_docs_text = (repo_root / "scripts/review_docs.py").read_text(encoding="utf-8")
    if rel_path not in review_docs_text:
        failures.append("implementation decision is missing from review docs")
    if rel_path not in docs_site:
        failures.append("implementation decision is missing from docs-site inputs")
    if "make sandbox-artifact-write-text-implementation-gate" not in readme:
        failures.append("README is missing make sandbox-artifact-write-text-implementation-gate")
    if "sandbox-artifact-write-text-implementation-gate:" not in makefile:
        failures.append("Make target is missing: sandbox-artifact-write-text-implementation-gate")
    if "sandbox-artifact-write-text-implementation-gate" not in release_check_body:
        failures.append(
            "sandbox-artifact-write-text-implementation-gate is missing from release-check"
        )
    if MANIFEST_PATH.exists():
        failures.append(
            "sandbox.artifact.write_text manifest must remain absent before runtime sprint"
        )
    if tool_surface.get("tool_count") != 23:
        failures.append("tool surface tool count is not 23")
    if no_new_powers.get("new_power_classes_allowed") is not False:
        failures.append("no-new-powers guardrail allows new power classes")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_name": "sandbox.artifact.write_text",
        "implementation_status": "approved_future_bounded_write_boundary",
        "runtime_implemented": False,
        "runtime_changes_allowed_now": False,
        "future_runtime_implementation_allowed": True,
        "tool_count": tool_surface.get("tool_count"),
        "manifest_absent": not MANIFEST_PATH.exists(),
        "new_power_classes_allowed": no_new_powers.get("new_power_classes_allowed"),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox.artifact.write_text implementation gate",
        f"valid: {str(report['valid']).lower()}",
        f"tool_name: {report['tool_name']}",
        f"implementation_status: {report['implementation_status']}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "runtime_implemented: false",
        "runtime_changes_allowed_now: false",
        "future_runtime_implementation_allowed: true",
        f"manifest_absent: {str(report['manifest_absent']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

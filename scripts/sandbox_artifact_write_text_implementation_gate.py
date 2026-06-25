"""Validate sandbox.artifact.write_text runtime implementation boundaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
DECISION_DOC = ROOT / "docs/codex/sandbox-artifact-write-text-implementation-decision.md"
MANIFEST_PATH = ROOT / "tool-manifests/sandbox-artifact-write-text.yaml"
EXECUTOR_PATH = ROOT / "apps/api/src/ithildin_api/sandbox_artifacts.py"
TEST_PATH = ROOT / "tests/test_governed_tool_calls.py"
REQUIRED_DECISION_PHRASES = [
    "Status: runtime implementation approved for bounded local-preview use.",
    "tool name: `sandbox.artifact.write_text`",
    "resource type: `sandbox_artifact`",
    "deny direct trusted-host writes",
    "require approval",
    "approval and audit evidence",
    "manifest and manifest-lock update",
    "policy preview/runtime parity for `sandbox_artifact`",
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
    review_docs_text = (repo_root / "scripts/review_docs.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    decision_path = repo_root / DECISION_DOC.relative_to(ROOT)
    if not decision_path.exists():
        failures.append("sandbox.artifact.write_text implementation decision doc is missing")
    else:
        text = decision_path.read_text(encoding="utf-8")
        for phrase in REQUIRED_DECISION_PHRASES:
            if phrase not in text:
                failures.append(f"implementation decision is missing phrase: {phrase}")
    rel_path = DECISION_DOC.relative_to(repo_root).as_posix()
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
    if "sandbox-artifact-write-text-preimplementation-check" in release_check_body:
        failures.append("preimplementation check must not run after runtime implementation")
    if not MANIFEST_PATH.exists():
        failures.append("sandbox.artifact.write_text manifest is missing")
    if not EXECUTOR_PATH.exists():
        failures.append("sandbox artifact executor module is missing")
    else:
        executor_text = EXECUTOR_PATH.read_text(encoding="utf-8")
        for phrase in [
            "SANDBOX_ARTIFACT_WRITE_TEXT_TOOL",
            "approval_scope",
            "apply_approved",
            "content_sha256",
            "host_promotion_performed",
        ]:
            if phrase not in executor_text:
                failures.append(f"executor is missing phrase: {phrase}")
    test_text = TEST_PATH.read_text(encoding="utf-8")
    for phrase in [
        "test_sandbox_artifact_write_requires_approval_and_executes_once",
        "test_sandbox_artifact_write_rejects_scope_mismatch_without_write",
        "test_sandbox_artifact_write_denies_unsafe_paths",
        "test_sandbox_artifact_write_audit_metadata_is_secret_free",
    ]:
        if phrase not in test_text:
            failures.append(f"governed tool tests are missing: {phrase}")
    if tool_surface.get("tool_count") != 24:
        failures.append("tool surface tool count is not 24")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_name": "sandbox.artifact.write_text",
        "implementation_status": "bounded_local_preview_runtime",
        "runtime_implemented": True,
        "runtime_changes_allowed_now": True,
        "tool_count": tool_surface.get("tool_count"),
        "manifest_present": MANIFEST_PATH.exists(),
        "new_power_classes_allowed": no_new_powers.get("new_power_classes_allowed"),
        "approved_bounded_sandbox_write": no_new_powers.get("approved_bounded_sandbox_write"),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox.artifact.write_text implementation gate",
        f"valid: {str(report['valid']).lower()}",
        f"tool_name: {report['tool_name']}",
        f"implementation_status: {report['implementation_status']}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "runtime_implemented: true",
        "runtime_changes_allowed_now: true",
        f"manifest_present: {str(report['manifest_present']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

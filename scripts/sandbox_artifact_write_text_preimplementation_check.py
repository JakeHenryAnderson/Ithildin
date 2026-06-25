"""Validate sandbox.artifact.write_text preimplementation planning boundaries."""

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
    review_docs,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
ROADMAP_DOC = ROOT / "docs/codex/hello-world-sandbox-demo-roadmap.md"
PROPOSAL_DOC = ROOT / "docs/codex/capability-proposals/sandbox-artifact-write-text.md"
IMPLEMENTATION_PLAN_DOC = (
    ROOT / "docs/codex/capability-implementation-plans/sandbox-artifact-write-text.md"
)
FIXTURE_PLAN_DOC = ROOT / "docs/codex/sandbox-artifact-write-text-fixture-plan.md"
NEGATIVE_PLAN_DOC = ROOT / "docs/codex/sandbox-artifact-write-text-negative-transcripts.md"
SOURCE_REVIEW_DOC = ROOT / "docs/codex/sandbox-artifact-write-text-source-review.md"
PROMOTION_CONTRACT_DOC = ROOT / "docs/codex/sandbox-promotion-evidence-contract.md"
FIXTURE_ARTIFACT = ROOT / "tests/fixtures/sandbox_artifact_write_text_fixture_contract.json"
MANIFEST_PATH = ROOT / "tool-manifests/sandbox-artifact-write-text.yaml"

REQUIRED_DOCS = [
    ROADMAP_DOC,
    PROPOSAL_DOC,
    IMPLEMENTATION_PLAN_DOC,
    FIXTURE_PLAN_DOC,
    NEGATIVE_PLAN_DOC,
    SOURCE_REVIEW_DOC,
    PROMOTION_CONTRACT_DOC,
]
REQUIRED_SCENARIOS = [
    "hello world artifact creation",
    "empty parent directory creation denied without approval",
    "traversal denied",
    "absolute path denied",
    "encoded ambiguity denied",
    "control character denied",
    "hidden sensitive and git paths denied",
    "symlink and hardlink denied",
    "overwrite denied by default",
    "replayed approval denied",
    "missing sandbox profile denied",
    "host write denied without promotion",
    "oversized or unsupported content denied",
    "unauthorized principal denied",
]
STRICT_NON_LEAK_LIST = [
    "no file contents in responses or audit metadata",
    "no raw host paths",
    "no prompts or chain-of-thought",
    "no secrets",
    "no environment names or values",
    "no shell output",
    "no VM logs",
    "no unrelated directory listings",
    "no sandbox root internals",
    "no Mission Control private state",
    "no production identity claims",
    "no compliance claims",
]
REQUIRED_PHRASES = {
    IMPLEMENTATION_PLAN_DOC: [
        "Status: implementation-planning only.",
        "Implementation is blocked",
        "No manifest is added",
        "sandbox_artifact",
        "approval binding",
        "same-directory temporary file and atomic replace",
        "Mission Control remains the operator surface and evidence viewer",
        "Actual implementation remains blocked",
    ],
    FIXTURE_PLAN_DOC: [
        "Status: future fixture/test contract only.",
        "The proposed tool remains blocked",
        "hello world artifact creation",
        "host write denied without promotion",
        "unauthorized principal denied",
    ],
    NEGATIVE_PLAN_DOC: [
        "Status: future negative-transcript plan only.",
        "overwrite denied by default",
        "Mission Control metadata cannot substitute for Ithildin execution",
    ],
    SOURCE_REVIEW_DOC: [
        "Status: future source-review handoff only.",
        "Runtime implementation: blocked.",
        "EXT-SANDBOX-WRITE-###",
        "No source-review closure is claimed",
    ],
    PROMOTION_CONTRACT_DOC: [
        "Status: design-only evidence contract.",
        "auto_promotion_performed",
        "approval_id",
    ],
}
FORBIDDEN_PHRASES = [
    "production-ready",
    "compliance-grade",
    "tamper-proof",
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
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    for doc_path in REQUIRED_DOCS:
        _check_doc(repo_root, doc_path, failures, docs_site=docs_site)

    if MANIFEST_PATH.exists():
        failures.append("sandbox.artifact.write_text manifest must remain absent")
    if "sandbox-artifact-write-text-preimplementation-check:" not in makefile:
        failures.append(
            "Make target is missing: sandbox-artifact-write-text-preimplementation-check"
        )
    if "sandbox-artifact-write-text-preimplementation-check" not in release_check_body:
        failures.append(
            "sandbox-artifact-write-text-preimplementation-check is missing from release-check"
        )
    if "make sandbox-artifact-write-text-preimplementation-check" not in readme:
        failures.append(
            "README is missing make sandbox-artifact-write-text-preimplementation-check"
        )
    if "tool count remains `23`" not in readme:
        failures.append("README is missing current tool count reference")

    fixture_artifact = _load_fixture_artifact(repo_root, failures)
    if fixture_artifact is not None:
        _check_fixture_artifact(fixture_artifact, failures)

    if tool_surface.get("tool_count") != 23:
        failures.append("tool surface tool count is not 23")
    if no_new_powers.get("new_power_classes_allowed") is not False:
        failures.append("no-new-powers guardrail allows new power classes")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "proposal": "sandbox.artifact.write_text",
        "scope": "preimplementation_planning",
        "implementation_allowed": False,
        "runtime_changes_allowed": False,
        "write_capability_implemented": False,
        "tool_count": tool_surface.get("tool_count"),
        "new_power_classes_allowed": no_new_powers.get("new_power_classes_allowed"),
        "manifest_absent": not MANIFEST_PATH.exists(),
    }


def _check_doc(repo_root: Path, path: Path, failures: list[str], *, docs_site: str) -> None:
    rel_path = path.relative_to(repo_root).as_posix()
    if not path.exists():
        failures.append(f"doc is missing: {rel_path}")
        return
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    for phrase in REQUIRED_PHRASES.get(path, []):
        if phrase not in text:
            failures.append(f"{rel_path} is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            failures.append(f"{rel_path} contains forbidden phrase: {phrase}")
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append(f"{rel_path} is missing from review docs")
    if rel_path not in docs_site:
        failures.append(f"{rel_path} is missing from docs-site inputs")


def _load_fixture_artifact(repo_root: Path, failures: list[str]) -> dict[str, Any] | None:
    fixture_path = repo_root / FIXTURE_ARTIFACT.relative_to(ROOT)
    if not fixture_path.exists():
        failures.append("sandbox.artifact.write_text fixture artifact is missing")
        return None
    try:
        fixture_artifact = json.loads(fixture_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"sandbox.artifact.write_text fixture artifact is invalid json: {exc.msg}")
        return None
    if not isinstance(fixture_artifact, dict):
        failures.append("sandbox.artifact.write_text fixture artifact must be a JSON object")
        return None
    return fixture_artifact


def _check_fixture_artifact(fixture_artifact: dict[str, Any], failures: list[str]) -> None:
    if fixture_artifact.get("version") != "1":
        failures.append("fixture artifact must report version: 1")
    if fixture_artifact.get("contract") != "sandbox.artifact.write_text":
        failures.append("fixture artifact must report contract: sandbox.artifact.write_text")
    if fixture_artifact.get("scope") != "preimplementation_fixture_contract":
        failures.append("fixture artifact must report preimplementation fixture scope")

    strict_non_leak_list = fixture_artifact.get("strict_non_leak_list")
    if not isinstance(strict_non_leak_list, list):
        failures.append("fixture artifact strict_non_leak_list must be a list")
    else:
        lowered = {str(item).lower() for item in strict_non_leak_list}
        for item in STRICT_NON_LEAK_LIST:
            if item.lower() not in lowered:
                failures.append(f"fixture artifact is missing strict non-leak entry: {item}")

    scenarios = fixture_artifact.get("scenarios")
    if not isinstance(scenarios, list):
        failures.append("fixture artifact scenarios must be a list")
        return

    scenario_names: list[str] = []
    scenario_ids: set[str] = set()
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            failures.append(f"fixture artifact scenario {index} must be an object")
            continue
        scenario_name = scenario.get("scenario")
        scenario_id = scenario.get("id")
        if not isinstance(scenario_name, str):
            failures.append(f"fixture artifact scenario {index} missing scenario name")
        else:
            scenario_names.append(scenario_name)
        if not isinstance(scenario_id, str):
            failures.append(f"fixture artifact scenario {index} missing id")
        elif scenario_id in scenario_ids:
            failures.append(f"fixture artifact duplicate scenario id: {scenario_id}")
        else:
            scenario_ids.add(scenario_id)

        safe_expected_labels = scenario.get("safe_expected_labels")
        if not isinstance(safe_expected_labels, list) or not safe_expected_labels:
            failures.append(f"fixture artifact scenario {index} must include safe_expected_labels")
        non_leak_assertions = scenario.get("non_leak_assertions")
        if not isinstance(non_leak_assertions, list) or not non_leak_assertions:
            failures.append(f"fixture artifact scenario {index} must include non_leak_assertions")
        future_test_type = scenario.get("future_test_type")
        if not isinstance(future_test_type, str) or not future_test_type:
            failures.append(f"fixture artifact scenario {index} must include future_test_type")

    for scenario in REQUIRED_SCENARIOS:
        if scenario not in scenario_names:
            failures.append(f"fixture artifact is missing scenario: {scenario}")


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox.artifact.write_text preimplementation check",
        f"valid: {str(report['valid']).lower()}",
        f"proposal: {report['proposal']}",
        f"scope: {report['scope']}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "implementation_allowed: false",
        "runtime_changes_allowed: false",
        "write_capability_implemented: false",
        f"manifest_absent: {str(report['manifest_absent']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

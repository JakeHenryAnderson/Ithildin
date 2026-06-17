"""Validate the project.risk.summary preimplementation fixture contract."""

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
    project_risk_summary_implementation_gate,
    project_risk_summary_implementation_plan_check,
    project_risk_summary_proposal_check,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_DOC = ROOT / "docs/codex/capability-proposals/project-risk-summary.md"
IMPLEMENTATION_PLAN_DOC = (
    ROOT / "docs/codex/capability-implementation-plans/project-risk-summary.md"
)
IMPLEMENTATION_BOUNDARY_DOC = ROOT / "docs/codex/v3-project-risk-summary-implementation.md"
FIXTURE_PLAN_DOC = ROOT / "docs/codex/project-risk-summary-fixture-plan.md"
FIXTURE_ARTIFACT = ROOT / "tests/fixtures/project_risk_summary_fixture_contract.json"
REQUIRED_SCENARIOS = [
    "empty workspace / no risk-shaped files",
    "coarse risk signal files present by category only",
    "security config shaped files counted without names or contents",
    "secrets-adjacent shaped files counted without secret names or values",
    "dependency risk shaped files counted without dependency or package names",
    "CI/deploy risk shaped files counted without workflow names or command values",
    "mixed safe and skipped candidates",
    "depth-limit truncation",
    "item-limit truncation",
    "category filter limits output categories",
    "hidden/sensitive path skipped",
    ".git skipped",
    "symlink skipped",
    "hardlink skipped",
    "binary/NUL skipped",
    "oversized input skipped",
    "unsupported encoding skipped",
    "malformed config shape counted as safe unknown",
    "unauthorized principal denied in future governed-call tests",
]
STRICT_NON_LEAK_LIST = [
    "no filenames",
    "no raw paths",
    "no file contents",
    "no dependency names",
    "no package names",
    "no CVE IDs",
    "no advisory IDs",
    "no secret names",
    "no secret values",
    "no environment names/values",
    "no command/script values",
    "no registry URLs",
    "no scanner output",
    "no vulnerability findings",
    "no compliance findings",
    "no security findings",
    "no shell/Git/package-manager/CI output",
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

    proposal = project_risk_summary_proposal_check.build_report(repo_root)
    implementation_plan = project_risk_summary_implementation_plan_check.build_report(repo_root)
    implementation_gate = project_risk_summary_implementation_gate.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)

    failures.extend(f"proposal: {failure}" for failure in proposal["failures"])
    failures.extend(
        f"implementation-plan: {failure}" for failure in implementation_plan["failures"]
    )
    failures.extend(
        f"implementation-gate: {failure}" for failure in implementation_gate["failures"]
    )
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    for path, label in [
        (PROPOSAL_DOC, "proposal doc"),
        (IMPLEMENTATION_PLAN_DOC, "implementation plan doc"),
        (IMPLEMENTATION_BOUNDARY_DOC, "implementation boundary doc"),
    ]:
        if not (repo_root / path.relative_to(ROOT)).exists():
            failures.append(f"project.risk.summary {label} is missing")

    fixture_doc_path = repo_root / FIXTURE_PLAN_DOC.relative_to(ROOT)
    if not fixture_doc_path.exists():
        failures.append("project.risk.summary fixture plan doc is missing")
    else:
        lower = fixture_doc_path.read_text(encoding="utf-8").lower()
        for scenario in REQUIRED_SCENARIOS:
            if scenario.lower() not in lower:
                failures.append(f"fixture plan is missing scenario: {scenario}")
        for item in STRICT_NON_LEAK_LIST:
            if item.lower() not in lower:
                failures.append(f"fixture plan is missing strict non-leak entry: {item}")

    fixture_artifact = _load_fixture_artifact(repo_root, failures)
    if fixture_artifact is not None:
        _validate_fixture_artifact(fixture_artifact, failures)

    if implementation_gate.get("runtime_implemented") is not False:
        failures.append("implementation gate must report runtime_implemented: false")
    if implementation_gate.get("future_runtime_implementation_allowed") is not True:
        failures.append("implementation gate must allow a later explicit runtime sprint")
    if implementation_gate.get("tool_count") != 22:
        failures.append("implementation gate tool count is not 22")
    if tool_surface.get("tool_count") != 22:
        failures.append("tool surface tool count is not 22")
    if no_new_powers.get("new_power_classes_allowed") is not False:
        failures.append("no-new-powers guardrail allows new power classes")
    if repo_root.joinpath("tool-manifests/project-risk-summary.yaml").exists():
        failures.append("project.risk.summary manifest must not exist during preimplementation")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "proposal": "project.risk.summary",
        "scope": "preimplementation_fixture_contract",
        "implementation_allowed": False,
        "runtime_changes_allowed": False,
        "proposal_valid": proposal["valid"],
        "implementation_plan_valid": implementation_plan["valid"],
        "implementation_gate_future_runtime_allowed": implementation_gate.get(
            "future_runtime_implementation_allowed"
        ),
        "tool_count": tool_surface.get("tool_count"),
        "new_power_classes_allowed": no_new_powers.get("new_power_classes_allowed"),
        "evidence": {
            "proposal_path": PROPOSAL_DOC.relative_to(ROOT).as_posix(),
            "implementation_plan_path": IMPLEMENTATION_PLAN_DOC.relative_to(ROOT).as_posix(),
            "implementation_boundary_path": (
                IMPLEMENTATION_BOUNDARY_DOC.relative_to(ROOT).as_posix()
            ),
            "fixture_plan_path": FIXTURE_PLAN_DOC.relative_to(ROOT).as_posix(),
            "fixture_artifact_path": FIXTURE_ARTIFACT.relative_to(ROOT).as_posix(),
            "implementation_gate": implementation_gate,
            "tool_surface": tool_surface,
            "no_new_powers": no_new_powers,
        },
    }


def _load_fixture_artifact(repo_root: Path, failures: list[str]) -> dict[str, Any] | None:
    fixture_artifact_path = repo_root / FIXTURE_ARTIFACT.relative_to(ROOT)
    if not fixture_artifact_path.exists():
        failures.append("project.risk.summary fixture artifact is missing")
        return None
    try:
        artifact = json.loads(fixture_artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"project.risk.summary fixture artifact is invalid json: {exc.msg}")
        return None
    if not isinstance(artifact, dict):
        failures.append("project.risk.summary fixture artifact must be a JSON object")
        return None
    return artifact


def _validate_fixture_artifact(
    fixture_artifact: dict[str, Any], failures: list[str]
) -> None:
    if fixture_artifact.get("version") != "1":
        failures.append("fixture artifact must report version: 1")
    if fixture_artifact.get("contract") != "project.risk.summary":
        failures.append("fixture artifact must report contract: project.risk.summary")
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
        scenarios = []
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

        for key in ["safe_expected_labels", "non_leak_assertions"]:
            value = scenario.get(key)
            if not isinstance(value, list) or not value:
                failures.append(f"fixture artifact scenario {index} must include {key}")
        future_test_type = scenario.get("future_test_type")
        if not isinstance(future_test_type, str) or not future_test_type:
            failures.append(f"fixture artifact scenario {index} must include future_test_type")

    for scenario in REQUIRED_SCENARIOS:
        if scenario not in scenario_names:
            failures.append(f"fixture artifact is missing scenario: {scenario}")


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin project.risk.summary preimplementation check",
        f"valid: {str(report['valid']).lower()}",
        "proposal: project.risk.summary",
        "scope: preimplementation_fixture_contract",
        "implementation_allowed: false",
        "runtime_changes_allowed: false",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "runtime_implemented: false",
        "future_runtime_implementation_allowed: true",
        "new_power_classes_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate sandbox/VM static preflight implementation decision boundaries."""

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
    sandbox_vm_static_profile_fixture_contract_check,
    sandbox_vm_static_profile_negative_fixtures_check,
    sandbox_vm_static_profile_preflight_plan_check,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
DECISION_DOC = ROOT / "docs/codex/sandbox-vm-static-preflight-implementation-decision.md"
RUNNER = ROOT / "scripts/sandbox_vm_static_preflight.py"
REQUIRED_PHRASES = [
    "Status: CLI-only implementation implemented for local fixture preflight.",
    "make sandbox-vm-static-preflight-implementation-gate",
    "scripts/sandbox_vm_static_preflight.py",
    "make sandbox-vm-static-preflight",
    "deterministic local CLI",
    "reads a JSON fixture path",
    "secret-free report",
    "Current decisions are `no_go` and `review_required`",
    "raw path-shaped mount/root labels",
    "broad network posture",
    "Mission Control execution authority claims",
    "local model invocation claims",
    "trusted-host promotion claims",
    "governed tool surface changes allowed: `false`",
    "API/MCP behavior changes allowed: `false`",
    "policy rule changes allowed: `false`",
    "runtime sandbox control allowed: `false`",
    "Mission Control runtime allowed: `false`",
    "local model invocation allowed: `false`",
    "sandbox orchestration allowed: `false`",
    "trusted-host promotion allowed: `false`",
    "network expansion allowed: `false`",
    "new power classes allowed: `false`",
    "CLI-only fixture preflight runner allowed: `true`",
    "CLI-only fixture preflight runner implemented: `true`",
    "Broader capability expansion remains blocked.",
]
FORBIDDEN_PHRASES = [
    "Ithildin starts the VM",
    "Ithildin starts containers",
    "Docker socket access is approved",
    "Kubernetes control is approved",
    "Mission Control may execute actions",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "new governed tool power is approved",
    "production sandbox is approved",
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
    makefile = repo_root.joinpath("Makefile").read_text(encoding="utf-8")
    readme = repo_root.joinpath("README.md").read_text(encoding="utf-8")
    docs_site = repo_root.joinpath("scripts/build_docs_site.py").read_text(encoding="utf-8")
    enterprise = repo_root.joinpath("docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    plan = sandbox_vm_static_profile_preflight_plan_check.build_report(repo_root)
    fixture = sandbox_vm_static_profile_fixture_contract_check.build_report(repo_root)
    negative = sandbox_vm_static_profile_negative_fixtures_check.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"preflight-plan: {failure}" for failure in plan["failures"])
    failures.extend(f"fixture-contract: {failure}" for failure in fixture["failures"])
    failures.extend(f"negative-fixtures: {failure}" for failure in negative["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    rel_path = DECISION_DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / rel_path
    text = ""
    if not doc_path.exists():
        failures.append("sandbox/VM static preflight implementation decision doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lower = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase.lower() not in lower:
                failures.append(f"implementation decision doc missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lower:
                failures.append(f"implementation decision doc contains forbidden phrase: {phrase}")

    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("implementation decision is missing from review docs")
    if rel_path not in docs_site:
        failures.append("implementation decision is missing from docs-site inputs")
    if "make sandbox-vm-static-preflight-implementation-gate" not in readme:
        failures.append("README is missing static preflight implementation gate command")
    if "sandbox-vm-static-preflight-implementation-gate:" not in makefile:
        failures.append("Make target is missing: sandbox-vm-static-preflight-implementation-gate")
    if "sandbox-vm-static-preflight-implementation-gate" not in release_check_body:
        failures.append("static preflight implementation gate missing from release-check")
    if "sandbox-vm-static-preflight-implementation-decision.md" not in enterprise:
        failures.append("enterprise runway is missing implementation decision pointer")
    if tool_surface.get("tool_count") != 24:
        failures.append("tool surface tool count is not 24")

    runner_path = repo_root / RUNNER.relative_to(ROOT)
    runner_implemented = runner_path.exists()
    if not runner_implemented:
        failures.append("static preflight runner script is missing")
    else:
        runner_text = runner_path.read_text(encoding="utf-8")
        for phrase in [
            "def build_report(",
            "MAX_FIXTURE_BYTES",
            "sandbox_runtime_inspected",
            "mission_control_runtime_called",
            "local_model_invoked",
            "trusted_host_promotion_performed",
        ]:
            if phrase not in runner_text:
                failures.append(f"static preflight runner is missing phrase: {phrase}")
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_doc": rel_path,
        "implementation_status": (
            "cli_fixture_preflight_implemented"
            if runner_implemented
            else "cli_fixture_preflight_boundary_approved"
        ),
        "tool_count": tool_surface.get("tool_count"),
        "runtime_implemented": runner_implemented,
        "cli_only_fixture_preflight_runner_allowed": True,
        "governed_tool_surface_changes_allowed": False,
        "api_mcp_behavior_changes_allowed": False,
        "policy_rule_changes_allowed": False,
        "runtime_sandbox_control_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static preflight implementation gate",
        f"valid: {str(report['valid']).lower()}",
        f"decision_doc: {report['decision_doc']}",
        f"implementation_status: {report['implementation_status']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_implemented: {str(report['runtime_implemented']).lower()}",
        "cli_only_fixture_preflight_runner_allowed: "
        f"{str(report['cli_only_fixture_preflight_runner_allowed']).lower()}",
        "governed_tool_surface_changes_allowed: "
        f"{str(report['governed_tool_surface_changes_allowed']).lower()}",
        "api_mcp_behavior_changes_allowed: "
        f"{str(report['api_mcp_behavior_changes_allowed']).lower()}",
        f"policy_rule_changes_allowed: {str(report['policy_rule_changes_allowed']).lower()}",
        "runtime_sandbox_control_allowed: "
        f"{str(report['runtime_sandbox_control_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

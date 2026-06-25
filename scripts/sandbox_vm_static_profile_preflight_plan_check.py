"""Validate the design-only sandbox/VM static profile preflight implementation plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, review_docs, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/sandbox-vm-static-profile-preflight-plan.md"

REQUIRED_PHRASES = [
    "Status: implementation-planning only.",
    "Implementation state: blocked.",
    "make sandbox-vm-static-profile-preflight-plan-check",
    "Relationship To Existing Evidence",
    "Future Static Profile Fixture",
    "Future Read-Only Preflight Runner",
    "Proposed Output Contract",
    "Future Negative Transcript Plan",
    "Future Source Review Requirements",
    "Current Allowed State",
    "Future Implementation Gate",
    "schema_version",
    "sandbox_id",
    "workspace_id",
    "profile_label",
    "trusted_config_source",
    "support_status",
    "platform",
    "mounts",
    "network",
    "ingress_egress",
    "cleanup",
    "warnings",
    "decision",
    "ithildin_starts_vm: false",
    "ithildin_starts_container: false",
    "ithildin_has_docker_socket: false",
    "ithildin_has_kubernetes_control: false",
    "ithildin_runs_shell: false",
    "mission_control_executes_actions: false",
    "local_model_invoked: false",
    "trusted_host_promotion_enabled: false",
    "broad_network_access: false",
    "promotion_status: not_promoted",
    "not_os_isolation_proof",
    "operator_managed",
    "local_preview_only",
    "runtime changes allowed: `false`",
    "Mission Control runtime allowed: `false`",
    "local model invocation allowed: `false`",
    "sandbox orchestration allowed: `false`",
    "trusted-host promotion allowed: `false`",
    "network expansion allowed: `false`",
    "new power classes allowed: `false`",
    "EXT-SANDBOX-PREFLIGHT-###",
]

FORBIDDEN_CLAIMS = [
    "Ithildin starts the VM.",
    "Ithildin starts containers.",
    "Ithildin manages the VM.",
    "Ithildin manages containers.",
    "Mission Control executes actions.",
    "local model is invoked",
    "host promotion is implemented",
    "production-ready sandbox",
    "OS isolation is proven",
    "compliance automation is implemented",
    "broad network access is allowed",
    "Docker socket access is allowed",
    "Kubernetes control is allowed",
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

    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    rel_path = DOC.relative_to(repo_root).as_posix()
    if not DOC.exists():
        failures.append("sandbox/VM static profile preflight plan is missing")
        text = ""
    else:
        text = DOC.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"sandbox/VM static profile preflight plan is missing phrase: {phrase}")
    for claim in FORBIDDEN_CLAIMS:
        if claim in text:
            failures.append(
                f"sandbox/VM static profile preflight plan contains forbidden overclaim: {claim}"
            )
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("sandbox/VM static profile preflight plan is missing from review docs")
    if rel_path not in docs_site:
        failures.append("sandbox/VM static profile preflight plan is missing from docs-site inputs")
    if "make sandbox-vm-static-profile-preflight-plan-check" not in readme:
        failures.append("README is missing sandbox/VM static profile preflight plan command")
    if "sandbox-vm-static-profile-preflight-plan-check:" not in makefile:
        failures.append("Make target is missing: sandbox-vm-static-profile-preflight-plan-check")
    if "sandbox-vm-static-profile-preflight-plan-check" not in release_check_body:
        failures.append(
            "sandbox/VM static profile preflight plan check is missing from release-check"
        )
    if "sandbox-vm-static-profile-preflight-plan.md" not in enterprise:
        failures.append("enterprise runway is missing static profile preflight plan pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "plan_doc": rel_path,
        "tool_count": tool_surface.get("tool_count"),
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static profile preflight plan check",
        f"valid: {str(report['valid']).lower()}",
        f"plan_doc: {report['plan_doc']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
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

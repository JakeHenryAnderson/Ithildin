"""Validate the sandbox/VM static profile fixture contract and example fixture."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, review_docs, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/sandbox-vm-static-profile-fixture-contract.md"
FIXTURE = ROOT / "docs/codex/fixtures/sandbox-vm-static-profile.local-preview.example.json"

TOP_LEVEL_KEYS = {
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
}

FALSE_AUTHORITY_FLAGS = {
    "ithildin_starts_vm",
    "ithildin_starts_container",
    "ithildin_has_docker_socket",
    "ithildin_has_kubernetes_control",
    "ithildin_runs_shell",
    "mission_control_executes_actions",
    "local_model_invoked",
    "trusted_host_promotion_enabled",
    "broad_network_access",
}

REQUIRED_WARNINGS = {
    "not_os_isolation_proof",
    "operator_managed",
    "local_preview_only",
}

REQUIRED_DOC_PHRASES = [
    "Status: fixture-contract only.",
    "Implementation state: fixture validation only.",
    "make sandbox-vm-static-profile-fixture-contract-check",
    "Required Fixture Sections",
    "Required False Authority Flags",
    "Safe Labels Only",
    "Supported Values",
    "Required Warning Labels",
    "Current Allowed State",
    "runtime changes allowed: `false`",
    "Mission Control runtime allowed: `false`",
    "local model invocation allowed: `false`",
    "sandbox orchestration allowed: `false`",
    "trusted-host promotion allowed: `false`",
    "network expansion allowed: `false`",
    "new power classes allowed: `false`",
]

FORBIDDEN_TEXT_PATTERNS = [
    re.compile(r"/Users/"),
    re.compile(r"/var/"),
    re.compile(r"/tmp/"),
    re.compile(r"~[/\\]"),
    re.compile(r"\b[A-Za-z]:\\\\"),
    re.compile(r"docker\.sock"),
    re.compile(r"kubeconfig", re.IGNORECASE),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"(?i)\b(secret|token|password|api_key)\s*[:=]\s*[^,\s]+"),
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

    doc_rel = DOC.relative_to(repo_root).as_posix()
    fixture_rel = FIXTURE.relative_to(repo_root).as_posix()
    doc_text = _read_text(DOC, failures, "sandbox/VM static profile fixture contract")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc_text:
            failures.append(f"sandbox/VM static profile fixture contract missing phrase: {phrase}")
    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("sandbox/VM static profile fixture contract is missing from review docs")
    if doc_rel not in docs_site:
        failures.append(
            "sandbox/VM static profile fixture contract is missing from docs-site inputs"
        )
    if fixture_rel not in docs_site:
        failures.append(
            "sandbox/VM static profile example fixture is missing from docs-site inputs"
        )
    if "make sandbox-vm-static-profile-fixture-contract-check" not in readme:
        failures.append("README is missing sandbox/VM static profile fixture contract command")
    if "sandbox-vm-static-profile-fixture-contract-check:" not in makefile:
        failures.append("Make target is missing: sandbox-vm-static-profile-fixture-contract-check")
    if "sandbox-vm-static-profile-fixture-contract-check" not in release_check_body:
        failures.append(
            "sandbox/VM static profile fixture contract check is missing from release-check"
        )
    if "sandbox-vm-static-profile-fixture-contract.md" not in enterprise:
        failures.append("enterprise runway is missing static profile fixture contract pointer")

    fixture = _load_fixture(FIXTURE, failures)
    if fixture is not None:
        failures.extend(_validate_fixture(fixture))
        fixture_text = json.dumps(fixture, sort_keys=True)
        for pattern in FORBIDDEN_TEXT_PATTERNS:
            if pattern.search(fixture_text):
                failures.append(
                    "sandbox/VM static profile example fixture contains forbidden "
                    "sensitive pattern: "
                    f"{pattern.pattern}"
                )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "contract_doc": doc_rel,
        "example_fixture": fixture_rel,
        "tool_count": tool_surface.get("tool_count"),
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "new_power_classes_allowed": False,
    }


def _read_text(path: Path, failures: list[str], label: str) -> str:
    if not path.exists():
        failures.append(f"{label} is missing")
        return ""
    return path.read_text(encoding="utf-8")


def _load_fixture(path: Path, failures: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        failures.append("sandbox/VM static profile example fixture is missing")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"sandbox/VM static profile example fixture is invalid JSON: {exc}")
        return None
    if not isinstance(data, dict):
        failures.append("sandbox/VM static profile example fixture must be a JSON object")
        return None
    return data


def _validate_fixture(fixture: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    keys = set(fixture)
    missing = TOP_LEVEL_KEYS - keys
    unknown = keys - TOP_LEVEL_KEYS
    if missing:
        failures.append(f"sandbox/VM static profile fixture missing keys: {sorted(missing)}")
    if unknown:
        failures.append(f"sandbox/VM static profile fixture has unknown keys: {sorted(unknown)}")
    if fixture.get("schema_version") != "1":
        failures.append("sandbox/VM static profile fixture schema_version must be 1")
    if fixture.get("support_status") not in {
        "supported_local_preview",
        "unsupported",
        "review_required",
    }:
        failures.append("sandbox/VM static profile fixture support_status is unsupported")
    if fixture.get("support_status") == "supported_local_preview":
        failures.append(
            "example fixture must not claim supported_local_preview before implementation"
        )
    warnings = fixture.get("warnings")
    if not isinstance(warnings, list) or not REQUIRED_WARNINGS.issubset(set(warnings)):
        failures.append("sandbox/VM static profile fixture is missing required warning labels")
    decision = fixture.get("decision")
    if not isinstance(decision, dict):
        failures.append("sandbox/VM static profile fixture decision must be an object")
        return failures
    if decision.get("promotion_status") != "not_promoted":
        failures.append("sandbox/VM static profile fixture promotion_status must be not_promoted")
    if decision.get("decision") not in {"go", "no_go", "review_required"}:
        failures.append("sandbox/VM static profile fixture decision value is unsupported")
    if decision.get("decision") == "go":
        failures.append("example fixture must not produce go before preflight implementation")
    flags = decision.get("false_authority_flags")
    if not isinstance(flags, dict):
        failures.append("sandbox/VM static profile fixture false_authority_flags must be an object")
        return failures
    missing_flags = FALSE_AUTHORITY_FLAGS - set(flags)
    unknown_flags = set(flags) - FALSE_AUTHORITY_FLAGS
    if missing_flags:
        failures.append(
            "sandbox/VM static profile fixture missing false flags: "
            f"{sorted(missing_flags)}"
        )
    if unknown_flags:
        failures.append(
            "sandbox/VM static profile fixture has unknown false flags: "
            f"{sorted(unknown_flags)}"
        )
    for flag in FALSE_AUTHORITY_FLAGS:
        if flags.get(flag) is not False:
            failures.append(f"sandbox/VM static profile fixture flag must be false: {flag}")
    network = fixture.get("network")
    if not isinstance(network, dict):
        failures.append("sandbox/VM static profile fixture network must be an object")
    elif network.get("posture") not in {
        "offline",
        "operator_managed",
        "unknown",
        "review_required",
    }:
        failures.append("sandbox/VM static profile fixture network posture is unsupported")
    return failures


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static profile fixture contract check",
        f"valid: {str(report['valid']).lower()}",
        f"contract_doc: {report['contract_doc']}",
        f"example_fixture: {report['example_fixture']}",
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

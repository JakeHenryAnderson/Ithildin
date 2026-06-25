"""Validate sandbox/VM static profile negative fixture expectations."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    review_docs,
)
from scripts import (
    sandbox_vm_static_profile_fixture_contract_check as fixture_contract,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/sandbox-vm-static-profile-negative-fixtures.md"
FIXTURE = ROOT / "docs/codex/fixtures/sandbox-vm-static-profile.local-preview.example.json"

REQUIRED_PHRASES = [
    "Status: fixture-contract negative cases only.",
    "make sandbox-vm-static-profile-negative-fixtures-check",
    "Fixture Source",
    "Required Rejections",
    "Safe Error Expectations",
    "Current Implementation Boundary",
    "SANDBOX-PROFILE-NEG-001",
    "SANDBOX-PROFILE-NEG-018",
]

FORBIDDEN_DOC_PHRASES = [
    "production-ready",
    "compliance-grade audit",
    "tamper-proof audit",
    "secure sandbox",
    "safe arbitrary tool use",
    "Mission Control may execute",
    "Ithildin starts containers",
    "Ithildin starts the VM",
    "trusted-host promotion is implemented",
]

SAFE_REASON_PATTERN = re.compile(r"^[a-z0-9_]+$")
SENSITIVE_PATTERNS = [
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

Mutator = Callable[[dict[str, Any]], None]


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
    doc_rel = DOC.relative_to(ROOT).as_posix()
    makefile = repo_root.joinpath("Makefile").read_text(encoding="utf-8")
    readme = repo_root.joinpath("README.md").read_text(encoding="utf-8")
    docs_site = repo_root.joinpath("scripts/build_docs_site.py").read_text(encoding="utf-8")
    enterprise = repo_root.joinpath("docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    doc_text = _read_text(DOC, failures)
    for phrase in REQUIRED_PHRASES:
        if phrase not in doc_text:
            failures.append(f"sandbox/VM static profile negative fixtures missing: {phrase}")
    lowered = doc_text.lower()
    for phrase in FORBIDDEN_DOC_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"sandbox/VM negative fixture doc contains forbidden phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append(
            "sandbox/VM static profile negative fixture doc is missing from review docs"
        )
    if doc_rel not in docs_site:
        failures.append("sandbox/VM static profile negative fixture doc is missing from docs-site")
    if "make sandbox-vm-static-profile-negative-fixtures-check" not in readme:
        failures.append("README is missing sandbox/VM static profile negative fixture command")
    if "sandbox-vm-static-profile-negative-fixtures-check:" not in makefile:
        failures.append("Make target is missing: sandbox-vm-static-profile-negative-fixtures-check")
    if "sandbox-vm-static-profile-negative-fixtures-check" not in release_check_body:
        failures.append(
            "sandbox/VM static profile negative fixture check missing from release-check"
        )
    if "sandbox-vm-static-profile-negative-fixtures.md" not in enterprise:
        failures.append("enterprise runway is missing sandbox/VM static profile negative fixtures")

    seed = _load_fixture(FIXTURE, failures)
    positive_reasons = _validate_for_static_profile_preflight(seed) if seed is not None else []
    if positive_reasons:
        failures.append(f"positive static profile fixture failed validation: {positive_reasons}")

    case_results = _run_negative_cases(seed) if seed is not None else []
    for result in case_results:
        if result["accepted"]:
            failures.append(f"negative static profile fixture was accepted: {result['id']}")
        if not result["reasons"]:
            failures.append(
                f"negative static profile fixture returned no safe reason: {result['id']}"
            )
        for reason in result["reasons"]:
            if not SAFE_REASON_PATTERN.match(reason):
                failures.append(
                    f"negative fixture reason is not a safe label: {result['id']}:{reason}"
                )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "fixture_doc": doc_rel,
        "negative_case_count": len(case_results),
        "negative_cases_rejected": sum(1 for result in case_results if not result["accepted"]),
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "new_power_classes_allowed": False,
        "cases": case_results,
    }


def _read_text(path: Path, failures: list[str]) -> str:
    if not path.exists():
        failures.append("sandbox/VM static profile negative fixture doc is missing")
        return ""
    return path.read_text(encoding="utf-8")


def _load_fixture(path: Path, failures: list[str]) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        failures.append(f"static profile seed fixture could not be loaded: {exc}")
        return None
    if not isinstance(data, dict):
        failures.append("static profile seed fixture must be an object")
        return None
    return data


def _run_negative_cases(seed: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[tuple[str, str, Mutator]] = [
        ("SANDBOX-PROFILE-NEG-001", "missing_schema_version", _pop_key("schema_version")),
        ("SANDBOX-PROFILE-NEG-002", "unsupported_schema_version", _set("schema_version", "999")),
        ("SANDBOX-PROFILE-NEG-003", "unknown_top_level", _set("runtime_authority", True)),
        (
            "SANDBOX-PROFILE-NEG-004",
            "missing_warning",
            _remove_warning("not_os_isolation_proof"),
        ),
        (
            "SANDBOX-PROFILE-NEG-005",
            "support_overclaim",
            _set("support_status", "supported_local_preview"),
        ),
        (
            "SANDBOX-PROFILE-NEG-006",
            "raw_mount_path",
            _set_nested(("mounts", "root_label"), "/Users/demo/workspace"),
        ),
        (
            "SANDBOX-PROFILE-NEG-007",
            "broad_network_access",
            _set_nested(("network", "broad_network_access"), True),
        ),
        (
            "SANDBOX-PROFILE-NEG-008",
            "promotion_overclaim",
            _set_nested(("decision", "promotion_status"), "promoted"),
        ),
        (
            "SANDBOX-PROFILE-NEG-009",
            "go_overclaim",
            _set_nested(("decision", "decision"), "go"),
        ),
        (
            "SANDBOX-PROFILE-NEG-010",
            "vm_lifecycle_overclaim",
            _set_false_flag("ithildin_starts_vm", True),
        ),
        (
            "SANDBOX-PROFILE-NEG-011",
            "docker_authority_overclaim",
            _set_false_flag("ithildin_has_docker_socket", True),
        ),
        (
            "SANDBOX-PROFILE-NEG-012",
            "kubernetes_authority_overclaim",
            _set_false_flag("ithildin_has_kubernetes_control", True),
        ),
        (
            "SANDBOX-PROFILE-NEG-013",
            "shell_authority_overclaim",
            _set_false_flag("ithildin_runs_shell", True),
        ),
        (
            "SANDBOX-PROFILE-NEG-014",
            "mission_control_authority_overclaim",
            _set_false_flag("mission_control_executes_actions", True),
        ),
        (
            "SANDBOX-PROFILE-NEG-015",
            "local_model_overclaim",
            _set_false_flag("local_model_invoked", True),
        ),
        (
            "SANDBOX-PROFILE-NEG-016",
            "trusted_host_promotion_overclaim",
            _set_false_flag("trusted_host_promotion_enabled", True),
        ),
        (
            "SANDBOX-PROFILE-NEG-017",
            "unsupported_network_posture",
            _set_nested(("network", "posture"), "unrestricted"),
        ),
        (
            "SANDBOX-PROFILE-NEG-018",
            "secret_like_field",
            _set("token", "redacted-fixture-token"),
        ),
    ]
    results: list[dict[str, Any]] = []
    for case_id, label, mutator in cases:
        payload = copy.deepcopy(seed)
        mutator(payload)
        reasons = _validate_for_static_profile_preflight(payload)
        results.append(
            {
                "id": case_id,
                "label": label,
                "accepted": not reasons,
                "reasons": reasons,
            }
        )
    return results


def _validate_for_static_profile_preflight(payload: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not isinstance(payload, dict):
        return ["not_object"]
    contract_reasons = fixture_contract._validate_fixture(dict(payload))  # noqa: SLF001
    reasons.extend(_to_reason_label(reason) for reason in contract_reasons)
    if _contains_sensitive_pattern(payload):
        reasons.append("sensitive_payload_shape")
    network = payload.get("network")
    if isinstance(network, Mapping) and network.get("broad_network_access") is not False:
        reasons.append("broad_network_overclaim")
    return sorted(set(reasons))


def _contains_sensitive_pattern(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _sensitive_key(str(key)) or _contains_sensitive_pattern(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_pattern(child) for child in value)
    if isinstance(value, str):
        return any(pattern.search(value) for pattern in SENSITIVE_PATTERNS)
    return False


def _sensitive_key(key: str) -> bool:
    return key.lower() in {
        "secret",
        "secrets",
        "token",
        "tokens",
        "password",
        "api_key",
        "private_key",
        "raw_prompt",
        "file_contents",
    }


def _to_reason_label(reason: str) -> str:
    lowered = reason.lower()
    if "schema_version" in lowered:
        return "unsupported_schema"
    if "unknown keys" in lowered:
        return "closed_schema_violation"
    if "warning" in lowered:
        return "missing_warning_state"
    if "supported_local_preview" in lowered:
        return "support_overclaim"
    if "promotion_status" in lowered:
        return "promotion_overclaim"
    if "decision" in lowered:
        return "readiness_overclaim"
    if "flag must be false" in lowered:
        return "authority_overclaim"
    if "network" in lowered:
        return "unsupported_network_posture"
    return "invalid_static_profile"


def _pop_key(key: str) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload.pop(key, None)

    return mutate


def _set(key: str, value: Any) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload[key] = value

    return mutate


def _set_nested(path: tuple[str, ...], value: Any) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        current: dict[str, Any] = payload
        for key in path[:-1]:
            child = current.setdefault(key, {})
            if not isinstance(child, dict):
                child = {}
                current[key] = child
            current = child
        current[path[-1]] = value

    return mutate


def _set_false_flag(flag: str, value: bool) -> Mutator:
    return _set_nested(("decision", "false_authority_flags", flag), value)


def _remove_warning(warning: str) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        warnings = payload.get("warnings")
        if isinstance(warnings, list):
            payload["warnings"] = [item for item in warnings if item != warning]

    return mutate


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static profile negative fixtures check",
        f"valid: {str(report['valid']).lower()}",
        f"fixture_doc: {report['fixture_doc']}",
        f"negative_case_count: {report['negative_case_count']}",
        f"negative_cases_rejected: {report['negative_cases_rejected']}",
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

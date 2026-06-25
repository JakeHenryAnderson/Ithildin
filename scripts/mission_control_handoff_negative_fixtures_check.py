"""Validate negative fixture expectations for Mission Control handoff payloads."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import hello_world_mission_control_handoff, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/mission-control-handoff-negative-fixtures.md"

REQUIRED_PHRASES = [
    "Status: design-only negative fixture plan",
    "make mission-control-handoff-negative-fixtures-check",
    "Fixture Source",
    "Required Rejections",
    "Safe Error Expectations",
    "Current Implementation Boundary",
    "MC-HANDOFF-NEG-001",
    "MC-HANDOFF-NEG-014",
]

FORBIDDEN_DOC_PHRASES = [
    "production-ready",
    "compliance-grade audit",
    "tamper-proof audit",
    "secure sandbox",
    "safe arbitrary tool use",
    "Mission Control may execute",
    "Mission Control may approve",
    "trusted-host promotion is implemented",
]

FALSE_FIELDS = [
    "mission_control_runtime_behavior",
    "local_llm_runtime_behavior",
    "real_vm_or_container_started",
    "sandbox_orchestration_performed",
    "shell_execution_performed",
    "host_promotion_performed",
]

REQUIRED_WARNING_CHIPS = {
    "local_preview_only",
    "mission_control_metadata_only",
    "local_llm_not_invoked",
    "vm_not_started",
    "host_promotion_not_performed",
}

REQUIRED_HIDE_FIELDS = {
    "file_contents",
    "raw_host_paths",
    "raw_model_prompt",
    "chain_of_thought",
    "private_keys",
    "tokens",
    "environment_values",
}

FORBIDDEN_PAYLOAD_KEYS = {
    "file_contents",
    "raw_prompt",
    "raw_model_prompt",
    "chain_of_thought",
    "private_key",
    "private_keys",
    "token",
    "tokens",
    "environment_values",
    "response_body",
}

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
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    v1_packet = (repo_root / "scripts/v1_rc_packet.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("Mission Control handoff negative fixture plan is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"negative fixture plan is missing phrase: {phrase}")
        for phrase in FORBIDDEN_DOC_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"negative fixture plan contains forbidden phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("Mission Control negative fixture plan is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("Mission Control negative fixture plan is missing from docs-site inputs")
    if doc_rel not in v1_packet:
        failures.append("Mission Control negative fixture plan is missing from v1 RC packet")
    if "mission-control-handoff-negative-fixtures-check:" not in makefile:
        failures.append("Make target is missing: mission-control-handoff-negative-fixtures-check")
    if "mission-control-handoff-negative-fixtures-check" not in release_check_body:
        failures.append(
            "mission-control-handoff-negative-fixtures-check missing from release-check"
        )
    if "make mission-control-handoff-negative-fixtures-check" not in readme:
        failures.append("README is missing Mission Control negative fixture command")

    seed = _build_seed_payload()
    seed_reasons = _validate_for_display_import(seed)
    if seed_reasons:
        failures.append(f"positive seed payload failed validation: {seed_reasons}")

    case_results = _run_negative_cases(seed)
    for result in case_results:
        if result["accepted"]:
            failures.append(f"negative fixture was accepted: {result['id']}")
        if not result["reasons"]:
            failures.append(f"negative fixture returned no safe reason: {result['id']}")

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
        "new_power_classes_allowed": False,
        "cases": case_results,
    }


def _build_seed_payload() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "mission-control-handoff"
        hello_world_mission_control_handoff.build_handoff(output_dir)
        return cast(
            dict[str, Any],
            json.loads(
                output_dir.joinpath(hello_world_mission_control_handoff.JSON_NAME).read_text(
                    encoding="utf-8"
                )
            ),
        )


def _run_negative_cases(seed: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[tuple[str, str, Mutator]] = [
        ("MC-HANDOFF-NEG-001", "missing_schema_version", _pop_key("schema_version")),
        ("MC-HANDOFF-NEG-002", "unsupported_schema_version", _set("schema_version", "999")),
        ("MC-HANDOFF-NEG-003", "live_status_claim", _set("status", "live_integration")),
        (
            "MC-HANDOFF-NEG-004",
            "mission_control_runtime_true",
            _set("mission_control_runtime_behavior", True),
        ),
        ("MC-HANDOFF-NEG-005", "host_promotion_true", _set("host_promotion_performed", True)),
        (
            "MC-HANDOFF-NEG-006",
            "policy_authority_false",
            _set("ithildin_remains_policy_authority", False),
        ),
        ("MC-HANDOFF-NEG-007", "absolute_attachment_path", _set_attachment_path("/tmp/secret")),
        ("MC-HANDOFF-NEG-008", "parent_attachment_path", _set_attachment_path("../secret")),
        ("MC-HANDOFF-NEG-009", "missing_display_contract", _pop_key("display_contract")),
        ("MC-HANDOFF-NEG-010", "missing_token_hide_field", _remove_hide_field("tokens")),
        (
            "MC-HANDOFF-NEG-011",
            "missing_host_promotion_warning",
            _remove_warning_chip("host_promotion_not_performed"),
        ),
        (
            "MC-HANDOFF-NEG-012",
            "executor_authority_claim",
            _set("mission_control_authority", "executor_authority"),
        ),
        ("MC-HANDOFF-NEG-013", "raw_file_contents", _inject("file_contents", "hello")),
        ("MC-HANDOFF-NEG-014", "raw_prompt", _inject("raw_prompt", "summarize this")),
    ]
    results: list[dict[str, Any]] = []
    for case_id, label, mutator in cases:
        payload = copy.deepcopy(seed)
        mutator(payload)
        reasons = _validate_for_display_import(payload)
        results.append(
            {
                "id": case_id,
                "label": label,
                "accepted": not reasons,
                "reasons": reasons,
            }
        )
    return results


def _validate_for_display_import(payload: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if payload.get("schema_version") != "1":
        reasons.append("unsupported_schema")
    if payload.get("status") != "metadata_only":
        reasons.append("not_metadata_only")
    if payload.get("mission_control_authority") != "display_and_operator_review_only":
        reasons.append("authority_overclaim")
    if payload.get("ithildin_remains_policy_authority") is not True:
        reasons.append("policy_authority_drift")
    for field in FALSE_FIELDS:
        if payload.get(field) is not False:
            reasons.append(f"{field}_overclaim")

    display_contract = payload.get("display_contract")
    if not isinstance(display_contract, Mapping):
        reasons.append("missing_display_contract")
    else:
        warning_chips = _string_set(display_contract.get("warning_chips"))
        hide_fields = _string_set(display_contract.get("hide_fields"))
        if not REQUIRED_WARNING_CHIPS.issubset(warning_chips):
            reasons.append("missing_warning_chips")
        if not REQUIRED_HIDE_FIELDS.issubset(hide_fields):
            reasons.append("missing_hidden_field_denylist")

    attachments = payload.get("attachments")
    if not isinstance(attachments, list) or not attachments:
        reasons.append("missing_attachments")
    else:
        for attachment in attachments:
            if not isinstance(attachment, Mapping):
                reasons.append("invalid_attachment")
                continue
            path = attachment.get("path")
            if not isinstance(path, str) or not path:
                reasons.append("invalid_attachment_path")
                continue
            parsed = Path(path)
            if parsed.is_absolute() or ".." in parsed.parts:
                reasons.append("unsafe_attachment_path")

    if _contains_forbidden_key(payload):
        reasons.append("forbidden_payload_field")
    return sorted(set(reasons))


def _string_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str) and key in FORBIDDEN_PAYLOAD_KEYS:
                return True
            if _contains_forbidden_key(child):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _set(key: str, value: Any) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload[key] = value

    return mutate


def _pop_key(key: str) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload.pop(key)

    return mutate


def _inject(key: str, value: Any) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload.setdefault("unsafe_debug", {})[key] = value

    return mutate


def _set_attachment_path(path: str) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload["attachments"][0]["path"] = path

    return mutate


def _remove_hide_field(field: str) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload["display_contract"]["hide_fields"].remove(field)

    return mutate


def _remove_warning_chip(chip: str) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload["display_contract"]["warning_chips"].remove(chip)

    return mutate


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control handoff negative fixtures check",
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
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate the Mission Control handoff schema contract and current seed payload."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import hello_world_mission_control_handoff, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/mission-control-handoff-schema-contract.md"

REQUIRED_PHRASES = [
    "Status: design-only Ithildin-side schema contract",
    "mission-control-handoff.json",
    "Contract Purpose",
    "Top-Level Required Fields",
    "Display Allowlist",
    "Hidden-Field Denylist",
    "Attachment Rules",
    "Negative Cases",
    "Current Implementation Boundary",
    "Runtime implementation remains",
]

REQUIRED_FALSE_FIELDS = [
    "mission_control_runtime_behavior",
    "local_llm_runtime_behavior",
    "real_vm_or_container_started",
    "sandbox_orchestration_performed",
    "shell_execution_performed",
    "host_promotion_performed",
]

REQUIRED_DISPLAY_FIELDS = [
    "mission_id",
    "operator_intent_label",
    "model_client_label",
    "tool_name",
    "request_status",
    "approval_status",
    "execution_status",
    "artifact_label",
    "artifact_content_sha256",
    "audit_valid",
    "audit_head_hash",
    "promotion_status",
]

REQUIRED_WARNING_CHIPS = [
    "local_preview_only",
    "mission_control_metadata_only",
    "local_llm_not_invoked",
    "vm_not_started",
    "host_promotion_not_performed",
]

REQUIRED_HIDE_FIELDS = [
    "file_contents",
    "raw_host_paths",
    "raw_model_prompt",
    "chain_of_thought",
    "private_keys",
    "tokens",
    "environment_values",
]

FORBIDDEN_PHRASES = [
    "production-ready",
    "compliance-grade audit",
    "tamper-proof audit",
    "secure sandbox",
    "safe arbitrary tool use",
    "Mission Control may execute",
    "Mission Control may approve",
    "trusted-host promotion is implemented",
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
    doc_rel = DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    v1_packet = (repo_root / "scripts/v1_rc_packet.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("Mission Control handoff schema contract is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"schema contract is missing phrase: {phrase}")
        for field in REQUIRED_FALSE_FIELDS:
            if f"`{field}`" not in text:
                failures.append(f"schema contract is missing required false field: {field}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"schema contract contains forbidden phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("Mission Control handoff schema contract is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("Mission Control handoff schema contract is missing from docs-site inputs")
    if doc_rel not in v1_packet:
        failures.append("Mission Control handoff schema contract is missing from v1 RC packet")
    if "mission-control-handoff-schema-contract-check:" not in makefile:
        failures.append("Make target is missing: mission-control-handoff-schema-contract-check")
    if "mission-control-handoff-schema-contract-check" not in release_check_body:
        failures.append("mission-control-handoff-schema-contract-check missing from release-check")
    if "make mission-control-handoff-schema-contract-check" not in readme:
        failures.append("README is missing Mission Control handoff schema command")

    try:
        payload = _build_seed_payload()
        _validate_seed_payload(payload, failures)
    except Exception as exc:  # pragma: no cover - defensive report path
        failures.append(f"failed to build or validate seed payload: {exc}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "contract_doc": doc_rel,
        "seed_payload": "mission-control-handoff.json",
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "mission_control_execution_allowed": False,
        "mission_control_policy_authority_allowed": False,
        "mission_control_approval_authority_allowed": False,
        "mission_control_audit_authority_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "new_power_classes_allowed": False,
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
            )
        )


def _validate_seed_payload(payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("schema_version") != "1":
        failures.append("seed payload schema_version is not 1")
    if payload.get("status") != "metadata_only":
        failures.append("seed payload status is not metadata_only")
    if payload.get("mission_control_authority") != "display_and_operator_review_only":
        failures.append("seed payload Mission Control authority is not display-only")
    if payload.get("ithildin_remains_policy_authority") is not True:
        failures.append("seed payload does not preserve Ithildin policy authority")
    for field in REQUIRED_FALSE_FIELDS:
        if payload.get(field) is not False:
            failures.append(f"seed payload field must be false: {field}")

    display_contract = payload.get("display_contract")
    if not isinstance(display_contract, dict):
        failures.append("seed payload display_contract is missing")
        return

    _require_subset(
        "display_contract.show_fields",
        REQUIRED_DISPLAY_FIELDS,
        display_contract.get("show_fields"),
        failures,
    )
    _require_subset(
        "display_contract.warning_chips",
        REQUIRED_WARNING_CHIPS,
        display_contract.get("warning_chips"),
        failures,
    )
    _require_subset(
        "display_contract.hide_fields",
        REQUIRED_HIDE_FIELDS,
        display_contract.get("hide_fields"),
        failures,
    )

    boundaries = payload.get("boundaries")
    if not isinstance(boundaries, dict):
        failures.append("seed payload boundaries are missing")
    else:
        for field in [
            "mission_control_must_not_claim_execution",
            "mission_control_must_not_claim_policy_authority",
            "mission_control_must_not_claim_vm_or_sandbox_control",
            "mission_control_must_not_claim_host_promotion",
            "no_file_contents",
            "no_raw_host_paths",
            "local_preview_only",
        ]:
            if boundaries.get(field) is not True:
                failures.append(f"seed payload boundary flag must be true: {field}")

    attachments = payload.get("attachments")
    if not isinstance(attachments, list) or not attachments:
        failures.append("seed payload attachments are missing")
    else:
        for index, attachment in enumerate(attachments):
            if not isinstance(attachment, dict):
                failures.append(f"seed payload attachment {index} is not an object")
                continue
            path = attachment.get("path")
            if not isinstance(path, str) or not path:
                failures.append(f"seed payload attachment {index} has invalid path")
                continue
            attachment_path = Path(path)
            if attachment_path.is_absolute():
                failures.append(f"seed payload attachment {index} path is absolute")
            if ".." in attachment_path.parts:
                failures.append(f"seed payload attachment {index} path traverses upward")


def _require_subset(
    label: str,
    required: list[str],
    actual: Any,
    failures: list[str],
) -> None:
    if not isinstance(actual, list):
        failures.append(f"seed payload {label} is not a list")
        return
    actual_set = set(actual)
    for item in required:
        if item not in actual_set:
            failures.append(f"seed payload {label} is missing: {item}")


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control handoff schema contract check",
        f"valid: {str(report['valid']).lower()}",
        f"contract_doc: {report['contract_doc']}",
        f"seed_payload: {report['seed_payload']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_execution_allowed: "
        f"{str(report['mission_control_execution_allowed']).lower()}",
        "mission_control_policy_authority_allowed: "
        f"{str(report['mission_control_policy_authority_allowed']).lower()}",
        "mission_control_approval_authority_allowed: "
        f"{str(report['mission_control_approval_authority_allowed']).lower()}",
        "mission_control_audit_authority_allowed: "
        f"{str(report['mission_control_audit_authority_allowed']).lower()}",
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

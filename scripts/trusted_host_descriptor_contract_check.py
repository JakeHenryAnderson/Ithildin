"""Validate the ERG-005 trusted host descriptor contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/trusted-host-descriptor-contract.md"
DOC_NAME = "trusted-host-descriptor-contract.md"

REQUIRED_PHRASES = [
    "Status: design-only descriptor contract for `ERG-005` and `PRD-TRUSTED-HOST-001`.",
    "Current governed tool count: `24`.",
    "Current `ERG-005` status: `blocked`.",
    "Current selected capability: `not selected`.",
    "make trusted-host-descriptor-contract-check",
    "Descriptor Meaning",
    "Required Descriptor Fields",
    "Forbidden Descriptor Fields",
    "Accepted Descriptor Fixture",
    "Rejected Descriptor Fixture",
    "Relationship To ERG-004",
    "trusted-host-promotion-zone-contract.md",
    "trusted-host-promotion-implementation-plan.md",
    "operator-reviewed local evidence record",
    "planning input for later review packets",
    "the host is secure",
    "Ithildin may control the host",
    "Ithildin may write to host-managed locations",
    "Mission Control may act as a runtime authority",
    "schema_version",
    "descriptor_id",
    "host_label",
    "operator_reviewed",
    "review_status",
    "support_status",
    "os_family",
    "architecture",
    "filesystem_profile",
    "workspace_posture",
    "warning_state",
    "evidence_timestamp",
    "source",
    "supported_local_preview",
    "unsupported_untested",
    "operator_review_required",
    "operator_reviewed_for_planning",
    "secrets, tokens, private keys, credentials",
    "raw environment variables",
    "raw host paths",
    "process lists",
    "network interface details",
    "descriptor-only warning state",
    "decision record required: `true`",
    "implementation approved: `false`",
    "runtime changes allowed: `false`",
    "trusted-host promotion allowed: `false`",
    "direct host writes allowed: `false`",
    "host registry mutation allowed: `false`",
    "automatic host enrollment allowed: `false`",
    "VM/container lifecycle allowed: `false`",
    "Mission Control runtime allowed: `false`",
    "local model invocation allowed: `false`",
    "sandbox orchestration allowed: `false`",
    "SIEM adapter allowed: `false`",
    "new power classes allowed: `false`",
    "public/security-product positioning allowed: `false`",
]

FORBIDDEN_PHRASES = [
    "trusted-host promotion is implemented",
    "trusted-host promotion is approved",
    "host writes are approved",
    "host registry mutation is approved",
    "automatic host enrollment is approved",
    "VM/container lifecycle is approved",
    "Mission Control runtime is approved",
    "secure sandbox",
    "production-ready",
    "compliance-grade",
]

REQUIRED_FIELDS = {
    "schema_version",
    "descriptor_id",
    "host_label",
    "operator_reviewed",
    "review_status",
    "support_status",
    "os_family",
    "architecture",
    "filesystem_profile",
    "workspace_posture",
    "warning_state",
    "evidence_timestamp",
    "source",
}

FORBIDDEN_KEYS = {
    "secret",
    "secrets",
    "token",
    "tokens",
    "private_key",
    "credential",
    "credentials",
    "environment",
    "environment_variables",
    "env",
    "env_vars",
    "username",
    "home_directory",
    "raw_host_path",
    "raw_host_paths",
    "raw_sandbox_path",
    "process_list",
    "processes",
    "network_interfaces",
    "ip_addresses",
    "hostname",
    "shell_output",
    "vm_logs",
    "file_contents",
    "diff",
    "response_body",
    "model_output",
    "dependency_names",
    "package_scripts",
    "registry_urls",
    "database_dsn",
}

SUPPORTED_OS = {"macos", "linux", "windows", "wsl", "unknown"}
SUPPORTED_SUPPORT_STATUS = {
    "supported_local_preview",
    "unsupported_untested",
    "operator_review_required",
}
SUPPORTED_REVIEW_STATUS = {
    "operator_review_required",
    "operator_reviewed_for_planning",
    "rejected",
}


def _accepted_fixture() -> dict[str, Any]:
    return {
        "schema_version": "1",
        "descriptor_id": "thd_local_preview_macos_example",
        "host_label": "local-preview-host",
        "operator_reviewed": True,
        "review_status": "operator_review_required",
        "support_status": "supported_local_preview",
        "os_family": "macos",
        "architecture": "arm64",
        "filesystem_profile": {
            "case_sensitivity": "case_insensitive",
            "nofollow_supported": True,
            "symlink_supported": True,
            "hardlink_supported": True,
        },
        "workspace_posture": {
            "workspace_id": "demo_workspace",
            "mount_root_label": "workspace://demo",
            "sandbox_id": "sandbox_descriptor_only",
            "sandbox_runtime_control": False,
            "host_write_allowed": False,
        },
        "warning_state": {
            "warnings": ["descriptor_only"],
            "operator_notes_present": True,
        },
        "evidence_timestamp": "2026-07-04T00:00:00Z",
        "source": "operator-local-descriptor",
    }


def _rejected_fixture() -> dict[str, Any]:
    return {
        "schema_version": "1",
        "descriptor_id": "thd_bad_descriptor",
        "host_label": "bad-host",
        "operator_reviewed": True,
        "review_status": "operator_reviewed_for_planning",
        "support_status": "supported_local_preview",
        "os_family": "macos",
        "architecture": "arm64",
        "filesystem_profile": {"nofollow_supported": True},
        "workspace_posture": {
            "workspace_id": "demo_workspace",
            "mount_root_label": "workspace://demo",
            "sandbox_runtime_control": True,
            "host_write_allowed": True,
            "raw_host_path": "/Users/demo/Approved",
        },
        "warning_state": {"warnings": []},
        "environment_variables": {"SECRET_TOKEN": "redacted"},
        "process_list": ["launchd", "agent"],
        "network_interfaces": ["en0"],
        "evidence_timestamp": "2026-07-04T00:00:00Z",
        "source": "operator-local-descriptor",
    }


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_guardrails = (repo_root / "scripts/release_guardrails.py").read_text(
        encoding="utf-8"
    )
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    runway = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    decision_register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(
        encoding="utf-8"
    )
    zone_contract = (repo_root / "docs/codex/trusted-host-promotion-zone-contract.md").read_text(
        encoding="utf-8"
    )
    implementation_plan = (
        repo_root / "docs/codex/trusted-host-promotion-implementation-plan.md"
    ).read_text(encoding="utf-8")
    source_review = (repo_root / "docs/codex/trusted-host-promotion-source-review.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("trusted host descriptor contract doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"trusted host descriptor contract missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    f"trusted host descriptor contract contains forbidden phrase: {phrase}"
                )

    accepted_valid = _validate_descriptor(_accepted_fixture()) == []
    rejected_errors = _validate_descriptor(_rejected_fixture())
    if not accepted_valid:
        failures.append("accepted trusted host descriptor fixture did not validate")
    if not rejected_errors:
        failures.append("rejected trusted host descriptor fixture was accepted")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("trusted host descriptor contract missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("trusted host descriptor contract missing from docs-site inputs")
    if DOC_NAME not in readme:
        failures.append("README is missing trusted host descriptor contract doc")
    if "make trusted-host-descriptor-contract-check" not in readme:
        failures.append("README is missing trusted host descriptor contract command")
    if "trusted-host-descriptor-contract-check:" not in makefile:
        failures.append("Make target is missing: trusted-host-descriptor-contract-check")
    if "trusted-host-descriptor-contract-check" not in release_check_body:
        failures.append("trusted host descriptor contract check missing from release-check")
    if "trusted-host-descriptor-contract-check" not in release_guardrails:
        failures.append("release guardrails do not require trusted host descriptor contract")
    if "Trusted Host Descriptor Contract" not in review_index:
        failures.append("review docs index is missing trusted host descriptor contract entry")
    for text_name, source_text in [
        ("enterprise runway", runway),
        ("enterprise gap matrix", gap_matrix),
        ("post-RC decision register", decision_register),
        ("trusted-host zone contract", zone_contract),
        ("trusted-host implementation plan", implementation_plan),
        ("trusted-host source review", source_review),
    ]:
        if DOC_NAME not in source_text:
            failures.append(f"{text_name} is missing trusted host descriptor contract pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "descriptor_contract_doc": DOC_REL,
        "tool_count": 24,
        "erg_005_status": "blocked",
        "prd_id": "PRD-TRUSTED-HOST-001",
        "accepted_fixture_valid": accepted_valid,
        "rejected_fixture_rejected": bool(rejected_errors),
        "required_field_count": len(REQUIRED_FIELDS),
        "forbidden_key_count": len(FORBIDDEN_KEYS),
        "decision_record_required": True,
        "implementation_approved": False,
        "runtime_changes_allowed": False,
        "trusted_host_promotion_allowed": False,
        "direct_host_writes_allowed": False,
        "host_registry_mutation_allowed": False,
        "automatic_host_enrollment_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def _validate_descriptor(descriptor: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(descriptor)
    if missing:
        errors.append("missing required fields: " + ", ".join(sorted(missing)))
    _find_forbidden_keys(descriptor, errors)
    if descriptor.get("schema_version") != "1":
        errors.append("schema_version must be 1")
    if descriptor.get("os_family") not in SUPPORTED_OS:
        errors.append("os_family has unsupported label")
    if descriptor.get("support_status") not in SUPPORTED_SUPPORT_STATUS:
        errors.append("support_status has unsupported label")
    if descriptor.get("review_status") not in SUPPORTED_REVIEW_STATUS:
        errors.append("review_status has unsupported label")
    workspace = descriptor.get("workspace_posture", {})
    if isinstance(workspace, dict):
        if workspace.get("host_write_allowed") is not False:
            errors.append("host_write_allowed must be false")
        if workspace.get("sandbox_runtime_control") is not False:
            errors.append("sandbox_runtime_control must be false")
        mount_label = workspace.get("mount_root_label", "")
        if isinstance(mount_label, str) and not mount_label.startswith("workspace://"):
            errors.append("mount_root_label must use workspace:// label")
    else:
        errors.append("workspace_posture must be an object")
    warnings = descriptor.get("warning_state", {})
    if isinstance(warnings, dict):
        warning_values = warnings.get("warnings", [])
        if "descriptor_only" not in warning_values:
            errors.append("warning_state must include descriptor_only")
    else:
        errors.append("warning_state must be an object")
    return errors


def _find_forbidden_keys(value: Any, errors: list[str], prefix: str = "") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_path = f"{prefix}.{key}" if prefix else key
            if key in FORBIDDEN_KEYS:
                errors.append(f"forbidden descriptor key: {key_path}")
            _find_forbidden_keys(nested, errors, key_path)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _find_forbidden_keys(nested, errors, f"{prefix}[{index}]")


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted host descriptor contract check",
        f"valid: {str(report['valid']).lower()}",
        f"descriptor_contract_doc: {report['descriptor_contract_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"prd_id: {report['prd_id']}",
        f"accepted_fixture_valid: {str(report['accepted_fixture_valid']).lower()}",
        f"rejected_fixture_rejected: {str(report['rejected_fixture_rejected']).lower()}",
        f"required_field_count: {report['required_field_count']}",
        f"forbidden_key_count: {report['forbidden_key_count']}",
        f"decision_record_required: {str(report['decision_record_required']).lower()}",
        f"implementation_approved: {str(report['implementation_approved']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "trusted_host_promotion_allowed: "
        f"{str(report['trusted_host_promotion_allowed']).lower()}",
        f"direct_host_writes_allowed: {str(report['direct_host_writes_allowed']).lower()}",
        "host_registry_mutation_allowed: "
        f"{str(report['host_registry_mutation_allowed']).lower()}",
        "automatic_host_enrollment_allowed: "
        f"{str(report['automatic_host_enrollment_allowed']).lower()}",
        "vm_container_lifecycle_allowed: "
        f"{str(report['vm_container_lifecycle_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("")
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


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


if __name__ == "__main__":
    raise SystemExit(main())

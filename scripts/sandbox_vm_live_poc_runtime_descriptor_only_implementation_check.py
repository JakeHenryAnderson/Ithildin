"""Validate the ERG-004 descriptor-only runtime implementation checkpoint."""

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
DOC_REL = "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-implementation.md"
DOC_TITLE = "Sandbox/VM Live POC Runtime Descriptor-Only Implementation"
TARGET = "sandbox-vm-live-poc-runtime-descriptor-only-implementation-check"

REQUIRED_DOC_PHRASES = [
    "Status: implemented bounded descriptor-only runtime slice for `ERG-004`.",
    "Current governed tool count: `24`.",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-check",
    "closed `SandboxDescriptorPayload` schema validation",
    "local SQLite-backed `sandbox_descriptors` record storage",
    "admin-protected `POST /sandbox-descriptors`",
    "admin-protected `GET /sandbox-descriptors`",
    "safe audit event metadata using `sandbox.descriptor.submitted`",
    "`descriptor_source: operator_supplied`",
    "`vm_lifecycle_source: operator_managed`",
    "`ithildin_live_inspection_performed: false`",
    "`ithildin_lifecycle_control_performed: false`",
    "`mission_control_runtime_authority_used: false`",
    "`trusted_host_promotion_performed: false`",
    "Rejected descriptors return a generic `invalid sandbox descriptor` error",
    "Before stronger claims or expanded ERG-004 behavior",
    "`EXT-LIVE-DESC-###`",
]

REQUIRED_SOURCE_PHRASES = {
    "apps/api/src/ithildin_api/sandbox_descriptors.py": [
        "class SandboxDescriptorPayload",
        "class SandboxDescriptorStore",
        "CREATE TABLE IF NOT EXISTS sandbox_descriptors",
        "def safe_audit_metadata",
        "no_live_vm_inspection",
        "no_lifecycle_control",
    ],
    "apps/api/src/ithildin_api/app.py": [
        "SandboxDescriptorStore",
        '"/sandbox-descriptors"',
        "AuditEventType.SANDBOX_DESCRIPTOR_SUBMITTED",
        '"invalid sandbox descriptor"',
        '"sandbox_descriptors"',
    ],
    "packages/schemas/src/ithildin_schemas/types.py": [
        'SANDBOX_DESCRIPTOR_SUBMITTED = "sandbox.descriptor.submitted"',
    ],
    "tests/test_api_service.py": [
        "test_sandbox_descriptor_endpoints_require_auth_and_store_safe_evidence",
        "test_sandbox_descriptor_denies_unsafe_inputs_safely",
        '"invalid sandbox descriptor"',
        "sandbox.descriptor.submitted",
    ],
}

FORBIDDEN_DOC_PHRASES = [
    "live VM/container inspection is approved",
    "VM/container lifecycle management is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "new governed tool powers are approved",
    "public security product approved",
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
    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not (repo_root / DOC_REL).exists():
        failures.append("descriptor-only runtime implementation doc is missing")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            failures.append(
                f"descriptor-only runtime implementation doc missing phrase: {phrase}"
            )
    lowered = doc.lower()
    for phrase in FORBIDDEN_DOC_PHRASES:
        if phrase.lower() in lowered:
            failures.append(
                "descriptor-only runtime implementation doc contains forbidden phrase: "
                + phrase
            )
    for rel_path, phrases in REQUIRED_SOURCE_PHRASES.items():
        text = _read(repo_root / rel_path)
        if not text:
            failures.append(f"required descriptor-only implementation source missing: {rel_path}")
            continue
        for phrase in phrases:
            if phrase not in text:
                failures.append(f"{rel_path} missing phrase: {phrase}")
    manifest_paths = sorted((repo_root / "tool-manifests").glob("*descriptor*.yaml"))
    if manifest_paths:
        failures.append(
            "descriptor-only runtime implementation must not add tool manifests: "
            + ", ".join(path.name for path in manifest_paths)
        )
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body and f"release-check: {TARGET}" not in makefile:
        failures.append("descriptor-only runtime implementation check missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require descriptor-only implementation check")
    if f"make {TARGET}" not in readme:
        failures.append("README missing descriptor-only implementation command")
    if DOC_REL not in readme:
        failures.append("README missing descriptor-only implementation doc")
    if DOC_REL not in docs_site:
        failures.append("descriptor-only implementation doc missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("descriptor-only implementation doc missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index missing descriptor-only implementation doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "implementation_doc": DOC_REL,
        "tool_count": 24,
        "runtime_descriptor_only_implemented": True,
        "descriptor_store_enabled": True,
        "admin_api_enabled": True,
        "audit_event_enabled": True,
        "mcp_tools_added": False,
        "governed_tools_added": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "host_writes_allowed": False,
        "network_expansion_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_004": False,
        "next_required_milestone": "descriptor_only_source_review_handoff",
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin ERG-004 descriptor-only runtime implementation check",
        f"valid: {str(report['valid']).lower()}",
        f"implementation_doc: {report['implementation_doc']}",
        f"tool_count: {report['tool_count']}",
        "runtime_descriptor_only_implemented: "
        f"{str(report['runtime_descriptor_only_implemented']).lower()}",
        f"descriptor_store_enabled: {str(report['descriptor_store_enabled']).lower()}",
        f"admin_api_enabled: {str(report['admin_api_enabled']).lower()}",
        f"audit_event_enabled: {str(report['audit_event_enabled']).lower()}",
        f"mcp_tools_added: {str(report['mcp_tools_added']).lower()}",
        f"governed_tools_added: {str(report['governed_tools_added']).lower()}",
        "live_vm_inspection_allowed: "
        f"{str(report['live_vm_inspection_allowed']).lower()}",
        "vm_container_lifecycle_allowed: "
        f"{str(report['vm_container_lifecycle_allowed']).lower()}",
        "sandbox_orchestration_allowed: "
        f"{str(report['sandbox_orchestration_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        "local_model_invocation_allowed: "
        f"{str(report['local_model_invocation_allowed']).lower()}",
        "trusted_host_promotion_allowed: "
        f"{str(report['trusted_host_promotion_allowed']).lower()}",
        f"host_writes_allowed: {str(report['host_writes_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
        f"next_required_milestone: {report['next_required_milestone']}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

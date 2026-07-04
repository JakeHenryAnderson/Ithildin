"""Validate the ERG-004 descriptor-only internal source review."""

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
DOC_REL = "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review.md"
DOC_TITLE = "Sandbox/VM Live POC Runtime Descriptor-Only Internal Source Review"
TARGET = "sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review-check"

REQUIRED_DOC_PHRASES = [
    "Status: internal source review completed for the implemented descriptor-only runtime slice.",
    "Current governed tool count: `24`.",
    "make sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review-check",
    "apps/api/src/ithildin_api/sandbox_descriptors.py",
    "apps/api/src/ithildin_api/app.py",
    "packages/schemas/src/ithildin_schemas/types.py",
    "tests/test_api_service.py",
    "SandboxDescriptorPayload",
    "SandboxDescriptorStore",
    "operator_attested_descriptor_only",
    "sandbox.descriptor.submitted",
    "test_sandbox_descriptor_endpoints_require_auth_and_store_safe_evidence",
    "test_sandbox_descriptor_denies_unsafe_inputs_safely",
    "Finding namespace: `EXT-LIVE-DESC-###`",
    "No `INT-LIVE-DESC-###` findings were opened in this pass.",
    "High-Review Addendum",
    "Reviewer label: `Codex high-effort internal source reviewer`.",
    "Finding namespace reserved for this addendum: `INT-HIGH-LIVE-DESC-###`.",
    "No `INT-HIGH-LIVE-DESC-###` findings were opened in this pass.",
    "make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check",
    "does not replace external/source disposition",
    "internally reviewed for continued local-preview development",
    "external/source disposition remains pending",
]

REQUIRED_SOURCE_PHRASES = {
    "apps/api/src/ithildin_api/sandbox_descriptors.py": [
        "class SandboxDescriptorPayload",
        "Literal[False]",
        "class SandboxDescriptorStore",
        "CREATE TABLE IF NOT EXISTS sandbox_descriptors",
        '"operator_attested_descriptor_only"',
        '"live_vm_inspection": False',
        '"no_live_vm_inspection": True',
        "def safe_audit_metadata",
    ],
    "apps/api/src/ithildin_api/app.py": [
        "@api.post(\"/sandbox-descriptors\"",
        "@api.get(\"/sandbox-descriptors\"",
        "Depends(require_admin_token)",
        "AuditEventType.SANDBOX_DESCRIPTOR_SUBMITTED",
        "invalid sandbox descriptor",
    ],
    "tests/test_api_service.py": [
        "test_sandbox_descriptor_endpoints_require_auth_and_store_safe_evidence",
        "test_sandbox_descriptor_denies_unsafe_inputs_safely",
        "sandbox.descriptor.submitted",
        "invalid sandbox descriptor",
    ],
}

FORBIDDEN_DOC_PHRASES = [
    "ERG-004 is closed",
    "externally closed",
    "live VM/container inspection is approved",
    "VM/container lifecycle management is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime authority is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "host writes are approved",
    "new governed tool powers are approved",
    "public security product approved",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    doc = _read(doc_path)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("descriptor-only internal source review doc is missing")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            failures.append(f"descriptor-only internal source review missing phrase: {phrase}")
    lowered = doc.lower()
    for phrase in FORBIDDEN_DOC_PHRASES:
        if phrase.lower() in lowered:
            failures.append(
                "descriptor-only internal source review contains forbidden phrase: "
                + phrase
            )
    for rel_path, phrases in REQUIRED_SOURCE_PHRASES.items():
        text = _read(repo_root / rel_path)
        if not text:
            failures.append(f"required descriptor-only source file missing: {rel_path}")
            continue
        for phrase in phrases:
            if phrase not in text:
                failures.append(f"{rel_path} missing phrase: {phrase}")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body and f"release-check: {TARGET}" not in makefile:
        failures.append("descriptor-only internal source review check missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require descriptor-only internal review check")
    if f"make {TARGET}" not in readme:
        failures.append("README missing descriptor-only internal review command")
    if DOC_REL not in readme:
        failures.append("README missing descriptor-only internal review doc")
    if DOC_REL not in docs_site:
        failures.append("descriptor-only internal review doc missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("descriptor-only internal review doc missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index missing descriptor-only internal review doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "internal_source_review_doc": DOC_REL,
        "tool_count": 24,
        "erg_004_status": "descriptor_only_runtime_implemented_internal_reviewed",
        "finding_namespace": "INT-LIVE-DESC-###",
        "blocking_findings_open": False,
        "descriptor_only_internal_review_complete": True,
        "high_review_addendum_recorded": True,
        "high_review_blocking_findings_open": False,
        "runtime_changes_allowed": False,
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
        "external_source_disposition_required": True,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin ERG-004 descriptor-only internal source review check",
        f"valid: {str(report['valid']).lower()}",
        f"internal_source_review_doc: {report['internal_source_review_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"blocking_findings_open: {str(report['blocking_findings_open']).lower()}",
        "descriptor_only_internal_review_complete: "
        f"{str(report['descriptor_only_internal_review_complete']).lower()}",
        "high_review_addendum_recorded: "
        f"{str(report['high_review_addendum_recorded']).lower()}",
        "high_review_blocking_findings_open: "
        f"{str(report['high_review_blocking_findings_open']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
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
        "external_source_disposition_required: "
        f"{str(report['external_source_disposition_required']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


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

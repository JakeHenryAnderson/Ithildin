"""Validate the ERG-004 descriptor-only external response intake template."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import external_response_normalize, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/"
    "sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake.md"
)
DOC_NAME = "sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake.md"
TARGET = "sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake-check"
AREA = "sandbox-vm-live-poc-runtime-descriptor-only"
NAMESPACE = "LIVE-DESC"

REQUIRED_PHRASES = [
    "Status: response-intake template for the implemented descriptor-only `ERG-004` runtime slice.",
    "Current governed tool count: `24`.",
    "descriptor_only_runtime_implemented_source_review_pending",
    "Current selected capability: `not selected`.",
    "Finding namespace: `EXT-LIVE-DESC-###`.",
    "Reviewed area for normalization: `sandbox-vm-live-poc-runtime-descriptor-only`.",
    "Required Disposition Answers",
    "Finding Extraction Table",
    "EXT-LIVE-DESC-###",
    "--area sandbox-vm-live-poc-runtime-descriptor-only",
    "--source-access packet-and-source",
    '--reviewed-packet-hash "sha256:<from generated ERG-004 inbox>"',
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox",
    "make enterprise-response-now",
    "mutates_findings: false",
    "closes_external_review: false",
    "can_close_source_rows: true",
    "Only a later committed triage/disposition update",
]

REQUIRED_QUESTIONS = [
    "Did the reviewer inspect the descriptor-only runtime source-review packet",
    "Does `SandboxDescriptorPayload` keep operator-attested descriptor fields bounded",
    "Does `SandboxDescriptorStore` preserve local SQLite descriptor evidence",
    "Are the admin-only descriptor submit/list/detail endpoints adequately authenticated",
    "Is `/system/status` descriptor evidence safe",
    "Is `sandbox.descriptor.submitted` audit metadata limited",
    "Are invalid descriptor safe-error and negative-path tests sufficient",
    "Are there any critical/high findings",
    "Can the descriptor-only runtime slice move",
    "Does the response avoid approving live VM/container inspection",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "local model invocation",
    "Mission Control runtime behavior",
    "trusted-host promotion",
    "host writes",
    "network expansion",
    "API/MCP profile loading",
    "SIEM adapter behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "shell/Docker/Kubernetes/browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "plugin SDK behavior",
    "compliance automation",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "ERG-004 is closed",
    "live VM control is approved",
    "VM/container lifecycle management is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "host writes are approved",
    "production-ready",
    "secure sandbox",
    "compliance-grade",
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
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    source_bundle_doc = _read(
        repo_root / "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle.md"
    )
    enterprise_next = _read(repo_root / "docs/codex/enterprise-operator-next-action.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    doc_path = repo_root / DOC_REL
    if not doc_path.exists():
        failures.append("descriptor-only external response intake doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"intake doc is missing phrase: {phrase}")
        for phrase in REQUIRED_QUESTIONS:
            if phrase not in text:
                failures.append(f"intake doc is missing disposition question: {phrase}")
        for phrase in REQUIRED_BLOCKED_BOUNDARIES:
            if phrase not in text:
                failures.append(f"intake doc is missing blocked boundary: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"intake doc contains forbidden phrase: {phrase}")

    if AREA not in external_response_normalize.AREA_NAMESPACES:
        failures.append("external response normalizer lacks descriptor-only ERG-004 area")
    elif external_response_normalize.AREA_NAMESPACES[AREA] != NAMESPACE:
        failures.append("external response normalizer uses wrong descriptor-only namespace")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("descriptor-only intake doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("descriptor-only intake doc is missing from docs-site inputs")
    if DOC_NAME not in review_index:
        failures.append("review-docs index is missing descriptor-only intake entry")
    if DOC_NAME not in source_bundle_doc:
        failures.append("source-review bundle doc does not point to descriptor-only intake")
    if DOC_NAME not in enterprise_next:
        failures.append("enterprise next-action doc is missing descriptor-only intake")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body and f"release-check: {TARGET}" not in makefile:
        failures.append(f"{TARGET} missing from release-check")
    if TARGET not in readme:
        failures.append("README is missing descriptor-only intake command")
    if DOC_REL not in readme:
        failures.append("README is missing descriptor-only intake doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "intake_doc": DOC_REL,
        "tool_count": 24,
        "area": AREA,
        "finding_namespace": "EXT-LIVE-DESC-###",
        "erg_004_status": "descriptor_only_runtime_implemented_source_review_pending",
        "mutates_findings": False,
        "closes_external_review": False,
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
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin ERG-004 descriptor-only external response intake check",
        f"valid: {str(report['valid']).lower()}",
        f"intake_doc: {report['intake_doc']}",
        f"tool_count: {report['tool_count']}",
        f"area: {report['area']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"mutates_findings: {str(report['mutates_findings']).lower()}",
        f"closes_external_review: {str(report['closes_external_review']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "vm_container_lifecycle_allowed: "
        f"{str(report['vm_container_lifecycle_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"host_writes_allowed: {str(report['host_writes_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate the committed ERG-003/ERG-002 external-response disposition record."""

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
DOC_REL = "docs/codex/enterprise-dual-response-disposition-record.md"
DOC_NAME = "enterprise-dual-response-disposition-record.md"
FINDING_REL = "docs/codex/findings/ext-mc-display-001-launch-bundle-artifact-coverage.md"

REQUIRED_PHRASES = [
    (
        "Status: committed disposition record for the received `ERG-003` and "
        "`ERG-002` external responses."
    ),
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "make enterprise-dual-response-disposition-record-check",
    "Reviewed commit: `6610ada5db26db095191aa838d97d37042a54d98`.",
    "var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md",
    "var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md",
    "var/review-runs/sandbox-vm-static-preflight/normalized-response.json",
    "var/review-runs/mission-control-display/normalized-response.json",
    "`closed_local_preview_static_preflight`",
    "`ready_for_design_only_decision_record`",
    "`EXT-MC-DISPLAY-001` remains open as a low advisory packet-coverage finding.",
    "This advisory does not block design-only continuation",
    "post-`ERG-003` live",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime importer behavior",
    "Mission Control execution authority",
    "Mission Control policy authority",
    "Mission Control approval authority",
    "Mission Control audit authority",
    "API callbacks",
    "polling or mutating Ithildin APIs",
    "local model invocation",
    "trusted-host promotion",
    "network expansion",
    "API/MCP profile loading",
    "SIEM adapter behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "compliance automation",
    "public/security-product positioning",
    "new governed tool powers",
]

FORBIDDEN_PHRASES = [
    "live VM/container inspection is approved",
    "VM/container lifecycle management is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime importer behavior is approved",
    "Mission Control execution authority is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "public security product approved",
    "new governed tool powers are approved",
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
    doc_path = repo_root / DOC_REL
    finding_path = repo_root / FINDING_REL
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    transition = _read(repo_root / "docs/codex/enterprise-transition-map.md")
    register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    text = _read(doc_path)
    if not text:
        failures.append("enterprise dual-response disposition record is missing")
    lowered = text.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"disposition record is missing phrase: {phrase}")
    for phrase in REQUIRED_BLOCKED_BOUNDARIES:
        if phrase not in text:
            failures.append(f"disposition record is missing blocked boundary: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"disposition record contains forbidden phrase: {phrase}")

    if not finding_path.exists():
        failures.append("EXT-MC-DISPLAY-001 finding record is missing")

    target = "enterprise-dual-response-disposition-record-check"
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in release_check_body:
        failures.append("enterprise dual-response disposition check missing from release-check")
    if target not in release_guardrails:
        failures.append("release guardrails do not require dual-response disposition check")
    if f"make {target}" not in readme:
        failures.append("README is missing dual-response disposition command")
    if DOC_REL not in readme:
        failures.append("README is missing dual-response disposition doc")
    if DOC_REL not in docs_site:
        failures.append("dual-response disposition doc is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("dual-response disposition doc is missing from review docs")
    if "Enterprise Dual Response Disposition Record" not in review_index:
        failures.append("review-docs index is missing dual-response disposition record")
    for label, source in [
        ("enterprise runway", runway),
        ("enterprise gap matrix", gap_matrix),
        ("enterprise external-review queue", queue),
        ("enterprise transition map", transition),
        ("post-RC decision register", register),
    ]:
        if DOC_NAME not in source:
            failures.append(f"{label} is missing {DOC_NAME}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "disposition_record_doc": DOC_REL,
        "tool_count": 24,
        "erg_003_status": "closed_local_preview_static_preflight",
        "erg_002_status": "ready_for_design_only_decision_record",
        "erg_002_open_advisory_finding": "EXT-MC-DISPLAY-001",
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise dual-response disposition record check",
        f"valid: {str(report['valid']).lower()}",
        f"disposition_record_doc: {report['disposition_record_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
        f"erg_002_status: {report['erg_002_status']}",
        f"erg_002_open_advisory_finding: {report['erg_002_open_advisory_finding']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

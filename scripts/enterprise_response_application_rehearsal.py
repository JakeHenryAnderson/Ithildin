"""Validate the active enterprise response application rehearsal."""

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
DOC_REL = "docs/codex/enterprise-response-application-rehearsal.md"
DOC_TITLE = "Enterprise Response Application Rehearsal"
NORMALIZED_RESPONSE_RELS = [
    "var/review-runs/sandbox-vm-static-preflight/normalized-response.json",
    "var/review-runs/mission-control-display/normalized-response.json",
    "var/review-runs/trusted-host-promotion/normalized-response.json",
    "var/review-runs/production-identity-storage/normalized-response.json",
    "var/review-runs/siem-export-adapter/normalized-response.json",
    "var/review-runs/compliance-mapping/normalized-response.json",
    "var/review-runs/sandbox-vm-live-poc/normalized-response.json",
    "var/review-runs/public-security-product-positioning/normalized-response.json",
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

    normalized_response_paths = [
        response_rel
        for response_rel in NORMALIZED_RESPONSE_RELS
        if (repo_root / response_rel).exists()
    ]
    response_present_count = len(normalized_response_paths)
    closure_ready_count = 0

    if response_present_count != 0:
        failures.append("enterprise responses are present; use lane-specific response intake")

    boundary_flags = {
        "normalizes_real_responses": False,
        "writes_response_files": False,
        "mutates_findings": False,
        "records_external_review": False,
        "closes_erg_003": False,
        "closes_erg_002": False,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    application_protocol_doc = _read(
        repo_root / "docs/codex/enterprise-response-application-protocol.md"
    )
    intake_quickstart_doc = _read(
        repo_root / "docs/codex/enterprise-response-intake-quickstart.md"
    )
    current_checkpoint = _read(repo_root / "docs/codex/enterprise-current-checkpoint.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    required_phrases = [
        "Status: checked fixture-free rehearsal",
        "Current governed tool count: `24`",
        "Current selected capability: `not selected`",
        "make enterprise-response-application-rehearsal",
        "does not normalize real responses",
        "does not write response files",
        "does not record external review",
        "does not close `ERG-003`",
        "does not close `ERG-002`",
        "make sandbox-vm-static-preflight-response-application-preflight-check",
        "make mission-control-display-response-application-preflight-check",
        "ERG-003: external_review_required -> closed_local_preview_static_preflight",
        "ERG-002: planning_only -> ready_for_design_only_decision_record",
        "live VM/container inspection",
        "Mission Control runtime behavior",
        "sandbox orchestration",
        "public/security-product positioning",
        "new governed tool powers",
    ]
    for phrase in required_phrases:
        if phrase not in doc:
            failures.append(f"application rehearsal doc is missing phrase: {phrase}")

    forbidden_phrases = [
        "runtime behavior is approved",
        "Mission Control runtime behavior is approved",
        "live VM/container inspection is approved",
        "sandbox orchestration is approved",
        "public/security-product positioning is approved",
    ]
    lowered = doc.lower()
    for phrase in forbidden_phrases:
        if phrase.lower() in lowered:
            failures.append(f"application rehearsal doc contains forbidden phrase: {phrase}")

    target = "enterprise-response-application-rehearsal"
    if f"{target}:" not in makefile:
        failures.append("Make target is missing: enterprise-response-application-rehearsal")
    if target not in release_check_body and f"release-check: {target}" not in makefile:
        failures.append("enterprise-response-application-rehearsal missing from release-check")
    if f"$(MAKE) {target}" not in review_candidate_body:
        failures.append("enterprise-response-application-rehearsal missing from review-candidate")
    if target not in release_guardrails:
        failures.append("release guardrails do not require application rehearsal")
    if f"make {target}" not in readme:
        failures.append("README is missing enterprise response application rehearsal command")
    if DOC_REL not in readme:
        failures.append("README is missing enterprise response application rehearsal doc")
    if DOC_REL not in docs_site:
        failures.append("enterprise response application rehearsal missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise response application rehearsal missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise response application rehearsal")
    for label, source in [
        ("application protocol", application_protocol_doc),
        ("intake quickstart", intake_quickstart_doc),
        ("current checkpoint", current_checkpoint),
    ]:
        if target not in source:
            failures.append(f"{label} is missing enterprise response application rehearsal pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "rehearsal_doc": DOC_REL,
        "tool_count": 24,
        "recommended_gaps": ["ERG-003", "ERG-002"],
        "erg_003_status": "external_review_required",
        "erg_002_status": "planning_only",
        "response_present_count": response_present_count,
        "closure_ready_count": closure_ready_count,
        "normalized_response_paths": normalized_response_paths,
        **boundary_flags,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise response application rehearsal",
        f"valid: {str(report['valid']).lower()}",
        f"rehearsal_doc: {report['rehearsal_doc']}",
        f"tool_count: {report['tool_count']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        f"erg_003_status: {report['erg_003_status']}",
        f"erg_002_status: {report['erg_002_status']}",
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"records_external_review: {str(report['records_external_review']).lower()}",
        f"normalizes_real_responses: {str(report['normalizes_real_responses']).lower()}",
        f"writes_response_files: {str(report['writes_response_files']).lower()}",
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
        f"closes_erg_002: {str(report['closes_erg_002']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())

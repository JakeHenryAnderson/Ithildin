"""Validate the fail-closed Mission Control display disposition closure gate."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/mission-control-display-disposition-closure-gate.md"
DOC_NAME = "mission-control-display-disposition-closure-gate.md"
NORMALIZED_RESPONSE_REL = "var/review-runs/mission-control-display/normalized-response.json"
EXPECTED_AREA = "mission-control-display"
EXPECTED_NAMESPACE = "EXT-MC-DISPLAY-###"
EXPECTED_OUTCOME = "continue_design_only"
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

REQUIRED_PHRASES = [
    "Status: fail-closed closure gate for planning-only `ERG-002`.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "make mission-control-display-disposition-closure-check",
    NORMALIZED_RESPONSE_REL,
    "ithildin.external_review.normalized_response",
    "reviewed area: `mission-control-display`",
    "source-level` or `packet-and-source`",
    "finding namespace: `EXT-MC-DISPLAY-###`",
    "can_close_source_rows: true",
    "mutates_findings: false",
    "closes_external_review: false",
    "no critical/high findings",
    "disposition_outcome: continue_design_only",
    "closure_ready: false",
    "erg_002_status: planning_only",
    "mission_control_runtime_allowed: false",
    "runtime_importer_allowed: false",
    "ready_for_design_only_decision_record",
    "separate committed triage update",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "runtime implementation",
    "Mission Control runtime importer behavior",
    "Mission Control execution authority",
    "Mission Control policy authority",
    "Mission Control approval authority",
    "Mission Control audit authority",
    "API callbacks",
    "polling or mutating Ithildin APIs",
    "local model invocation",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "trusted-host promotion",
    "SIEM adapter behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote delivery",
    "shell/Docker/Kubernetes/browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "compliance automation",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "runtime implementation is approved",
    "Mission Control runtime importer behavior is approved",
    "Mission Control execution authority is approved",
    "Mission Control policy authority is approved",
    "Mission Control approval authority is approved",
    "Mission Control audit authority is approved",
    "API callbacks are approved",
    "polling or mutating Ithildin APIs are approved",
    "local model invocation is approved",
    "sandbox orchestration is approved",
    "trusted-host promotion is approved",
    "SIEM adapter behavior is approved",
    "ERG-002 is closed",
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
    doc_path = repo_root / DOC_REL
    normalized_response_path = repo_root / NORMALIZED_RESPONSE_REL
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    intake = _read(repo_root / "docs/codex/mission-control-display-external-response-intake.md")
    disposition_packet = _read(
        repo_root / "docs/codex/mission-control-display-disposition-packet.md"
    )
    decision_intake = _read(repo_root / "docs/codex/mission-control-display-decision-intake.md")
    readiness_packet = _read(
        repo_root / "docs/codex/mission-control-integration-readiness-packet.md"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("Mission Control display disposition closure gate doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"closure gate doc is missing phrase: {phrase}")
        for phrase in REQUIRED_BLOCKED_BOUNDARIES:
            if phrase not in text:
                failures.append(f"closure gate doc is missing blocked boundary: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"closure gate doc contains forbidden phrase: {phrase}")

    response_present = normalized_response_path.exists()
    response_report = _validate_normalized_response(normalized_response_path)
    failures.extend(response_report["failures"])
    closure_ready = response_report["closure_ready"]

    for linked_text, source_name in [
        (readme, "README"),
        (docs_site, "docs site"),
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
        (decision_register, "post-RC decision register"),
        (intake, "external response intake"),
        (disposition_packet, "Mission Control disposition packet"),
        (decision_intake, "Mission Control decision intake"),
        (readiness_packet, "Mission Control integration readiness packet"),
    ]:
        if DOC_NAME not in linked_text and DOC_REL not in linked_text:
            failures.append(f"{source_name} is missing {DOC_NAME}")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("review_docs.REVIEW_DOCS is missing Mission Control closure gate doc")
    if "mission-control-display-disposition-closure-check:" not in makefile:
        failures.append("Make target is missing: mission-control-display-disposition-closure-check")
    release_check_additive = "release-check: mission-control-display-disposition-closure-check"
    if (
        "mission-control-display-disposition-closure-check" not in release_check_body
        and release_check_additive not in makefile
    ):
        failures.append(
            "mission-control-display-disposition-closure-check missing from release-check"
        )
    if "mission-control-display-disposition-closure-check" not in release_guardrails:
        failures.append("release guardrails do not require Mission Control closure-check")

    return {
        "valid": not failures,
        "failures": failures,
        "closure_gate_doc": DOC_REL,
        "normalized_response_path": NORMALIZED_RESPONSE_REL,
        "normalized_response_present": response_present,
        "closure_ready": closure_ready,
        "disposition_outcome": response_report["disposition_outcome"],
        "erg_002_status": (
            "planning_only" if not closure_ready else "ready_for_design_only_decision_record"
        ),
        "allowed_closure_state": "ready_for_design_only_decision_record",
        "tool_count": 24,
        "area": EXPECTED_AREA,
        "finding_namespace": EXPECTED_NAMESPACE,
        "runtime_changes_allowed": False,
        "mission_control_planning_allowed": True,
        "mission_control_runtime_allowed": False,
        "runtime_importer_allowed": False,
        "mission_control_execution_authority_allowed": False,
        "mission_control_policy_authority_allowed": False,
        "mission_control_approval_authority_allowed": False,
        "mission_control_audit_authority_allowed": False,
        "api_callbacks_allowed": False,
        "polling_or_mutating_ithildin_apis_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "response": response_report,
    }


def _validate_normalized_response(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "failures": [],
            "closure_ready": False,
            "disposition_outcome": None,
            "reason": "normalized response is absent; ERG-002 remains planning-only",
        }
    failures: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "failures": [f"normalized response is invalid JSON: {exc}"],
            "closure_ready": False,
            "disposition_outcome": None,
            "reason": "invalid normalized response",
        }

    if payload.get("response_type") != "ithildin.external_review.normalized_response":
        failures.append("normalized response has unexpected response_type")
    if payload.get("area") != EXPECTED_AREA:
        failures.append("normalized response area is not mission-control-display")
    if payload.get("source_access") not in {"source-level", "packet-and-source"}:
        failures.append("normalized response source_access is not sufficient for closure")
    if payload.get("can_close_source_rows") is not True:
        failures.append("normalized response cannot close source rows")
    if payload.get("mutates_findings") is not False:
        failures.append("normalized response must not mutate findings")
    if payload.get("closes_external_review") is not False:
        failures.append("normalized response must not close external review directly")
    if not SHA256_PATTERN.match(str(payload.get("reviewed_packet_hash", ""))):
        failures.append("normalized response reviewed_packet_hash is not a sha256 digest")
    disposition_outcome = payload.get("disposition_outcome")
    if disposition_outcome != EXPECTED_OUTCOME:
        failures.append(
            "normalized response disposition_outcome does not permit design-only continuation"
        )

    findings = payload.get("findings", [])
    if not isinstance(findings, list):
        failures.append("normalized response findings must be a list")
        findings = []
    for finding in findings:
        if not isinstance(finding, dict):
            failures.append("normalized response contains a non-object finding")
            continue
        finding_id = str(finding.get("finding_id", ""))
        if not finding_id.startswith("EXT-MC-DISPLAY-"):
            failures.append(f"finding has wrong namespace: {finding_id}")
        if finding.get("area") != EXPECTED_AREA:
            failures.append(f"{finding_id} has wrong area")
        if str(finding.get("severity", "")).lower() in {"critical", "high"}:
            failures.append(f"{finding_id} is critical/high and blocks closure")

    return {
        "failures": failures,
        "closure_ready": not failures,
        "disposition_outcome": disposition_outcome,
        "reason": "normalized response validates" if not failures else "normalized response failed",
        "finding_count": len(findings),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control display disposition closure check",
        f"valid: {str(report['valid']).lower()}",
        f"closure_gate_doc: {report['closure_gate_doc']}",
        f"normalized_response_path: {report['normalized_response_path']}",
        f"normalized_response_present: {str(report['normalized_response_present']).lower()}",
        f"closure_ready: {str(report['closure_ready']).lower()}",
        f"disposition_outcome: {report['disposition_outcome']}",
        f"erg_002_status: {report['erg_002_status']}",
        f"allowed_closure_state: {report['allowed_closure_state']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_planning_allowed: "
        f"{str(report['mission_control_planning_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"runtime_importer_allowed: {str(report['runtime_importer_allowed']).lower()}",
        "mission_control_execution_authority_allowed: "
        f"{str(report['mission_control_execution_authority_allowed']).lower()}",
        "mission_control_policy_authority_allowed: "
        f"{str(report['mission_control_policy_authority_allowed']).lower()}",
        "mission_control_approval_authority_allowed: "
        f"{str(report['mission_control_approval_authority_allowed']).lower()}",
        "mission_control_audit_authority_allowed: "
        f"{str(report['mission_control_audit_authority_allowed']).lower()}",
        f"api_callbacks_allowed: {str(report['api_callbacks_allowed']).lower()}",
        "polling_or_mutating_ithildin_apis_allowed: "
        f"{str(report['polling_or_mutating_ithildin_apis_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
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

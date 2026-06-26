"""Validate the fail-closed sandbox/VM static preflight disposition closure gate."""

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
DOC_REL = "docs/codex/sandbox-vm-static-preflight-disposition-closure-gate.md"
DOC_NAME = "sandbox-vm-static-preflight-disposition-closure-gate.md"
NORMALIZED_RESPONSE_REL = (
    "var/review-runs/sandbox-vm-static-preflight/normalized-response.json"
)
EXPECTED_AREA = "sandbox-vm-static-preflight"
EXPECTED_NAMESPACE = "EXT-SVP-###"
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

REQUIRED_PHRASES = [
    "Status: fail-closed closure gate for `ERG-003`.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "make sandbox-vm-static-preflight-disposition-closure-check",
    NORMALIZED_RESPONSE_REL,
    "ithildin.external_review.normalized_response",
    "reviewed area: `sandbox-vm-static-preflight`",
    "source-level` or `packet-and-source`",
    "finding namespace: `EXT-SVP-###`",
    "can_close_source_rows: true",
    "mutates_findings: false",
    "closes_external_review: false",
    "no critical/high findings",
    "closure_ready: false",
    "closed_local_preview_static_preflight",
    "The CLI-only static sandbox/VM profile preflight lane is externally reviewed",
    "separate committed triage update",
    "sandbox-vm-static-preflight-triage-update.md",
    "make sandbox-vm-static-preflight-triage-update-check",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "network expansion",
    "API/MCP profile loading",
    "production identity",
    "SIEM delivery",
    "compliance automation",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "live VM control is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "ERG-003 is closed",
    "implementation is approved",
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
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_guardrails = (repo_root / "scripts/release_guardrails.py").read_text(
        encoding="utf-8"
    )
    enterprise = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    queue = (repo_root / "docs/codex/enterprise-external-review-queue.md").read_text(
        encoding="utf-8"
    )
    decision_register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(
        encoding="utf-8"
    )
    disposition_plan = (
        repo_root / "docs/codex/sandbox-vm-static-preflight-disposition-plan.md"
    ).read_text(encoding="utf-8")
    intake = (
        repo_root / "docs/codex/sandbox-vm-static-preflight-external-response-intake.md"
    ).read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("sandbox/VM static preflight disposition closure gate doc is missing")
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
        (enterprise, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
        (decision_register, "post-RC decision register"),
        (disposition_plan, "disposition plan"),
        (intake, "external response intake"),
    ]:
        if DOC_NAME not in linked_text and DOC_REL not in linked_text:
            failures.append(f"{source_name} is missing {DOC_NAME}")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("review_docs.REVIEW_DOCS is missing closure gate doc")
    if "sandbox-vm-static-preflight-disposition-closure-check:" not in makefile:
        failures.append(
            "Make target is missing: sandbox-vm-static-preflight-disposition-closure-check"
        )
    if "sandbox-vm-static-preflight-disposition-closure-check" not in release_check_body:
        failures.append(
            "sandbox-vm-static-preflight-disposition-closure-check missing from release-check"
        )
    if "sandbox-vm-static-preflight-disposition-closure-check" not in release_guardrails:
        failures.append(
            "release guardrails do not require disposition closure-check in release-check"
        )

    return {
        "valid": not failures,
        "failures": failures,
        "closure_gate_doc": DOC_REL,
        "normalized_response_path": NORMALIZED_RESPONSE_REL,
        "normalized_response_present": response_present,
        "closure_ready": closure_ready,
        "erg_003_status": "external_review_required"
        if not closure_ready
        else "ready_for_triage_update",
        "allowed_closure_state": "closed_local_preview_static_preflight",
        "tool_count": 24,
        "area": EXPECTED_AREA,
        "finding_namespace": EXPECTED_NAMESPACE,
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": False,
        "response": response_report,
    }


def _validate_normalized_response(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "failures": [],
            "closure_ready": False,
            "reason": "normalized response is absent; ERG-003 remains external_review_required",
        }
    failures: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "failures": [f"normalized response is invalid JSON: {exc}"],
            "closure_ready": False,
            "reason": "invalid normalized response",
        }

    if payload.get("response_type") != "ithildin.external_review.normalized_response":
        failures.append("normalized response has unexpected response_type")
    if payload.get("area") != EXPECTED_AREA:
        failures.append("normalized response area is not sandbox-vm-static-preflight")
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

    findings = payload.get("findings", [])
    if not isinstance(findings, list):
        failures.append("normalized response findings must be a list")
        findings = []
    for finding in findings:
        if not isinstance(finding, dict):
            failures.append("normalized response contains a non-object finding")
            continue
        finding_id = str(finding.get("finding_id", ""))
        if not finding_id.startswith("EXT-SVP-"):
            failures.append(f"finding has wrong namespace: {finding_id}")
        if finding.get("area") != EXPECTED_AREA:
            failures.append(f"{finding_id} has wrong area")
        if str(finding.get("severity", "")).lower() in {"critical", "high"}:
            failures.append(f"{finding_id} is critical/high and blocks closure")

    return {
        "failures": failures,
        "closure_ready": not failures,
        "reason": "normalized response supports later triage update"
        if not failures
        else "normalized response is not closure-ready",
        "finding_count": len(findings),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static preflight disposition closure check",
        f"valid: {str(report['valid']).lower()}",
        f"closure_gate_doc: {report['closure_gate_doc']}",
        f"normalized_response_path: {report['normalized_response_path']}",
        f"normalized_response_present: {str(report['normalized_response_present']).lower()}",
        f"closure_ready: {str(report['closure_ready']).lower()}",
        f"erg_003_status: {report['erg_003_status']}",
        f"allowed_closure_state: {report['allowed_closure_state']}",
        f"tool_count: {report['tool_count']}",
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


if __name__ == "__main__":
    raise SystemExit(main())

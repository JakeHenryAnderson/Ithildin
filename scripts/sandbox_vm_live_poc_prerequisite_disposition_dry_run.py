"""Exercise ERG-004 prerequisite disposition evidence with temporary fixtures."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-live-poc-prerequisite-disposition-dry-run.md"
DOC_NAME = "sandbox-vm-live-poc-prerequisite-disposition-dry-run.md"
EXPECTED_RECORD_TYPE = "ithildin.sandbox_vm_static_preflight.disposition_record"
EXPECTED_DECISION_ID = "PRD-SANDBOX-STATIC-PREFLIGHT-001"
EXPECTED_TARGET_LANE = "ERG-003"
EXPECTED_OUTCOME = "closed_local_preview_static_preflight"
EXPECTED_PACKET_HASH = "sha256:" + "7" * 64
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

REQUIRED_DOC_PHRASES = [
    "Status: temporary fixture dry run for the blocked `ERG-004` prerequisite chain.",
    "Current governed tool count: `24`.",
    "Current `ERG-003` status: `external_review_required`.",
    "Current `ERG-004` status: `blocked`.",
    "make sandbox-vm-live-poc-prerequisite-disposition-dry-run",
    "missing static-preflight disposition record is rejected",
    "favorable `ERG-003` static-preflight disposition record satisfies only the "
    "prerequisite fixture",
    "committed_findings_mutated: false",
    "external_review_recorded: false",
    "erg_003_closed: false",
    "erg_004_unblocked: false",
    "decision_record_recorded: false",
    "implementation_planning_allowed: false",
    "runtime_changes_allowed: false",
    "live_vm_inspection_allowed: false",
    "vm_container_lifecycle_management_allowed: false",
    "mission_control_runtime_allowed: false",
    "local_model_invocation_allowed: false",
    "sandbox_orchestration_allowed: false",
    "trusted_host_promotion_allowed: false",
    "public_security_product_positioning_allowed: false",
    "No fixture outcome in this dry run approves live POC planning",
]

FORBIDDEN_DOC_PHRASES = [
    "implementation planning is approved",
    "runtime implementation is approved",
    "live VM control is approved",
    "live VM/container inspection is approved",
    "sandbox orchestration is approved",
    "local model invocation is approved",
    "ERG-003 is closed",
    "ERG-004 is unblocked",
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
    cases = _run_fixture_cases()
    failures.extend(
        f"dry-run case failed: {case}" for case, passed in cases.items() if not passed
    )
    failures.extend(_validate_wiring(repo_root))

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "dry_run_doc": DOC_REL,
        "record_type": EXPECTED_RECORD_TYPE,
        "decision_id": EXPECTED_DECISION_ID,
        "target_lane": EXPECTED_TARGET_LANE,
        "allowed_disposition_outcome": EXPECTED_OUTCOME,
        "area": "sandbox-vm-live-poc-prerequisite-disposition",
        "tool_count": 24,
        "erg_003_status": "external_review_required",
        "erg_004_status": "blocked",
        "cases": cases,
        "temporary_fixtures_only": True,
        "real_normalized_response_mutated": False,
        "committed_findings_mutated": False,
        "external_review_recorded": False,
        "erg_003_closed": False,
        "erg_004_unblocked": False,
        "decision_record_recorded": False,
        "implementation_planning_allowed": False,
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_management_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "siem_adapter_allowed": False,
        "production_identity_allowed": False,
        "runtime_postgres_allowed": False,
        "hosted_telemetry_allowed": False,
        "remote_mcp_allowed": False,
        "compliance_automation_allowed": False,
        "shell_docker_kubernetes_browser_powers_allowed": False,
        "arbitrary_http_allowed": False,
        "broad_filesystem_writes_allowed": False,
        "plugin_sdk_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def _run_fixture_cases() -> dict[str, bool]:
    with tempfile.TemporaryDirectory(prefix="ithildin-erg004-prereq-") as tmp:
        tmp_path = Path(tmp)
        disposition_path = tmp_path / "disposition-record.json"
        cases: dict[str, bool] = {}

        cases["missing_disposition_rejected"] = _is_rejected(
            _validate_disposition_record(disposition_path)
        )

        _write_json(disposition_path, _valid_disposition_record())
        valid_report = _validate_disposition_record(disposition_path)
        cases["favorable_disposition_satisfies_prerequisite_only"] = (
            valid_report["valid"] is True
            and valid_report["prerequisite_satisfied"] is True
            and valid_report["erg_004_unblocked"] is False
            and valid_report["implementation_planning_allowed"] is False
            and valid_report["runtime_changes_allowed"] is False
        )

        _write_json(disposition_path, _valid_disposition_record(target_lane="ERG-004"))
        cases["wrong_lane_rejected"] = _is_rejected(
            _validate_disposition_record(disposition_path)
        )

        _write_json(disposition_path, _valid_disposition_record(outcome="closed"))
        cases["wrong_outcome_rejected"] = _is_rejected(
            _validate_disposition_record(disposition_path)
        )

        _write_json(disposition_path, _valid_disposition_record(reviewed_packet_hash="sha256:nope"))
        cases["bad_hash_rejected"] = _is_rejected(
            _validate_disposition_record(disposition_path)
        )

        _write_json(
            disposition_path,
            _valid_disposition_record(
                findings=[
                    {
                        "finding_id": "EXT-SVP-001",
                        "severity": "high",
                        "area": "sandbox-vm-static-preflight",
                        "disposition": "open",
                    }
                ]
            ),
        )
        cases["critical_high_static_preflight_finding_rejected"] = _is_rejected(
            _validate_disposition_record(disposition_path)
        )

        _write_json(disposition_path, _valid_disposition_record(runtime_changes_allowed=True))
        cases["runtime_approval_rejected"] = _is_rejected(
            _validate_disposition_record(disposition_path)
        )

        _write_json(disposition_path, _valid_disposition_record(erg_004_unblocked=True))
        cases["erg_004_unblock_rejected"] = _is_rejected(
            _validate_disposition_record(disposition_path)
        )

        _write_json(
            disposition_path,
            _valid_disposition_record(implementation_planning_allowed=True),
        )
        cases["live_poc_planning_approval_rejected"] = _is_rejected(
            _validate_disposition_record(disposition_path)
        )

    return cases


def _validate_disposition_record(path: Path) -> dict[str, Any]:
    failures: list[str] = []
    if not path.exists():
        return {
            "valid": False,
            "failures": ["disposition record is missing"],
            "prerequisite_satisfied": False,
            "erg_004_unblocked": False,
            "implementation_planning_allowed": False,
            "runtime_changes_allowed": False,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "valid": False,
            "failures": [f"disposition record is invalid JSON: {exc}"],
            "prerequisite_satisfied": False,
            "erg_004_unblocked": False,
            "implementation_planning_allowed": False,
            "runtime_changes_allowed": False,
        }

    if payload.get("record_type") != EXPECTED_RECORD_TYPE:
        failures.append("disposition record has unexpected record_type")
    if payload.get("decision_id") != EXPECTED_DECISION_ID:
        failures.append("disposition record has unexpected decision_id")
    if payload.get("target_lane") != EXPECTED_TARGET_LANE:
        failures.append("disposition record target_lane is not ERG-003")
    if payload.get("disposition_outcome") != EXPECTED_OUTCOME:
        failures.append("disposition record has unexpected disposition_outcome")
    if payload.get("source_access") not in {"source-level", "packet-and-source"}:
        failures.append("disposition record source_access is not sufficient")
    if payload.get("can_close_source_rows") is not True:
        failures.append("disposition record cannot close source rows")
    if payload.get("mutates_findings") is not False:
        failures.append("disposition record must not mutate findings")
    if payload.get("closes_external_review") is not False:
        failures.append("disposition record must not close external review directly")
    if not SHA256_PATTERN.match(str(payload.get("reviewed_packet_hash", ""))):
        failures.append("disposition record reviewed_packet_hash is not a sha256 digest")
    if payload.get("erg_004_unblocked") is not False:
        failures.append("disposition record must keep ERG-004 blocked")
    if payload.get("implementation_planning_allowed") is not False:
        failures.append("disposition record must not approve implementation planning")
    if payload.get("runtime_changes_allowed") is not False:
        failures.append("disposition record must not approve runtime changes")

    findings = payload.get("findings", [])
    if not isinstance(findings, list):
        failures.append("disposition record findings must be a list")
        findings = []
    for finding in findings:
        if not isinstance(finding, dict):
            failures.append("disposition record contains a non-object finding")
            continue
        finding_id = str(finding.get("finding_id", ""))
        if not finding_id.startswith("EXT-SVP-"):
            failures.append(f"finding has wrong namespace: {finding_id}")
        if str(finding.get("severity", "")).lower() in {"critical", "high"}:
            failures.append(f"{finding_id} is critical/high and blocks prerequisite")

    valid = not failures
    return {
        "valid": valid,
        "failures": failures,
        "prerequisite_satisfied": valid,
        "erg_004_unblocked": False,
        "implementation_planning_allowed": False,
        "runtime_changes_allowed": False,
    }


def _valid_disposition_record(
    *,
    target_lane: str = EXPECTED_TARGET_LANE,
    outcome: str = EXPECTED_OUTCOME,
    reviewed_packet_hash: str = EXPECTED_PACKET_HASH,
    findings: list[dict[str, Any]] | None = None,
    runtime_changes_allowed: bool = False,
    erg_004_unblocked: bool = False,
    implementation_planning_allowed: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "record_type": EXPECTED_RECORD_TYPE,
        "decision_id": EXPECTED_DECISION_ID,
        "target_lane": target_lane,
        "disposition_outcome": outcome,
        "source_access": "source-level",
        "can_close_source_rows": True,
        "mutates_findings": False,
        "closes_external_review": False,
        "reviewed_packet_hash": reviewed_packet_hash,
        "finding_count": len(findings or []),
        "findings": findings or [],
        "erg_004_unblocked": erg_004_unblocked,
        "implementation_planning_allowed": implementation_planning_allowed,
        "runtime_changes_allowed": runtime_changes_allowed,
    }


def _validate_wiring(repo_root: Path) -> list[str]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    preconditions = _read(repo_root / "docs/codex/sandbox-vm-live-poc-preconditions-map.md")
    response_dry_run = _read(repo_root / "docs/codex/sandbox-vm-live-poc-response-dry-run.md")
    decision_skeleton = _read(
        repo_root / "docs/codex/sandbox-vm-live-poc-decision-record-skeleton.md"
    )
    readiness = _read(repo_root / "docs/codex/enterprise-sandbox-control-plane-readiness.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("live POC prerequisite disposition dry-run doc is missing")
    else:
        doc = doc_path.read_text(encoding="utf-8")
        lowered = doc.lower()
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in doc:
                failures.append(f"dry-run doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_DOC_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"dry-run doc contains forbidden phrase: {phrase}")

    if "sandbox-vm-live-poc-prerequisite-disposition-dry-run:" not in makefile:
        failures.append(
            "Make target is missing: sandbox-vm-live-poc-prerequisite-disposition-dry-run"
        )
    if (
        "sandbox-vm-live-poc-prerequisite-disposition-dry-run" not in release_check_body
        and "release-check: sandbox-vm-live-poc-prerequisite-disposition-dry-run"
        not in makefile
    ):
        failures.append("live POC prerequisite dry run missing from release-check")
    if "sandbox-vm-live-poc-prerequisite-disposition-dry-run" not in release_guardrails:
        failures.append("release guardrails do not require live POC prerequisite dry run")
    if DOC_REL not in docs_site:
        failures.append("docs site is missing live POC prerequisite dry-run doc")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("review_docs.REVIEW_DOCS is missing live POC prerequisite dry-run doc")
    if "Sandbox/VM Live POC Prerequisite Disposition Dry Run" not in review_index:
        failures.append("review-docs index is missing live POC prerequisite dry-run doc")
    if "make sandbox-vm-live-poc-prerequisite-disposition-dry-run" not in readme:
        failures.append("README is missing live POC prerequisite dry-run command")
    for text, source_name in [
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
        (decision_register, "post-RC decision register"),
        (preconditions, "live POC preconditions map"),
        (response_dry_run, "live POC response dry run"),
        (decision_skeleton, "live POC decision record skeleton"),
        (readiness, "enterprise sandbox control-plane readiness"),
    ]:
        if DOC_NAME not in text and DOC_REL not in text:
            failures.append(f"{source_name} is missing {DOC_NAME}")
    return failures


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _is_rejected(report: dict[str, Any]) -> bool:
    return report["valid"] is False and report["prerequisite_satisfied"] is False


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC prerequisite disposition dry run",
        f"valid: {str(report['valid']).lower()}",
        f"dry_run_doc: {report['dry_run_doc']}",
        f"record_type: {report['record_type']}",
        f"decision_id: {report['decision_id']}",
        f"target_lane: {report['target_lane']}",
        f"allowed_disposition_outcome: {report['allowed_disposition_outcome']}",
        f"area: {report['area']}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"temporary_fixtures_only: {str(report['temporary_fixtures_only']).lower()}",
        "real_normalized_response_mutated: "
        f"{str(report['real_normalized_response_mutated']).lower()}",
        f"committed_findings_mutated: {str(report['committed_findings_mutated']).lower()}",
        f"external_review_recorded: {str(report['external_review_recorded']).lower()}",
        f"erg_003_closed: {str(report['erg_003_closed']).lower()}",
        f"erg_004_unblocked: {str(report['erg_004_unblocked']).lower()}",
        f"decision_record_recorded: {str(report['decision_record_recorded']).lower()}",
        "implementation_planning_allowed: "
        f"{str(report['implementation_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "vm_container_lifecycle_management_allowed: "
        f"{str(report['vm_container_lifecycle_management_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        "api_mcp_profile_loading_allowed: "
        f"{str(report['api_mcp_profile_loading_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        "cases:",
    ]
    lines.extend(f"- {case}: {str(passed).lower()}" for case, passed in report["cases"].items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

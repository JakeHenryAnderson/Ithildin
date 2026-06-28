"""Exercise sandbox/VM live POC response closure without recording review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import sandbox_vm_live_poc_decision_closure_check as closure
from scripts.response_dry_run_lock import response_dry_run_lock

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-live-poc-response-dry-run.md"
DOC_NAME = "sandbox-vm-live-poc-response-dry-run.md"
EXPECTED_OUTCOME = "approve_limited_operator_managed_poc_planning"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = run_dry_run(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def run_dry_run(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    with response_dry_run_lock(repo_root, closure.NORMALIZED_RESPONSE_REL):
        response_path = repo_root / closure.NORMALIZED_RESPONSE_REL
        original = response_path.read_bytes() if response_path.exists() else None
        original_present = original is not None
        cases: dict[str, bool] = {}

        try:
            if response_path.exists():
                response_path.unlink()
            absent_report = closure.build_report(repo_root)
            cases["absent_response_valid"] = absent_report["valid"] is True
            cases["absent_response_not_ready"] = absent_report["closure_ready"] is False

            response_path.parent.mkdir(parents=True, exist_ok=True)

            _write_response(response_path, _valid_response())
            valid_report = closure.build_report(repo_root)
            cases["valid_response_accepts"] = (
                valid_report["valid"] is True
                and valid_report["closure_ready"] is True
                and valid_report["erg_004_status"] == "ready_for_decision_record"
                and valid_report["erg_003_favorable_disposition"] is True
            )

            _write_response(
                response_path,
                _valid_response(erg_003_favorable_disposition=False),
            )
            cases["missing_erg_003_favorable_disposition_rejected"] = _is_rejected(
                closure.build_report(repo_root)
            )

            _write_response(response_path, _valid_response(source_access="packet-only"))
            cases["packet_only_rejected"] = _is_rejected(closure.build_report(repo_root))

            _write_response(
                response_path, _valid_response(reviewed_packet_hash="sha256:not-a-hash")
            )
            cases["bad_hash_rejected"] = _is_rejected(closure.build_report(repo_root))

            high_finding = {
                "finding_id": "EXT-LIVE-POC-001",
                "severity": "high",
                "area": closure.EXPECTED_AREA,
                "affected_files_functions": "docs/codex/sandbox-vm-live-poc-decision-packet.md",
                "blocking_status": "should-fix",
                "disposition": "open",
                "recommended_fix": "dry-run negative fixture",
            }
            _write_response(response_path, _valid_response(findings=[high_finding]))
            cases["critical_high_finding_rejected"] = _is_rejected(closure.build_report(repo_root))

            _write_response(response_path, _valid_response(closes_external_review=True))
            cases["direct_external_closure_rejected"] = _is_rejected(
                closure.build_report(repo_root)
            )
        finally:
            if original is None:
                response_path.unlink(missing_ok=True)
            else:
                response_path.parent.mkdir(parents=True, exist_ok=True)
                response_path.write_bytes(original)

        restored_present = response_path.exists()
        restored_original = True
        if original is not None and restored_present:
            restored_original = response_path.read_bytes() == original
        if original_present != restored_present:
            failures.append(
                "normalized response path was not restored to its original presence state"
            )
        if not restored_original:
            failures.append("normalized response path content was not restored")
        for case, passed in cases.items():
            if not passed:
                failures.append(f"dry-run case failed: {case}")

        return {
            "schema_version": "1",
            "valid": not failures,
            "failures": failures,
            "dry_run_doc": DOC_REL,
            "normalized_response_path": closure.NORMALIZED_RESPONSE_REL,
            "area": closure.EXPECTED_AREA,
            "finding_namespace": closure.EXPECTED_NAMESPACE,
            "tool_count": 24,
            "original_response_present": original_present,
            "response_restored": not failures
            or not any("restored" in failure for failure in failures),
            "cases": cases,
            "committed_findings_mutated": False,
            "external_review_recorded": False,
            "erg_004_closed": False,
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


def _valid_response(
    *,
    source_access: str = "source-level",
    reviewed_packet_hash: str = "sha256:" + "4" * 64,
    findings: list[dict[str, Any]] | None = None,
    closes_external_review: bool = False,
    erg_003_favorable_disposition: bool = True,
    decision_outcome: str = EXPECTED_OUTCOME,
) -> dict[str, Any]:
    findings = findings or []
    return {
        "schema_version": "1",
        "response_type": "ithildin.external_review.normalized_response",
        "reviewer": "dry-run reviewer",
        "reviewer_type": "fixture",
        "source_access": source_access,
        "reviewed_commit": "abcdef1234567890",
        "reviewed_packet_hash": reviewed_packet_hash,
        "area": closure.EXPECTED_AREA,
        "finding_count": len(findings),
        "findings": findings,
        "can_close_source_rows": source_access in {"source-level", "packet-and-source"},
        "mutates_findings": False,
        "closes_external_review": closes_external_review,
        "erg_003_favorable_disposition": erg_003_favorable_disposition,
        "decision_outcome": decision_outcome,
    }


def _write_response(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _is_rejected(report: dict[str, Any]) -> bool:
    return report["valid"] is False and report["closure_ready"] is False


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC response dry run",
        f"valid: {str(report['valid']).lower()}",
        f"dry_run_doc: {report['dry_run_doc']}",
        f"normalized_response_path: {report['normalized_response_path']}",
        f"area: {report['area']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"tool_count: {report['tool_count']}",
        f"original_response_present: {str(report['original_response_present']).lower()}",
        f"response_restored: {str(report['response_restored']).lower()}",
        f"committed_findings_mutated: {str(report['committed_findings_mutated']).lower()}",
        f"external_review_recorded: {str(report['external_review_recorded']).lower()}",
        f"erg_004_closed: {str(report['erg_004_closed']).lower()}",
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
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"runtime_postgres_allowed: {str(report['runtime_postgres_allowed']).lower()}",
        f"hosted_telemetry_allowed: {str(report['hosted_telemetry_allowed']).lower()}",
        f"remote_mcp_allowed: {str(report['remote_mcp_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        "shell_docker_kubernetes_browser_powers_allowed: "
        f"{str(report['shell_docker_kubernetes_browser_powers_allowed']).lower()}",
        f"arbitrary_http_allowed: {str(report['arbitrary_http_allowed']).lower()}",
        "broad_filesystem_writes_allowed: "
        f"{str(report['broad_filesystem_writes_allowed']).lower()}",
        f"plugin_sdk_allowed: {str(report['plugin_sdk_allowed']).lower()}",
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

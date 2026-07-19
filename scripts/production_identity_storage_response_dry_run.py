"""Exercise production identity/storage response closure without recording review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import external_response_normalize
from scripts import production_identity_storage_disposition_closure_check as closure
from scripts.response_dry_run_lock import response_dry_run_lock

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/production-identity-storage-response-dry-run.md"
DOC_NAME = "production-identity-storage-response-dry-run.md"


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
        expected_commit, commit_failure = closure._expected_reviewed_commit(repo_root)
        expected_packet_hash, hash_failure = closure._expected_reviewed_packet_hash(repo_root)
        if commit_failure or expected_commit is None:
            expected_commit = "0" * 40
        if hash_failure or expected_packet_hash is None:
            expected_packet_hash = "sha256:" + "0" * 64

        def closure_report() -> dict[str, Any]:
            return closure.build_report(
                repo_root,
                expected_reviewed_commit_override=expected_commit,
                expected_reviewed_packet_hash_override=expected_packet_hash,
            )

        def valid_response(**overrides: Any) -> dict[str, Any]:
            values: dict[str, Any] = {
                "reviewed_commit": expected_commit or ("0" * 40),
                "reviewed_packet_hash": expected_packet_hash or ("sha256:" + "0" * 64),
            }
            values.update(overrides)
            return _valid_response(**values)

        try:
            if response_path.exists():
                response_path.unlink()
            absent_report = closure_report()
            cases["absent_response_valid"] = absent_report["valid"] is True
            cases["absent_response_not_ready"] = absent_report["closure_ready"] is False

            response_path.parent.mkdir(parents=True, exist_ok=True)

            raw_response = "\n".join(
                [
                    "# Production Identity And Storage Review",
                    "",
                    "continue_architecture_planning",
                    "",
                    "finding_count: 0",
                ]
            )
            normalized = external_response_normalize.normalize_response(
                raw_response,
                reviewer="dry-run reviewer",
                reviewer_type="fixture",
                source_access="packet-and-source",
                reviewed_commit=expected_commit or ("0" * 40),
                reviewed_packet_hash=expected_packet_hash
                or ("sha256:" + "0" * 64),
                area=closure.EXPECTED_AREA,
                disposition_outcome=closure.EXPECTED_OUTCOME,
            )
            _write_response(response_path, normalized)
            normalized_report = closure_report()
            cases["real_normalizer_response_accepts"] = (
                normalized_report["valid"] is True
                and normalized_report["closure_ready"] is True
            )

            _write_response(response_path, valid_response())
            valid_report = closure_report()
            cases["valid_response_accepts"] = (
                valid_report["valid"] is True
                and valid_report["closure_ready"] is True
                and valid_report["erg_006_status"] == "ready_for_architecture_decision_record"
                and valid_report["erg_007_status"] == "ready_for_architecture_decision_record"
            )

            _write_response(response_path, valid_response(source_access="packet-only"))
            cases["packet_only_rejected"] = _is_rejected(closure_report())

            _write_response(
                response_path, valid_response(reviewed_packet_hash="sha256:not-a-hash")
            )
            cases["bad_hash_rejected"] = _is_rejected(closure_report())

            _write_response(
                response_path,
                valid_response(reviewed_packet_hash="sha256:" + "f" * 64),
            )
            cases["wrong_well_formed_hash_rejected"] = _is_rejected(
                closure_report()
            )

            _write_response(
                response_path,
                valid_response(reviewed_commit="f" * 40),
            )
            cases["wrong_well_formed_commit_rejected"] = _is_rejected(
                closure_report()
            )

            high_finding = {
                "finding_id": "EXT-PROD-IAM-STORAGE-001",
                "severity": "high",
                "area": closure.EXPECTED_AREA,
                "affected_files_functions": (
                    "docs/codex/production-identity-storage-architecture.md"
                ),
                "blocking_status": "should-fix",
                "disposition": "open",
                "recommended_fix": "dry-run negative fixture",
            }
            _write_response(response_path, valid_response(findings=[high_finding]))
            cases["critical_high_finding_rejected"] = _is_rejected(closure_report())

            _write_response(response_path, valid_response(closes_external_review=True))
            cases["direct_external_closure_rejected"] = _is_rejected(
                closure_report()
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
            "erg_006_closed": False,
            "erg_007_closed": False,
            "architecture_planning_recorded": False,
            "implementation_planning_allowed": False,
            "runtime_changes_allowed": False,
            "production_identity_allowed": False,
            "enterprise_rbac_allowed": False,
            "tenant_team_authorization_allowed": False,
            "remote_admin_allowed": False,
            "runtime_postgres_allowed": False,
            "database_migrations_allowed": False,
            "backup_restore_runtime_allowed": False,
            "retention_enforcement_allowed": False,
            "hosted_control_plane_allowed": False,
            "custody_grade_audit_claims_allowed": False,
            "compliance_automation_allowed": False,
            "hosted_telemetry_allowed": False,
            "remote_mcp_allowed": False,
            "siem_adapter_allowed": False,
            "sandbox_orchestration_allowed": False,
            "local_model_invocation_allowed": False,
            "trusted_host_promotion_allowed": False,
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
    reviewed_commit: str = "0" * 40,
    reviewed_packet_hash: str = "sha256:" + "0" * 64,
    findings: list[dict[str, Any]] | None = None,
    closes_external_review: bool = False,
) -> dict[str, Any]:
    findings = findings or []
    return {
        "schema_version": "1",
        "response_type": "ithildin.external_review.normalized_response",
        "reviewer": "dry-run reviewer",
        "reviewer_type": "fixture",
        "source_access": source_access,
        "reviewed_commit": reviewed_commit,
        "reviewed_packet_hash": reviewed_packet_hash,
        "area": closure.EXPECTED_AREA,
        "finding_count": len(findings),
        "findings": findings,
        "can_close_source_rows": source_access in {"source-level", "packet-and-source"},
        "mutates_findings": False,
        "closes_external_review": closes_external_review,
        "disposition_outcome": closure.EXPECTED_OUTCOME,
    }


def _write_response(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _is_rejected(report: dict[str, Any]) -> bool:
    return report["valid"] is False and report["closure_ready"] is False


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin production identity/storage response dry run",
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
        f"erg_006_closed: {str(report['erg_006_closed']).lower()}",
        f"erg_007_closed: {str(report['erg_007_closed']).lower()}",
        f"architecture_planning_recorded: {str(report['architecture_planning_recorded']).lower()}",
        "implementation_planning_allowed: "
        f"{str(report['implementation_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"enterprise_rbac_allowed: {str(report['enterprise_rbac_allowed']).lower()}",
        "tenant_team_authorization_allowed: "
        f"{str(report['tenant_team_authorization_allowed']).lower()}",
        f"remote_admin_allowed: {str(report['remote_admin_allowed']).lower()}",
        f"runtime_postgres_allowed: {str(report['runtime_postgres_allowed']).lower()}",
        f"database_migrations_allowed: {str(report['database_migrations_allowed']).lower()}",
        f"backup_restore_runtime_allowed: {str(report['backup_restore_runtime_allowed']).lower()}",
        f"retention_enforcement_allowed: {str(report['retention_enforcement_allowed']).lower()}",
        f"hosted_control_plane_allowed: {str(report['hosted_control_plane_allowed']).lower()}",
        "custody_grade_audit_claims_allowed: "
        f"{str(report['custody_grade_audit_claims_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        f"hosted_telemetry_allowed: {str(report['hosted_telemetry_allowed']).lower()}",
        f"remote_mcp_allowed: {str(report['remote_mcp_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
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

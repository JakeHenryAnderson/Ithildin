"""Exercise ERG-004 descriptor-only response intake without recording review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import external_response_normalize
from scripts import (
    sandbox_vm_live_poc_runtime_descriptor_only_external_response_intake_check as intake,
)
from scripts.response_dry_run_lock import response_dry_run_lock

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run.md"
)
NORMALIZED_RESPONSE_REL = (
    "var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only/"
    "normalized-response.json"
)
EXPECTED_OUTCOME = "approve_descriptor_only_local_preview_disposition"


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
    normalized_path = repo_root / NORMALIZED_RESPONSE_REL
    with response_dry_run_lock(repo_root, NORMALIZED_RESPONSE_REL):
        original = normalized_path.read_bytes() if normalized_path.exists() else None
        original_present = original is not None
        cases: dict[str, bool] = {}

        try:
            normalized_path.unlink(missing_ok=True)
            absent_report = intake.build_report(repo_root)
            cases["absent_response_keeps_intake_valid"] = absent_report["valid"] is True
            cases["absent_response_does_not_close"] = (
                absent_report["closes_external_review"] is False
                and absent_report["runtime_changes_allowed"] is False
            )

            favorable_text = _response_text(
                outcome=EXPECTED_OUTCOME,
                no_findings=True,
            )
            favorable = _normalize_and_write(normalized_path, favorable_text)
            cases["favorable_source_response_normalizes"] = (
                favorable["finding_count"] == 0
                and favorable["can_close_source_rows"] is True
                and _descriptor_disposition_consideration_ready(
                    favorable, favorable_text
                )
            )

            packet_only_text = _response_text(
                source_access_note="packet-only",
                outcome=EXPECTED_OUTCOME,
                no_findings=True,
            )
            packet_only = _normalize_and_write(
                normalized_path,
                packet_only_text,
                source_access="packet-only",
            )
            cases["packet_only_response_not_disposition_ready"] = (
                packet_only["can_close_source_rows"] is False
                and _descriptor_disposition_consideration_ready(
                    packet_only, packet_only_text
                )
                is False
            )

            docs_only_text = _response_text(
                source_access_note="docs-only",
                outcome=EXPECTED_OUTCOME,
                no_findings=True,
            )
            docs_only = _normalize_and_write(
                normalized_path,
                docs_only_text,
                source_access="docs-only",
            )
            cases["docs_only_response_not_disposition_ready"] = (
                docs_only["can_close_source_rows"] is False
                and _descriptor_disposition_consideration_ready(
                    docs_only, docs_only_text
                )
                is False
            )

            internal_proxy_text = _response_text(
                source_access_note="packet-and-source internal proxy review",
                outcome=EXPECTED_OUTCOME,
                no_findings=True,
            )
            internal_proxy = _normalize_and_write(
                normalized_path,
                internal_proxy_text,
                reviewer_type="codex-high",
            )
            cases["internal_proxy_response_local_development_ready"] = (
                internal_proxy["finding_count"] == 0
                and internal_proxy["can_close_source_rows"] is True
                and _descriptor_disposition_consideration_ready(
                    internal_proxy, internal_proxy_text
                )
                is True
            )

            missing_outcome_text = _response_text(no_findings=True)
            missing_outcome = _normalize_and_write(
                normalized_path, missing_outcome_text
            )
            cases["missing_outcome_not_disposition_ready"] = (
                missing_outcome["finding_count"] == 0
                and _descriptor_disposition_consideration_ready(
                    missing_outcome, missing_outcome_text
                )
                is False
            )

            high_finding_text = _response_text(
                outcome=EXPECTED_OUTCOME,
                findings=[
                    {
                        "finding_id": "EXT-LIVE-DESC-001",
                        "severity": "high",
                        "area": intake.AREA,
                        "affected_files_functions": DOC_REL,
                        "blocking_status": "blocking",
                        "disposition": "open",
                        "recommended_fix": "dry-run negative fixture",
                    }
                ],
            )
            high_finding = _normalize_and_write(normalized_path, high_finding_text)
            cases["critical_high_finding_not_disposition_ready"] = (
                high_finding["finding_count"] == 1
                and _has_critical_high_findings(high_finding) is True
                and _descriptor_disposition_consideration_ready(
                    high_finding, high_finding_text
                )
                is False
            )

            cases["bad_hash_rejected"] = _normalization_rejected(
                favorable_text,
                reviewed_packet_hash="sha256:not-a-hash",
            )
            cases["wrong_namespace_rejected"] = _normalization_rejected(
                _response_text(
                    findings=[
                        {
                            "finding_id": "EXT-LIVE-GATE-001",
                            "severity": "low",
                            "area": intake.AREA,
                            "affected_files_functions": DOC_REL,
                            "blocking_status": "advisory",
                            "disposition": "open",
                            "recommended_fix": "dry-run negative fixture",
                        }
                    ]
                )
            )
            cases["wrong_area_rejected"] = _normalization_rejected(
                _response_text(
                    findings=[
                        {
                            "finding_id": "EXT-LIVE-DESC-002",
                            "severity": "low",
                            "area": "sandbox-vm-live-poc-runtime-gate-readiness",
                            "affected_files_functions": DOC_REL,
                            "blocking_status": "advisory",
                            "disposition": "open",
                            "recommended_fix": "dry-run negative fixture",
                        }
                    ]
                )
            )
            cases["secret_marker_rejected"] = _normalization_rejected(
                favorable_text + "\nBEGIN PRIVATE KEY\n",
            )
            cases["missing_explicit_finding_statement_rejected"] = (
                _normalization_rejected("Overall judgment: looks fine.\n")
            )
        finally:
            if original is None:
                normalized_path.unlink(missing_ok=True)
            else:
                normalized_path.parent.mkdir(parents=True, exist_ok=True)
                normalized_path.write_bytes(original)

        restored_present = normalized_path.exists()
        restored_original = True
        if original is not None and restored_present:
            restored_original = normalized_path.read_bytes() == original
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
            "intake_doc": intake.DOC_REL,
            "normalized_response_path": NORMALIZED_RESPONSE_REL,
            "area": intake.AREA,
            "finding_namespace": "EXT-LIVE-DESC-###",
            "tool_count": 24,
            "original_response_present": original_present,
            "response_restored": not any("restored" in failure for failure in failures),
            "cases": cases,
            "committed_findings_mutated": False,
            "external_review_recorded": False,
            "erg_004_closed": False,
            "descriptor_only_closure_recorded": False,
            "descriptor_only_source_disposition_allowed": False,
            "runtime_changes_allowed": False,
            "runtime_implementation_allowed": False,
            "live_vm_inspection_allowed": False,
            "vm_container_lifecycle_allowed": False,
            "sandbox_orchestration_allowed": False,
            "mission_control_runtime_allowed": False,
            "local_model_invocation_allowed": False,
            "trusted_host_promotion_allowed": False,
            "host_writes_allowed": False,
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


def _normalize_and_write(
    path: Path,
    text: str,
    *,
    reviewer_type: str = "gpt-5.5-pro",
    source_access: str = "packet-and-source",
    reviewed_packet_hash: str = "sha256:" + "6" * 64,
) -> dict[str, Any]:
    result = external_response_normalize.normalize_response(
        text,
        reviewer="dry-run reviewer",
        reviewer_type=reviewer_type,
        source_access=source_access,
        reviewed_commit="abcdef1234567890",
        reviewed_packet_hash=reviewed_packet_hash,
        area=intake.AREA,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _normalization_rejected(
    text: str,
    *,
    source_access: str = "packet-and-source",
    reviewed_packet_hash: str = "sha256:" + "6" * 64,
) -> bool:
    try:
        external_response_normalize.normalize_response(
            text,
            reviewer="dry-run reviewer",
            reviewer_type="gpt-5.5-pro",
            source_access=source_access,
            reviewed_commit="abcdef1234567890",
            reviewed_packet_hash=reviewed_packet_hash,
            area=intake.AREA,
        )
    except external_response_normalize.ExternalResponseNormalizationError:
        return True
    return False


def _descriptor_disposition_consideration_ready(
    response: dict[str, Any], text: str
) -> bool:
    return (
        response.get("can_close_source_rows") is True
        and response.get("reviewer_type")
        in {"human", "gpt-5.5-pro", "external-ai", "codex-high", "codex-xhigh"}
        and not _has_critical_high_findings(response)
        and EXPECTED_OUTCOME in text
    )


def _has_critical_high_findings(response: dict[str, Any]) -> bool:
    return any(
        finding.get("severity") in {"critical", "high"}
        for finding in response.get("findings", [])
    )


def _response_text(
    *,
    source_access_note: str = "packet-and-source",
    outcome: str | None = None,
    no_findings: bool = False,
    findings: list[dict[str, str]] | None = None,
) -> str:
    lines = [
        "Overall judgment: fixture response for descriptor-only runtime intake.",
        f"Source access: {source_access_note}.",
    ]
    if outcome:
        lines.append(f"Disposition: {outcome}.")
    if no_findings:
        lines.append("No findings.")
    if findings:
        lines.extend(
            [
                "",
                "| Finding ID | Severity | Area | Affected files/functions | "
                "Blocking status | Disposition | Recommended fix |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for finding in findings:
            lines.append(
                "| {finding_id} | {severity} | {area} | {affected_files_functions} | "
                "{blocking_status} | {disposition} | {recommended_fix} |".format(
                    **finding
                )
            )
    return "\n".join(lines) + "\n"


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC descriptor-only response dry run",
        f"valid: {str(report['valid']).lower()}",
        f"dry_run_doc: {report['dry_run_doc']}",
        f"intake_doc: {report['intake_doc']}",
        f"normalized_response_path: {report['normalized_response_path']}",
        f"area: {report['area']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"tool_count: {report['tool_count']}",
        f"original_response_present: {str(report['original_response_present']).lower()}",
        f"response_restored: {str(report['response_restored']).lower()}",
        f"committed_findings_mutated: {str(report['committed_findings_mutated']).lower()}",
        f"external_review_recorded: {str(report['external_review_recorded']).lower()}",
        f"erg_004_closed: {str(report['erg_004_closed']).lower()}",
        "descriptor_only_closure_recorded: "
        f"{str(report['descriptor_only_closure_recorded']).lower()}",
        "descriptor_only_source_disposition_allowed: "
        f"{str(report['descriptor_only_source_disposition_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
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

"""Exercise enterprise response-intake paths without recording external review."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    compliance_mapping_response_dry_run,
    enterprise_response_inbox,
    enterprise_response_normalization_coverage,
    enterprise_response_status_board,
    external_response_normalize,
    mission_control_display_response_dry_run,
    production_identity_storage_response_dry_run,
    sandbox_vm_live_poc_response_dry_run,
    sandbox_vm_static_preflight_response_dry_run,
    siem_export_adapter_response_dry_run,
    trusted_host_promotion_response_dry_run,
)
from scripts import (
    public_security_product_positioning_decision_closure_check as public_closure,
)
from scripts.response_dry_run_lock import response_dry_run_lock

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-response-intake-drill.md"
DOC_TITLE = "Enterprise Response Intake Drill"
PUBLIC_REVIEWED_PACKET_HASH = "sha256:" + "8" * 64
FIXTURE_COMMIT = "abcdef1234567890"

DryRun = Callable[[Path], dict[str, Any]]


DRY_RUNS: tuple[tuple[str, str, DryRun], ...] = (
    (
        "ERG-003",
        "sandbox-vm-static-preflight",
        sandbox_vm_static_preflight_response_dry_run.run_dry_run,
    ),
    ("ERG-002", "mission-control-display", mission_control_display_response_dry_run.run_dry_run),
    ("ERG-005", "trusted-host-promotion", trusted_host_promotion_response_dry_run.run_dry_run),
    (
        "ERG-006/ERG-007",
        "production-identity-storage",
        production_identity_storage_response_dry_run.run_dry_run,
    ),
    ("ERG-008", "siem-export-adapter", siem_export_adapter_response_dry_run.run_dry_run),
    ("ERG-009", "compliance-mapping", compliance_mapping_response_dry_run.run_dry_run),
    ("ERG-004", "sandbox-vm-live-poc", sandbox_vm_live_poc_response_dry_run.run_dry_run),
)


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
    status_report = enterprise_response_status_board.build_report(repo_root)
    coverage_report = enterprise_response_normalization_coverage.build_report(repo_root)
    inbox_report = enterprise_response_inbox.build_check_report(repo_root)
    if status_report.get("valid") is not True:
        failures.append("enterprise response status board is not valid")
    if coverage_report.get("valid") is not True:
        failures.append("enterprise response normalization coverage is not valid")
    if inbox_report.get("valid") is not True:
        failures.append("enterprise response inbox is not valid")

    dry_run_rows: list[dict[str, Any]] = []
    for gap, area, dry_run in DRY_RUNS:
        report = dry_run(repo_root)
        row = _dry_run_row(gap, area, report)
        dry_run_rows.append(row)
        if not row["valid"]:
            failures.append(f"{gap} response dry run is not valid")
        if not row["response_restored"]:
            failures.append(f"{gap} response dry run did not restore normalized-response state")
        if row["committed_findings_mutated"]:
            failures.append(f"{gap} response dry run mutated committed findings")
        if row["external_review_recorded"]:
            failures.append(f"{gap} response dry run recorded external review")
        if row["runtime_changes_allowed"]:
            failures.append(f"{gap} response dry run allowed runtime changes")

    public_report = _run_public_positioning_drill(repo_root)
    failures.extend(public_report["failures"])

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    queue_doc = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    inbox_doc = _read(repo_root / "docs/codex/enterprise-response-inbox.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    for phrase in [
        "Status: fixture drill for enterprise response-intake paths.",
        "make enterprise-response-intake-drill",
        "does not record external review",
        "does not close any enterprise lane",
        "does not approve runtime behavior",
        "ERG-010 public/security-product positioning",
    ]:
        if phrase not in doc:
            failures.append(f"enterprise response intake drill doc is missing phrase: {phrase}")
    if "enterprise-response-intake-drill:" not in makefile:
        failures.append("Make target is missing: enterprise-response-intake-drill")
    if (
        "enterprise-response-intake-drill" not in release_check_body
        and "release-check: enterprise-response-intake-drill" not in makefile
    ):
        failures.append("enterprise-response-intake-drill is missing from release-check")
    if "$(MAKE) enterprise-response-intake-drill" not in review_candidate_body:
        failures.append("enterprise-response-intake-drill is missing from review-candidate")
    if "make enterprise-response-intake-drill" not in readme:
        failures.append("README is missing enterprise response intake drill command")
    if DOC_REL not in docs_site:
        failures.append("enterprise response intake drill is missing from docs-site inputs")
    if DOC_REL not in review_docs:
        failures.append("enterprise response intake drill is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise response intake drill")
    if "enterprise-response-intake-drill" not in release_guardrails:
        failures.append("release guardrails do not require enterprise response intake drill")
    if "enterprise-response-intake-drill" not in queue_doc:
        failures.append("enterprise external-review queue is missing intake drill pointer")
    if "enterprise-response-intake-drill" not in inbox_doc:
        failures.append("enterprise response inbox is missing intake drill pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "drill_doc": DOC_REL,
        "tool_count": 24,
        "lane_count": 8,
        "dry_run_count": len(dry_run_rows),
        "normalizer_area_count": coverage_report.get("covered_area_count", 0),
        "response_present_count": status_report.get("response_present_count", 0),
        "closure_ready_count": status_report.get("closure_ready_count", 0),
        "dry_runs": dry_run_rows,
        "public_positioning": public_report,
        "normalizes_fixture_responses": True,
        "writes_fixture_normalized_response_temporarily": True,
        "restores_fixture_response_state": public_report["response_restored"]
        and all(row["response_restored"] for row in dry_run_rows),
        "committed_findings_mutated": False,
        "external_review_recorded": False,
        "closes_enterprise_lanes": False,
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


def _dry_run_row(gap: str, area: str, report: dict[str, Any]) -> dict[str, Any]:
    return {
        "gap": gap,
        "area": area,
        "valid": report.get("valid") is True,
        "response_restored": report.get("response_restored") is True,
        "case_count": len(report.get("cases", {})),
        "cases": report.get("cases", {}),
        "committed_findings_mutated": report.get("committed_findings_mutated") is not False,
        "external_review_recorded": report.get("external_review_recorded") is not False,
        "runtime_changes_allowed": report.get("runtime_changes_allowed") is not False,
    }


def _run_public_positioning_drill(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    with response_dry_run_lock(repo_root, public_closure.NORMALIZED_RESPONSE_REL):
        response_path = repo_root / public_closure.NORMALIZED_RESPONSE_REL
        original = response_path.read_bytes() if response_path.exists() else None
        original_present = original is not None
        cases: dict[str, bool] = {}
        try:
            no_findings = external_response_normalize.normalize_response(
                "# Public positioning review\n\nNo findings.",
                reviewer="dry-run reviewer",
                reviewer_type="fixture",
                source_access="source-level",
                reviewed_commit=FIXTURE_COMMIT,
                reviewed_packet_hash=PUBLIC_REVIEWED_PACKET_HASH,
                area=public_closure.EXPECTED_AREA,
            )
            cases["no_findings_normalizes"] = no_findings["finding_count"] == 0

            try:
                external_response_normalize.normalize_response(
                    _finding_table(
                        finding_id="EXT-SVP-001",
                        severity="medium",
                        area=public_closure.EXPECTED_AREA,
                    ),
                    reviewer="dry-run reviewer",
                    reviewer_type="fixture",
                    source_access="source-level",
                    reviewed_commit=FIXTURE_COMMIT,
                    reviewed_packet_hash=PUBLIC_REVIEWED_PACKET_HASH,
                    area=public_closure.EXPECTED_AREA,
                )
            except external_response_normalize.ExternalResponseNormalizationError:
                cases["wrong_namespace_rejected"] = True
            else:
                cases["wrong_namespace_rejected"] = False

            try:
                external_response_normalize.normalize_response(
                    "# Public positioning review\n\nLooks good.",
                    reviewer="dry-run reviewer",
                    reviewer_type="fixture",
                    source_access="source-level",
                    reviewed_commit=FIXTURE_COMMIT,
                    reviewed_packet_hash=PUBLIC_REVIEWED_PACKET_HASH,
                    area=public_closure.EXPECTED_AREA,
                )
            except external_response_normalize.ExternalResponseNormalizationError:
                cases["missing_findings_statement_rejected"] = True
            else:
                cases["missing_findings_statement_rejected"] = False

            try:
                external_response_normalize.normalize_response(
                    "# Public positioning review\n\nNo findings.\n\nsecret=example",
                    reviewer="dry-run reviewer",
                    reviewer_type="fixture",
                    source_access="source-level",
                    reviewed_commit=FIXTURE_COMMIT,
                    reviewed_packet_hash=PUBLIC_REVIEWED_PACKET_HASH,
                    area=public_closure.EXPECTED_AREA,
                )
            except external_response_normalize.ExternalResponseNormalizationError:
                cases["secret_marker_rejected"] = True
            else:
                cases["secret_marker_rejected"] = False

            response_path.parent.mkdir(parents=True, exist_ok=True)
            favorable_payload = {
                **no_findings,
                "disposition_outcome": public_closure.EXPECTED_OUTCOME,
            }
            _write_response(response_path, favorable_payload)
            favorable_report = public_closure.build_report(repo_root)
            cases["favorable_fixture_reaches_closure_ready"] = (
                favorable_report["valid"] is True and favorable_report["closure_ready"] is True
            )

            high_payload = external_response_normalize.normalize_response(
                _finding_table(
                    finding_id="EXT-PUBLIC-POSITIONING-001",
                    severity="high",
                    area=public_closure.EXPECTED_AREA,
                ),
                reviewer="dry-run reviewer",
                reviewer_type="fixture",
                source_access="source-level",
                reviewed_commit=FIXTURE_COMMIT,
                reviewed_packet_hash=PUBLIC_REVIEWED_PACKET_HASH,
                area=public_closure.EXPECTED_AREA,
            )
            _write_response(
                response_path,
                {**high_payload, "disposition_outcome": public_closure.EXPECTED_OUTCOME},
            )
            high_report = public_closure.build_report(repo_root)
            cases["critical_high_finding_blocks_closure"] = (
                high_report["valid"] is False and high_report["closure_ready"] is False
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
            failures.append("public positioning response path was not restored")
        if not restored_original:
            failures.append("public positioning response content was not restored")
        for case, passed in cases.items():
            if not passed:
                failures.append(f"public positioning drill case failed: {case}")

        return {
            "area": public_closure.EXPECTED_AREA,
            "finding_namespace": public_closure.EXPECTED_NAMESPACE,
            "normalized_response_path": public_closure.NORMALIZED_RESPONSE_REL,
            "valid": not failures,
            "failures": failures,
            "case_count": len(cases),
            "cases": cases,
            "original_response_present": original_present,
            "response_restored": not any("restored" in failure for failure in failures),
            "committed_findings_mutated": False,
            "external_review_recorded": False,
            "erg_010_closed": False,
            "runtime_changes_allowed": False,
            "public_security_product_positioning_allowed": False,
            "new_power_classes_allowed": False,
        }


def _finding_table(*, finding_id: str, severity: str, area: str) -> str:
    return "\n".join(
        [
            "# Public positioning review",
            "",
            "| Finding ID | Severity | Area | Affected files/functions | "
            "Blocking status | Disposition | Recommended fix |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            f"| {finding_id} | {severity} | {area} | docs/codex/README.md | "
            "should-fix | open | dry-run fixture |",
        ]
    )


def _write_response(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise response intake drill",
        f"valid: {str(report['valid']).lower()}",
        f"drill_doc: {report['drill_doc']}",
        f"tool_count: {report['tool_count']}",
        f"lane_count: {report['lane_count']}",
        f"dry_run_count: {report['dry_run_count']}",
        f"normalizer_area_count: {report['normalizer_area_count']}",
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        f"normalizes_fixture_responses: {str(report['normalizes_fixture_responses']).lower()}",
        "writes_fixture_normalized_response_temporarily: "
        f"{str(report['writes_fixture_normalized_response_temporarily']).lower()}",
        "restores_fixture_response_state: "
        f"{str(report['restores_fixture_response_state']).lower()}",
        f"committed_findings_mutated: {str(report['committed_findings_mutated']).lower()}",
        f"external_review_recorded: {str(report['external_review_recorded']).lower()}",
        f"closes_enterprise_lanes: {str(report['closes_enterprise_lanes']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "dry_runs:",
    ]
    for row in report["dry_runs"]:
        lines.append(
            f"- {row['gap']} {row['area']}: valid={str(row['valid']).lower()} "
            f"cases={row['case_count']} restored={str(row['response_restored']).lower()}"
        )
    lines.append("public_positioning_cases:")
    lines.extend(
        f"- {case}: {str(passed).lower()}"
        for case, passed in report["public_positioning"]["cases"].items()
    )
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

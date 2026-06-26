"""Validate the fail-closed production identity/storage disposition closure gate."""

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
DOC_REL = "docs/codex/production-identity-storage-disposition-closure-gate.md"
DOC_NAME = "production-identity-storage-disposition-closure-gate.md"
NORMALIZED_RESPONSE_REL = "var/review-runs/production-identity-storage/normalized-response.json"
EXPECTED_AREA = "production-identity-storage"
EXPECTED_NAMESPACE = "EXT-PROD-IAM-STORAGE-###"
EXPECTED_OUTCOME = "continue_architecture_planning"
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

REQUIRED_PHRASES = [
    "Status: fail-closed closure gate for planning-only `ERG-006` and `ERG-007`.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "make production-identity-storage-disposition-closure-check",
    NORMALIZED_RESPONSE_REL,
    "ithildin.external_review.normalized_response",
    "reviewed area: `production-identity-storage`",
    "source-level` or `packet-and-source`",
    "finding namespace: `EXT-PROD-IAM-STORAGE-###`",
    "can_close_source_rows: true",
    "mutates_findings: false",
    "closes_external_review: false",
    "no critical/high findings",
    "disposition_outcome: continue_architecture_planning",
    "closure_ready: false",
    "erg_006_status: planning_only",
    "erg_007_status: planning_only",
    "implementation_planning_allowed: false",
    "production_identity_allowed: false",
    "runtime_postgres_allowed: false",
    "ready_for_architecture_decision_record",
    "separate committed triage update",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "implementation planning",
    "runtime implementation",
    "production IAM",
    "enterprise RBAC",
    "tenant/team authorization runtime behavior",
    "remote admin use",
    "runtime Postgres",
    "database migrations",
    "backup/restore runtime behavior",
    "retention enforcement",
    "hosted control plane",
    "custody-grade audit claims",
    "compliance automation",
    "hosted telemetry",
    "remote MCP",
    "SIEM adapter behavior",
    "sandbox orchestration",
    "local model invocation",
    "trusted-host promotion",
    "shell/Docker/Kubernetes/browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "plugin SDK behavior",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "implementation planning is approved",
    "runtime implementation is approved",
    "production IAM is approved",
    "enterprise RBAC is approved",
    "runtime Postgres is approved",
    "database migrations are approved",
    "backup/restore runtime behavior is approved",
    "retention enforcement is approved",
    "hosted control plane is approved",
    "custody-grade audit is implemented",
    "ERG-006 is closed",
    "ERG-007 is closed",
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
    intake = _read(repo_root / "docs/codex/production-identity-storage-external-response-intake.md")
    disposition_packet = _read(
        repo_root / "docs/codex/production-identity-storage-disposition-packet.md"
    )
    architecture = _read(repo_root / "docs/codex/production-identity-storage-architecture.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("production identity/storage disposition closure gate doc is missing")
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
        (disposition_packet, "production identity/storage disposition packet"),
        (architecture, "production identity/storage architecture"),
    ]:
        if DOC_NAME not in linked_text and DOC_REL not in linked_text:
            failures.append(f"{source_name} is missing {DOC_NAME}")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append(
            "review_docs.REVIEW_DOCS is missing production identity/storage closure gate doc"
        )
    if "production-identity-storage-disposition-closure-check:" not in makefile:
        failures.append(
            "Make target is missing: production-identity-storage-disposition-closure-check"
        )
    release_check_additive = "release-check: production-identity-storage-disposition-closure-check"
    if (
        "production-identity-storage-disposition-closure-check" not in release_check_body
        and release_check_additive not in makefile
    ):
        failures.append(
            "production-identity-storage-disposition-closure-check missing from release-check"
        )
    if "production-identity-storage-disposition-closure-check" not in release_guardrails:
        failures.append(
            "release guardrails do not require production identity/storage closure-check"
        )

    return {
        "valid": not failures,
        "failures": failures,
        "closure_gate_doc": DOC_REL,
        "normalized_response_path": NORMALIZED_RESPONSE_REL,
        "normalized_response_present": response_present,
        "closure_ready": closure_ready,
        "disposition_outcome": response_report["disposition_outcome"],
        "erg_006_status": (
            "planning_only" if not closure_ready else "ready_for_architecture_decision_record"
        ),
        "erg_007_status": (
            "planning_only" if not closure_ready else "ready_for_architecture_decision_record"
        ),
        "allowed_closure_state": "ready_for_architecture_decision_record",
        "tool_count": 24,
        "area": EXPECTED_AREA,
        "finding_namespace": EXPECTED_NAMESPACE,
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
            "reason": "normalized response is absent; ERG-006/ERG-007 remain planning-only",
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
        failures.append("normalized response area is not production-identity-storage")
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
            "normalized response disposition_outcome does not permit architecture continuation"
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
        if not finding_id.startswith("EXT-PROD-IAM-STORAGE-"):
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
        "Ithildin production identity/storage disposition closure check",
        f"valid: {str(report['valid']).lower()}",
        f"closure_gate_doc: {report['closure_gate_doc']}",
        f"normalized_response_path: {report['normalized_response_path']}",
        f"normalized_response_present: {str(report['normalized_response_present']).lower()}",
        f"closure_ready: {str(report['closure_ready']).lower()}",
        f"disposition_outcome: {report['disposition_outcome']}",
        f"erg_006_status: {report['erg_006_status']}",
        f"erg_007_status: {report['erg_007_status']}",
        f"allowed_closure_state: {report['allowed_closure_state']}",
        f"tool_count: {report['tool_count']}",
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
        "backup_restore_runtime_allowed: "
        f"{str(report['backup_restore_runtime_allowed']).lower()}",
        f"retention_enforcement_allowed: {str(report['retention_enforcement_allowed']).lower()}",
        f"hosted_control_plane_allowed: {str(report['hosted_control_plane_allowed']).lower()}",
        "custody_grade_audit_claims_allowed: "
        f"{str(report['custody_grade_audit_claims_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
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

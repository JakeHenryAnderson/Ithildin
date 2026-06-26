"""Validate the fail-closed docs/claims public-preview disposition closure gate."""

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
DOC_REL = "docs/codex/docs-claims-public-preview-disposition-closure-gate.md"
DOC_NAME = "docs-claims-public-preview-disposition-closure-gate.md"
NORMALIZED_RESPONSE_REL = "var/review-runs/docs-claims-public-preview/normalized-response.json"
EXPECTED_AREA = "docs-claims-public-preview"
EXPECTED_NAMESPACE = "EXT-DOCS-CLAIMS-###"
EXPECTED_OUTCOME = "close_docs_claims_for_local_preview"
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

RESIDUAL_ROWS = [
    "Documentation IA",
    "Threat model refresh",
    "v0.4 packet generator",
    "v0.4 external packet",
    "v0.5 roadmap",
    "Capability expansion gate",
    "Evidence-confusion gate",
    "v0.5 threat model delta",
    "v0.5 external review prompt",
    "v0.5 boundary decision draft",
    "v0.5 handoff packet",
    "v0.6 boundary charter",
]

REQUIRED_PHRASES = [
    "Status: fail-closed closure gate for residual docs/claims/public-preview wording rows.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "make docs-claims-public-preview-disposition-closure-check",
    NORMALIZED_RESPONSE_REL,
    "ithildin.external_review.normalized_response",
    "reviewed area: `docs-claims-public-preview`",
    "packet-only`, `source-level`, or `packet-and-source`",
    "finding namespace: `EXT-DOCS-CLAIMS-###`",
    "can_close_source_rows: true",
    "mutates_findings: false",
    "closes_external_review: false",
    "no critical/high findings",
    "disposition_outcome: close_docs_claims_for_local_preview",
    "closure_ready: false",
    "docs_claims_status: external_pending",
    "docs_claims_public_preview_wording_closed: false",
    "capability_expansion_allowed: false",
    "public_security_product_positioning_allowed: false",
    "runtime_changes_allowed: false",
    "closed_local_preview_docs_claims",
    "separate committed matrix update",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "capability expansion",
    "public/security-product positioning",
    "production/security/compliance positioning",
    "production deployment ready wording",
    "sandbox guarantee language",
    "EDR/MDM claims",
    "SIEM custody claims",
    "compliance claims",
    "compliance automation",
    "production identity",
    "enterprise RBAC",
    "runtime Postgres",
    "hosted telemetry",
    "hosted MCP",
    "remote MCP transport/gateway claims",
    "managed model serving",
    "Mission Control runtime behavior",
    "sandbox orchestration",
    "local model invocation",
    "trusted-host promotion",
    "SIEM adapter behavior",
    "compliance mapping runtime behavior",
    "shell/Docker/Kubernetes/browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "plugin SDK behavior",
    "new governed tool powers",
]

FORBIDDEN_PHRASES = [
    "capability expansion is approved",
    "public/security-product positioning is approved",
    "production/security/compliance positioning is approved",
    "production deployment readiness is approved",
    "runtime behavior is approved",
    "new governed tool powers are approved",
    "secure sandbox",
    "production-ready",
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
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    matrix = _read(repo_root / "docs/codex/source-review-closure-matrix.md")
    row_partition = _read(repo_root / "docs/codex/v0.7-external-review-row-partition.md")
    assurance = _read(repo_root / "docs/codex/v1.0-assurance-closure.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("docs/claims public-preview closure gate doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"closure gate doc is missing phrase: {phrase}")
        for row in RESIDUAL_ROWS:
            if row not in text:
                failures.append(f"closure gate doc is missing residual row: {row}")
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
        (review_index, "review-docs index"),
        (matrix, "source-review closure matrix"),
        (row_partition, "v0.7 external-review row partition"),
        (assurance, "v1.0 assurance closure"),
    ]:
        if DOC_NAME not in linked_text and DOC_REL not in linked_text:
            failures.append(f"{source_name} is missing {DOC_NAME}")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("review_docs.REVIEW_DOCS is missing docs/claims closure gate doc")
    if "docs-claims-public-preview-disposition-closure-check:" not in makefile:
        failures.append(
            "Make target is missing: docs-claims-public-preview-disposition-closure-check"
        )
    release_check_additive = (
        "release-check: docs-claims-public-preview-disposition-closure-check"
    )
    if (
        "docs-claims-public-preview-disposition-closure-check" not in release_check_body
        and release_check_additive not in makefile
    ):
        failures.append(
            "docs-claims-public-preview-disposition-closure-check missing from release-check"
        )
    if "docs-claims-public-preview-disposition-closure-check" not in release_guardrails:
        failures.append("release guardrails do not require docs/claims closure-check")

    return {
        "valid": not failures,
        "failures": failures,
        "closure_gate_doc": DOC_REL,
        "normalized_response_path": NORMALIZED_RESPONSE_REL,
        "normalized_response_present": response_present,
        "closure_ready": closure_ready,
        "disposition_outcome": response_report["disposition_outcome"],
        "docs_claims_status": (
            "external_pending" if not closure_ready else "closed_local_preview_docs_claims"
        ),
        "allowed_closure_state": "closed_local_preview_docs_claims",
        "tool_count": 24,
        "area": EXPECTED_AREA,
        "finding_namespace": EXPECTED_NAMESPACE,
        "residual_row_count": len(RESIDUAL_ROWS),
        "docs_claims_public_preview_wording_closed": False,
        "capability_expansion_allowed": False,
        "public_security_product_positioning_allowed": False,
        "production_security_compliance_positioning_allowed": False,
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "new_tool_powers_allowed": False,
        "mission_control_runtime_allowed": False,
        "sandbox_orchestration_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_mapping_runtime_allowed": False,
        "response": response_report,
    }


def _validate_normalized_response(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "failures": [],
            "closure_ready": False,
            "disposition_outcome": None,
            "reason": "normalized response is absent; docs/claims rows remain external-pending",
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
        failures.append("normalized response area is not docs-claims-public-preview")
    if payload.get("source_access") not in {"packet-only", "source-level", "packet-and-source"}:
        failures.append("normalized response source_access is not sufficient for docs closure")
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
        failures.append("normalized response disposition_outcome does not permit docs closure")

    findings = payload.get("findings", [])
    if not isinstance(findings, list):
        failures.append("normalized response findings must be a list")
        findings = []
    for finding in findings:
        if not isinstance(finding, dict):
            failures.append("normalized response contains a non-object finding")
            continue
        finding_id = str(finding.get("finding_id", ""))
        if not finding_id.startswith("EXT-DOCS-CLAIMS-"):
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
        "Ithildin docs/claims public-preview disposition closure check",
        f"valid: {str(report['valid']).lower()}",
        f"closure_gate_doc: {report['closure_gate_doc']}",
        f"normalized_response_path: {report['normalized_response_path']}",
        f"normalized_response_present: {str(report['normalized_response_present']).lower()}",
        f"closure_ready: {str(report['closure_ready']).lower()}",
        f"disposition_outcome: {report['disposition_outcome']}",
        f"docs_claims_status: {report['docs_claims_status']}",
        f"allowed_closure_state: {report['allowed_closure_state']}",
        f"tool_count: {report['tool_count']}",
        f"residual_row_count: {report['residual_row_count']}",
        "docs_claims_public_preview_wording_closed: "
        f"{str(report['docs_claims_public_preview_wording_closed']).lower()}",
        f"capability_expansion_allowed: {str(report['capability_expansion_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        "production_security_compliance_positioning_allowed: "
        f"{str(report['production_security_compliance_positioning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"new_tool_powers_allowed: {str(report['new_tool_powers_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        "compliance_mapping_runtime_allowed: "
        f"{str(report['compliance_mapping_runtime_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

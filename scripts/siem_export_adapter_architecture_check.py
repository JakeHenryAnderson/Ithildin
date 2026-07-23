"""Validate the SIEM export adapter architecture packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    review_docs,
    siem_evidence_design_check,
    siem_export_adapter_compatibility_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/siem-export-adapter-architecture.md"
CONTRACT_START = "<!-- siem-export-adapter-contract:start -->"
CONTRACT_END = "<!-- siem-export-adapter-contract:end -->"
ORDERED_WORK_PACKAGES = [f"SEA-{index:03d}" for index in range(1, 6)]

REQUIRED_PHRASES = [
    "Status: design-only architecture packet for `ERG-008`.",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "`ERG-008`: SIEM-shaped export adapter",
    "siem-shaped-evidence-design.md",
    "Phase 1 Offline Handoff Candidate",
    "operator-retrieved, offline, signed evidence handoff bundle",
    "Authority And Data Flow",
    "canonical audit store remains the authority",
    "Current Source Gap",
    "current local-preview signed audit export does **not** satisfy this candidate",
    "Row position or download order must not be silently promoted",
    "Closed Bundle Layout",
    "ithildin.security_export_manifest.v1",
    "ithildin.security_event.v1",
    "ithildin.security_export_signature.v1",
    "Security Event Envelope",
    "optional principal reference is an opaque server-owned Ithildin principal ID",
    "Category Registry And Mapping Rules",
    "historical binding is immutable",
    "semantic correction is a new canonical audit event",
    "Redaction And Data Minimization",
    "Ordering, Idempotency, And Replay",
    "Failure, Retry, And Backpressure",
    "There is no `delivered`, `accepted_by_siem`, or `in_custody` state",
    "Trust, Key Custody, And Verification",
    "Compatibility Contract",
    "SEA-001 Offline Compatibility Corpus",
    "siem-export-adapter-compatibility-fixtures.md",
    "make siem-export-adapter-compatibility-check",
    "Candidate Work-Package Order",
    "`SEA-001`",
    "`SEA-005`",
    "Future Adapter Architecture Questions",
    "Event Schema Requirements",
    "Delivery Requirements",
    "Export Non-Goals",
    "Required Before Implementation",
    "external/source review",
    "The current decision is `planning_only`.",
    "Runtime adapter implementation remains blocked",
    "does not change `PRD-SIEM-EXPORT-001` from `no_go`",
    "make siem-export-adapter-architecture-check",
]

REQUIRED_DELIVERY_PHRASES = [
    "target adapter type",
    "supported event schema version and compatibility policy",
    "field redaction and denylist rules",
    "retry, dead-letter, and backpressure behavior",
    "delivery authentication model",
    "signing and verification story",
    "idempotency and replay handling",
    "operator-visible diagnostics",
    "deterministic allowlist mapper",
    "there is no persistent incremental cursor",
    "One bundle may cover only one mapper/redaction-policy activation segment",
    "must request separate bundles",
    "out-of-band trusted public key",
]

REQUIRED_NON_EXPORT_PHRASES = [
    "prompts",
    "secrets",
    "file contents",
    "diffs",
    "response bodies",
    "package script values",
    "dependency names",
    "raw sensitive paths",
    "raw tool arguments",
    "model output",
    "private key material",
    "bearer tokens",
    "connection strings",
    "local database contents",
    "raw sandbox internals",
]

FORBIDDEN_PHRASES = [
    "SIEM adapter is implemented",
    "hosted telemetry is enabled",
    "remote delivery is approved",
    "custody-grade audit is implemented",
    "compliance automation is approved",
    "security operations control plane is implemented",
    "public security product approved",
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
    doc_rel = DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    runway = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    decision_register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    evidence_design_report = siem_evidence_design_check.build_report(repo_root)
    compatibility_report = siem_export_adapter_compatibility_check.build_report(repo_root)

    text = ""
    contract: dict[str, Any] = {}
    if not doc_path.exists():
        failures.append("SIEM export adapter architecture doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        normalized_text = " ".join(text.split())
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized_text:
                failures.append(f"SIEM export adapter architecture is missing phrase: {phrase}")
        for phrase in REQUIRED_DELIVERY_PHRASES:
            if phrase not in normalized_text:
                failures.append(
                    f"SIEM export adapter architecture is missing delivery phrase: {phrase}"
                )
        for phrase in REQUIRED_NON_EXPORT_PHRASES:
            if phrase not in normalized_text:
                failures.append(
                    f"SIEM export adapter architecture is missing non-export phrase: {phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    f"SIEM export adapter architecture contains forbidden phrase: {phrase}"
                )
        try:
            contract = _contract(text)
        except ValueError as exc:
            failures.append(f"SIEM export adapter contract is invalid: {exc}")

    expected_contract: dict[str, Any] = {
        "document_type": "offline_signed_evidence_handoff_candidate",
        "schema_version": "1",
        "tool_count": _tool_count(repo_root, failures),
        "decision_status": "planning_only",
        "adapter_profile": "operator_retrieved_offline_signed_bundle",
        "source_authority": "verified_canonical_audit_export",
        "current_signed_export_satisfies_candidate": False,
        "explicit_deployment_epoch_required": True,
        "explicit_source_sequence_required": True,
        "event_schema": "ithildin.security_event.v1",
        "manifest_schema": "ithildin.security_export_manifest.v1",
        "signature_schema": "ithildin.security_export_signature.v1",
        "bundle_layout": "manifest_events_signature_detached",
        "event_identity": "deployment_epoch_plus_canonical_event_id",
        "ordering_scope": "deployment_epoch_audit_sequence",
        "range_selection_model": "stateless_explicit_contiguous_range",
        "range_version_scope": "single_mapper_and_redaction_activation",
        "cross_activation_range_authorized": False,
        "persistent_cursor_authorized": False,
        "mapping_mode": "deterministic_allowlist_only",
        "mapping_version_binding": "immutable_source_sequence_activation",
        "retroactive_remap_authorized": False,
        "unknown_source_event_behavior": "fail_export_range",
        "not_exportable_behavior": "counted_omission_receipt_only",
        "manifest_binds_source_export_digest": True,
        "manifest_binds_event_bytes_digest": True,
        "signature_scope": "canonical_manifest_bytes",
        "embedded_signing_key_trusted": False,
        "remote_delivery_authorized": False,
        "destination_credentials_authorized": False,
        "arbitrary_directory_watch_authorized": False,
        "archive_extraction_required": False,
        "downstream_ack_authoritative": False,
        "automatic_retry_authorized": False,
        "dead_letter_mode": "attempt_receipts_only_no_event_copy",
        "canonical_action_backpressure_authorized": False,
        "partial_bundle_import_authorized": False,
        "signature_algorithm": "ed25519",
        "trusted_key_source": "out_of_band_only",
        "signing_key_custody_selected": False,
        "compatibility_policy": (
            "separate_event_manifest_signature_major_mapper_and_redaction_versions"
        ),
        "ordered_work_packages": ORDERED_WORK_PACKAGES,
        "runtime_implementation_authorized": False,
        "siem_adapter_authorized": False,
        "hosted_telemetry_authorized": False,
        "remote_delivery_claim_authorized": False,
        "custody_claim_authorized": False,
        "compliance_claim_authorized": False,
        "uat_required_now": False,
    }
    for key, expected in expected_contract.items():
        if contract.get(key) != expected:
            failures.append(
                f"SIEM export adapter contract has unexpected {key}: {contract.get(key)!r}"
            )
    unexpected_contract_keys = sorted(set(contract) - set(expected_contract))
    if unexpected_contract_keys:
        failures.append(
            "SIEM export adapter contract has unreviewed keys: "
            + ", ".join(unexpected_contract_keys)
        )

    failures.extend(
        f"SIEM-shaped evidence design: {failure}"
        for failure in evidence_design_report["failures"]
    )
    failures.extend(
        f"SIEM compatibility fixtures: {failure}"
        for failure in compatibility_report["failures"]
    )

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("SIEM export adapter architecture doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("SIEM export adapter architecture doc is missing from docs site")
    if "SIEM Export Adapter Architecture" not in review_index:
        failures.append("review docs index is missing SIEM export adapter architecture")
    if "siem-export-adapter-architecture-check:" not in makefile:
        failures.append("Make target is missing: siem-export-adapter-architecture-check")
    if "siem-export-adapter-architecture-check" not in release_check_body:
        failures.append("siem-export-adapter-architecture-check is missing from release-check")
    if "make siem-export-adapter-architecture-check" not in readme:
        failures.append("README is missing SIEM export adapter architecture command")
    if "siem-export-adapter-architecture.md" not in readme:
        failures.append("README is missing SIEM export adapter architecture doc")
    for container_name, container_text in {
        "enterprise runway": runway,
        "enterprise gap matrix": gap_matrix,
        "post-RC decision register": decision_register,
    }.items():
        if "siem-export-adapter-architecture.md" not in container_text:
            failures.append(
                f"{container_name} is missing SIEM export adapter architecture pointer"
            )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "architecture_doc": doc_rel,
        "erg_008_status": "planning_only",
        "tool_count": 24,
        "candidate_profile_specified": bool(contract),
        "adapter_profile": contract.get("adapter_profile"),
        "event_schema": contract.get("event_schema"),
        "ordered_work_packages": contract.get("ordered_work_packages", []),
        "compatibility_fixture_count": compatibility_report.get("case_count"),
        "compatibility_fixtures_valid": compatibility_report.get("valid"),
        "runtime_changes_allowed": False,
        "siem_adapter_allowed": False,
        "hosted_telemetry_allowed": False,
        "remote_delivery_allowed": False,
        "custody_grade_audit_allowed": False,
        "compliance_claims_allowed": False,
        "security_operations_control_plane_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin SIEM export adapter architecture check",
        f"valid: {str(report['valid']).lower()}",
        f"architecture_doc: {report['architecture_doc']}",
        f"erg_008_status: {report['erg_008_status']}",
        f"tool_count: {report['tool_count']}",
        f"candidate_profile_specified: {str(report['candidate_profile_specified']).lower()}",
        f"adapter_profile: {report['adapter_profile']}",
        f"event_schema: {report['event_schema']}",
        f"compatibility_fixture_count: {report['compatibility_fixture_count']}",
        "compatibility_fixtures_valid: "
        f"{str(report['compatibility_fixtures_valid']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"hosted_telemetry_allowed: {str(report['hosted_telemetry_allowed']).lower()}",
        f"remote_delivery_allowed: {str(report['remote_delivery_allowed']).lower()}",
        f"custody_grade_audit_allowed: {str(report['custody_grade_audit_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
        "security_operations_control_plane_allowed: "
        f"{str(report['security_operations_control_plane_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _contract(text: str) -> dict[str, Any]:
    if text.count(CONTRACT_START) != 1 or text.count(CONTRACT_END) != 1:
        raise ValueError("contract markers must each occur exactly once")
    start_index = text.index(CONTRACT_START)
    end_index = text.index(CONTRACT_END)
    if start_index >= end_index:
        raise ValueError("contract start marker must precede end marker")
    payload_start = start_index + len(CONTRACT_START)
    payload = text[payload_start:end_index].strip()
    try:
        document = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ValueError("contract must be valid JSON") from exc
    if not isinstance(document, dict):
        raise ValueError("contract must be a JSON object")
    return document


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate contract key: {key}")
        document[key] = value
    return document


def _tool_count(repo_root: Path, failures: list[str]) -> int:
    lock_path = repo_root / "tool-manifests.lock.json"
    try:
        lock = json.loads(
            lock_path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError, ValueError):
        failures.append("tool manifest lock is unavailable or ambiguous")
        return -1
    manifests = lock.get("manifests") if isinstance(lock, dict) else None
    if not isinstance(manifests, list):
        failures.append("tool manifest lock has no manifest list")
        return -1
    if len(manifests) != 24:
        failures.append(f"actual governed tool count changed: {len(manifests)}")
    return len(manifests)


if __name__ == "__main__":
    raise SystemExit(main())

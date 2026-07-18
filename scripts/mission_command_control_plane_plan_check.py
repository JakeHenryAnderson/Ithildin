"""Validate the structured Mission Command control-plane planning packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = "mission-command-control-plane-plan-check"
CAPABILITY = "docs/codex/mission-command-control-plane-capability-decision.md"
ARCHITECTURE = "docs/codex/mission-command-control-plane-architecture.md"
TICKETS = "docs/codex/mission-command-control-plane-implementation-tickets.md"
AUTHORIZATION = "docs/codex/mission-command-control-plane-authorization-record.md"
DOCS = (CAPABILITY, ARCHITECTURE, TICKETS, AUTHORIZATION)
CONTRACT_START = "<!-- mission-command-contract:start -->"
CONTRACT_END = "<!-- mission-command-contract:end -->"
ORDERED_TICKETS = [f"MCC-{index:03d}" for index in range(1, 7)]
LIFECYCLE_STATES = {
    "unadmitted",
    "queued",
    "claimed",
    "runner_reported_running",
    "runner_reported_succeeded",
    "runner_reported_failed",
    "canceled",
    "cancel_requested",
    "runner_reported_canceled",
    "claim_expired_review_required",
}
EVIDENCE_STATUSES = {"pending", "complete", "evidence_incomplete"}


class ContractError(ValueError):
    """Raised when a machine-readable packet contract is ambiguous or invalid."""


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    texts: dict[str, str] = {}
    contracts: dict[str, dict[str, Any]] = {}
    for relative in DOCS:
        path = repo_root / relative
        if not path.is_file():
            failures.append(f"missing Mission Command document: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        texts[relative] = text
        try:
            contracts[relative] = _contract(text)
        except ContractError as exc:
            failures.append(f"invalid Mission Command contract in {relative}: {exc}")

    lock_count = _tool_count(repo_root / "tool-manifests.lock.json", failures)
    capability = contracts.get(CAPABILITY, {})
    architecture = contracts.get(ARCHITECTURE, {})
    tickets = contracts.get(TICKETS, {})
    authorization = contracts.get(AUTHORIZATION, {})

    _expect(capability, "document_type", "capability_decision", CAPABILITY, failures)
    _expect(capability, "decision", "approved_for_bounded_implementation", CAPABILITY, failures)
    _expect(capability, "mission_admission_authorized", True, CAPABILITY, failures)
    _expect(capability, "node_signed_delivery_authorized", True, CAPABILITY, failures)
    for key in (
        "freeform_objective_authorized",
        "runner_bridge_authorized",
        "runner_lifecycle_authority",
        "model_provider_authority",
        "arbitrary_host_control_authorized",
        "production_identity_authorized",
        "uat_required_now",
    ):
        _expect(capability, key, False, CAPABILITY, failures)

    _expect(architecture, "document_type", "architecture", ARCHITECTURE, failures)
    _expect(architecture, "database_schema_version", "4", ARCHITECTURE, failures)
    _expect(architecture, "minimum_writer_version", "4", ARCHITECTURE, failures)
    _expect(
        architecture,
        "mission_template_ids",
        ["synthetic_read_review_v1"],
        ARCHITECTURE,
        failures,
    )
    _expect(architecture, "freeform_objective_allowed", False, ARCHITECTURE, failures)
    _expect(architecture, "freeform_report_summary_allowed", False, ARCHITECTURE, failures)
    _expect(architecture, "claim_expiry_requeues", False, ARCHITECTURE, failures)
    _expect(architecture, "quarantined_reports_advance_lifecycle", False, ARCHITECTURE, failures)
    _expect(
        architecture,
        "transition_attempt_statuses",
        ["admission_pending_evidence", "claim_pending_evidence"],
        ARCHITECTURE,
        failures,
    )
    _expect(
        architecture,
        "admission_idempotency_namespace",
        ["requester_principal_id", "requester_identity_generation", "client_request_id"],
        ARCHITECTURE,
        failures,
    )
    _expect(architecture, "runner_bridge_authorized", False, ARCHITECTURE, failures)
    _expect(architecture, "arbitrary_host_control_authorized", False, ARCHITECTURE, failures)
    if set(_string_list(architecture.get("lifecycle_states"))) != LIFECYCLE_STATES:
        failures.append("architecture lifecycle state contract is incomplete or expanded")
    if set(_string_list(architecture.get("evidence_statuses"))) != EVIDENCE_STATUSES:
        failures.append("architecture evidence-status contract is incomplete or expanded")

    _expect(tickets, "document_type", "implementation_tickets", TICKETS, failures)
    _expect(tickets, "ordered_tickets", ORDERED_TICKETS, TICKETS, failures)
    _expect(tickets, "database_schema_version", "4", TICKETS, failures)
    _expect(tickets, "minimum_writer_version", "4", TICKETS, failures)
    for key in (
        "runtime_starts_after_review",
        "evidence_commit_protocol_required",
        "late_report_quarantine_required",
        "signed_cancel_poll_required",
    ):
        _expect(tickets, key, True, TICKETS, failures)
    for key in (
        "freeform_objective_authorized",
        "runner_bridge_authorized",
        "sol_ultra_authorized",
    ):
        _expect(tickets, key, False, TICKETS, failures)

    _expect(authorization, "document_type", "authorization_record", AUTHORIZATION, failures)
    _expect(
        authorization,
        "decision",
        "approved_for_bounded_implementation",
        AUTHORIZATION,
        failures,
    )
    _expect(authorization, "ordered_tickets", ORDERED_TICKETS, AUTHORIZATION, failures)
    for key in (
        "runner_bridge_authorized",
        "arbitrary_host_control_authorized",
        "sol_ultra_authorized",
    ):
        _expect(authorization, key, False, AUTHORIZATION, failures)
    for relative, key in (
        (CAPABILITY, "capability_decision_sha256"),
        (ARCHITECTURE, "architecture_sha256"),
        (TICKETS, "implementation_tickets_sha256"),
    ):
        if relative in texts:
            _expect(
                authorization,
                key,
                f"sha256:{hashlib.sha256(texts[relative].encode('utf-8')).hexdigest()}",
                AUTHORIZATION,
                failures,
            )

    for relative, contract in contracts.items():
        _expect(contract, "schema_version", "1", relative, failures)
        _expect(contract, "tool_count", lock_count, relative, failures)

    _validate_document_tokens(texts, failures)
    _validate_wiring(repo_root, failures)

    mission_admission_authorized = (
        capability.get("mission_admission_authorized") is True
        and authorization.get("decision") == "approved_for_bounded_implementation"
    )
    node_signed_delivery_authorized = (
        capability.get("node_signed_delivery_authorized") is True
        and tickets.get("late_report_quarantine_required") is True
    )
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "documents": list(DOCS),
        "tool_count": lock_count,
        "mission_admission_implementation_authorized": mission_admission_authorized,
        "node_signed_delivery_implementation_authorized": node_signed_delivery_authorized,
        "runner_bridge_authorized": capability.get("runner_bridge_authorized"),
        "runner_lifecycle_authority": capability.get("runner_lifecycle_authority"),
        "model_provider_authority": capability.get("model_provider_authority"),
        "arbitrary_host_control_authorized": capability.get("arbitrary_host_control_authorized"),
        "production_identity_authorized": capability.get("production_identity_authorized"),
        "uat_required_now": capability.get("uat_required_now"),
        "packet_digest_binding_valid": not any("sha256" in failure for failure in failures),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Mission Command control-plane plan check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        "mission_admission_implementation_authorized: "
        f"{str(report['mission_admission_implementation_authorized']).lower()}",
        f"runner_bridge_authorized: {str(report['runner_bridge_authorized']).lower()}",
        "arbitrary_host_control_authorized: "
        f"{str(report['arbitrary_host_control_authorized']).lower()}",
        f"packet_digest_binding_valid: {str(report['packet_digest_binding_valid']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(args.repo_root.resolve())
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


def _contract(text: str) -> dict[str, Any]:
    if text.count(CONTRACT_START) != 1 or text.count(CONTRACT_END) != 1:
        raise ContractError("contract markers must each occur exactly once")
    payload = text.split(CONTRACT_START, 1)[1].split(CONTRACT_END, 1)[0].strip()
    try:
        document = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, ContractError) as exc:
        raise ContractError("contract must be unambiguous JSON") from exc
    if not isinstance(document, dict):
        raise ContractError("contract must be a JSON object")
    return document


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ContractError(f"duplicate contract key: {key}")
        document[key] = value
    return document


def _tool_count(path: Path, failures: list[str]) -> int:
    try:
        document = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError, ContractError):
        failures.append("tool manifest lock is unavailable or ambiguous")
        return -1
    manifests = document.get("manifests") if isinstance(document, dict) else None
    if not isinstance(manifests, list) or not all(isinstance(item, dict) for item in manifests):
        failures.append("tool manifest lock has no closed manifest list")
        return -1
    names = [item.get("name") for item in manifests]
    if not all(isinstance(name, str) and name for name in names) or len(set(names)) != len(names):
        failures.append("tool manifest lock names are missing or duplicated")
        return -1
    if len(manifests) != 24:
        failures.append(f"actual governed tool count changed: {len(manifests)}")
    return len(manifests)


def _validate_document_tokens(texts: dict[str, str], failures: list[str]) -> None:
    required = {
        CAPABILITY: ("server-owned synthetic mission template", "quarantined historical evidence"),
        ARCHITECTURE: (
            "## Evidence Commit Protocol",
            "prior lifecycle state/revision remains unchanged",
            "transition-attempt statuses, not",
            "requester_identity_generation, client_request_id",
            "## Cancellation Delivery Protocol",
            "## Coordinated Migration And Downgrade",
            "restore-only",
            "retired key is denied",
        ),
        TICKETS: (
            *ORDERED_TICKETS,
            "late-report negative transcripts",
            "before/after mission finalization",
        ),
        AUTHORIZATION: ("exact SHA-256", "Sol Ultra requires separate prior user approval"),
    }
    for relative, tokens in required.items():
        text = texts.get(relative, "")
        for token in tokens:
            if token not in text:
                failures.append(f"{relative} is missing required token: {token}")


def _validate_wiring(repo_root: Path, failures: list[str]) -> None:
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("Mission Command plan check is missing from release-check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing the Mission Command plan check")
    for relative in DOCS:
        if relative not in readme:
            failures.append(f"README is missing: {relative}")
        if relative not in docs_site:
            failures.append(f"docs site is missing: {relative}")
        if relative not in review_docs:
            failures.append(f"review docs are missing: {relative}")
    if "Mission Command Control Plane" not in review_index:
        failures.append("review docs index is missing the Mission Command Control Plane section")


def _expect(
    document: dict[str, Any],
    key: str,
    expected: object,
    relative: str,
    failures: list[str],
) -> None:
    if document.get(key) != expected:
        failures.append(f"{relative} contract {key} must equal {expected!r}")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return []
    return value


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


if __name__ == "__main__":
    raise SystemExit(main())

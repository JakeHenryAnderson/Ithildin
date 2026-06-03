"""Validate the local-preview accepted-risk register."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTER_JSON = ROOT / "docs/codex/accepted-risk-register.json"
REGISTER_DOC = ROOT / "docs/codex/accepted-risk-register.md"

REQUIRED_RISK_IDS = {
    "AR-001",
    "AR-002",
    "AR-003",
    "AR-004",
    "AR-005",
    "AR-006",
    "AR-007",
    "AR-008",
    "AR-009",
    "AR-010",
}
ALLOWED_SEVERITIES = {"informational", "low", "medium"}
ALLOWED_STATUSES = {
    "accepted_local_preview",
    "accepted_deferred",
    "closed_local_preview",
    "deferred_until_external_review",
    "reviewed_local_preview",
}
FORBIDDEN_ACCEPTANCE_PHRASES = [
    "allows capability expansion",
    "approves new tool powers",
    "production ready",
    "production identity approved",
    "runtime postgres enabled",
    "remote mcp enabled",
    "shell execution allowed",
    "docker socket access allowed",
    "kubernetes tools allowed",
    "browser automation allowed",
    "broad filesystem writes allowed",
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
    register_path = repo_root / REGISTER_JSON.relative_to(ROOT)
    doc_path = repo_root / REGISTER_DOC.relative_to(ROOT)
    failures: list[str] = []

    if not register_path.exists():
        return _report(["accepted-risk register JSON is missing"], [], [])
    if not doc_path.exists():
        return _report(["accepted-risk register document is missing"], [], [])

    try:
        register = json.loads(register_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _report([f"accepted-risk register JSON is invalid: {exc}"], [], [])

    risks = register.get("risks", [])
    if not isinstance(risks, list):
        failures.append("accepted-risk register risks must be a list")
        risks = []

    ids: list[str] = []
    undispositioned_ids: list[str] = []
    reviewed_external_review_ids: list[str] = []
    accepted_deferred_ids: list[str] = []
    blocks_public_preview_ids: list[str] = []
    blocks_capability_design_ids: list[str] = []
    for index, risk in enumerate(risks, start=1):
        if not isinstance(risk, dict):
            failures.append(f"risk #{index} must be an object")
            continue
        risk_id = str(risk.get("id", ""))
        ids.append(risk_id)
        failures.extend(_validate_risk(risk, index))
        if _has_review_closure(risk):
            reviewed_external_review_ids.append(risk_id)
        elif _has_accepted_deferral(risk):
            accepted_deferred_ids.append(risk_id)
            if risk.get("blocks_public_preview") is True:
                blocks_public_preview_ids.append(risk_id)
            if risk.get("blocks_capability_design") is True:
                blocks_capability_design_ids.append(risk_id)
        elif risk.get("external_review_required_before_closure") is True:
            undispositioned_ids.append(risk_id)

    duplicate_ids = sorted({risk_id for risk_id in ids if ids.count(risk_id) > 1})
    if duplicate_ids:
        failures.append(f"duplicate accepted-risk IDs: {', '.join(duplicate_ids)}")

    missing_ids = sorted(REQUIRED_RISK_IDS.difference(ids))
    if missing_ids:
        failures.append(f"missing required accepted-risk IDs: {', '.join(missing_ids)}")

    doc_text = doc_path.read_text(encoding="utf-8")
    for risk_id in REQUIRED_RISK_IDS:
        if risk_id not in doc_text:
            failures.append(f"accepted-risk doc does not mention {risk_id}")
    for required_phrase in [
        "does not approve capability expansion",
        "does not close external source review",
        "not production authorization",
        "not external notarization",
    ]:
        if required_phrase not in doc_text:
            failures.append(f"accepted-risk doc is missing phrase: {required_phrase}")

    combined = f"{json.dumps(register, sort_keys=True)}\n{doc_text}".lower()
    for phrase in FORBIDDEN_ACCEPTANCE_PHRASES:
        if phrase in combined:
            failures.append(f"accepted-risk register contains forbidden phrase: {phrase}")

    return _report(
        failures,
        risks,
        undispositioned_ids,
        reviewed_external_review_ids,
        accepted_deferred_ids,
        blocks_public_preview_ids,
        blocks_capability_design_ids,
    )


def _validate_risk(risk: dict[str, Any], index: int) -> list[str]:
    failures: list[str] = []
    required_fields = {
        "id",
        "title",
        "severity",
        "status",
        "accepted_scope",
        "risk",
        "rationale",
        "mitigations",
        "external_review_required_before_closure",
        "revisit_trigger",
    }
    missing = sorted(required_fields.difference(risk))
    if missing:
        failures.append(f"risk #{index} is missing fields: {', '.join(missing)}")
        return failures

    risk_id = str(risk["id"])
    if not risk_id.startswith("AR-"):
        failures.append(f"{risk_id} must use AR- prefix")
    if risk["severity"] not in ALLOWED_SEVERITIES:
        failures.append(f"{risk_id} uses unacceptable severity {risk['severity']!r}")
    if risk["status"] not in ALLOWED_STATUSES:
        failures.append(f"{risk_id} uses invalid status {risk['status']!r}")
    if not str(risk["accepted_scope"]).startswith("v0.1 local-preview"):
        failures.append(f"{risk_id} accepted scope must stay within v0.1 local-preview")
    if not isinstance(risk["mitigations"], list) or not risk["mitigations"]:
        failures.append(f"{risk_id} must include at least one mitigation")
    if (
        risk["external_review_required_before_closure"] is not True
        and not _has_review_closure(risk)
        and not _has_accepted_deferral(risk)
    ):
        failures.append(
            f"{risk_id} must require external review before closure or record "
            "closed local-preview review evidence or accepted-deferred rationale"
        )
    if not str(risk["revisit_trigger"]).strip():
        failures.append(f"{risk_id} must include a revisit trigger")
    return failures


def _has_review_closure(risk: dict[str, Any]) -> bool:
    return (
        risk.get("external_review_required_before_closure") is False
        and risk.get("status") in {"reviewed_local_preview", "closed_local_preview"}
        and risk.get("external_review_closure") == "closed_local_preview"
        and str(risk.get("closure_finding", "")).startswith("EXT-")
        and bool(str(risk.get("closure_notes", "")).strip())
    )


def _has_accepted_deferral(risk: dict[str, Any]) -> bool:
    return (
        risk.get("external_review_required_before_closure") is False
        and risk.get("status") == "accepted_deferred"
        and risk.get("external_review_closure") == "accepted_deferred"
        and bool(str(risk.get("disposition_rationale", "")).strip())
        and bool(str(risk.get("owner", "")).strip())
        and bool(str(risk.get("revisit_criteria", "")).strip())
        and isinstance(risk.get("blocked_claims"), list)
        and bool(risk.get("blocked_claims"))
        and isinstance(risk.get("linked_reviews"), list)
        and bool(risk.get("linked_reviews"))
    )


def _report(
    failures: list[str],
    risks: list[Any],
    undispositioned_ids: list[str],
    reviewed_external_review_ids: list[str] | None = None,
    accepted_deferred_ids: list[str] | None = None,
    blocks_public_preview_ids: list[str] | None = None,
    blocks_capability_design_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "risk_count": len(risks),
        "open_external_review_ids": undispositioned_ids,
        "undispositioned_external_review_ids": undispositioned_ids,
        "undispositioned_ids": undispositioned_ids,
        "reviewed_external_review_ids": reviewed_external_review_ids or [],
        "closed_local_preview_ids": reviewed_external_review_ids or [],
        "accepted_deferred_ids": accepted_deferred_ids or [],
        "blocks_public_preview_ids": blocks_public_preview_ids or [],
        "blocks_capability_design_ids": blocks_capability_design_ids or [],
        "capability_expansion_approved": False,
        "external_source_review_closed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin accepted-risk register check",
        f"valid: {str(report['valid']).lower()}",
        f"risk_count: {report['risk_count']}",
        f"undispositioned_external_review_ids: {len(report['undispositioned_ids'])}",
        f"reviewed_external_review_ids: {len(report['reviewed_external_review_ids'])}",
        f"accepted_deferred_ids: {len(report['accepted_deferred_ids'])}",
        "accepted_deferred_risks_are_not_closed: "
        f"{str(bool(report['accepted_deferred_ids'])).lower()}",
        f"blocks_public_preview_ids: {len(report['blocks_public_preview_ids'])}",
        f"blocks_capability_design_ids: {len(report['blocks_capability_design_ids'])}",
        "capability_expansion_approved: false",
        "external_source_review_closed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate the fixed Ithildin Enterprise Track E1 completion contract."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("docs/codex/enterprise-e1-completion-contract.json")
DOC_REL = Path("docs/codex/enterprise-e1-completion-contract.md")
SOURCE_BRANCH = "origin/codex/lv1-007-candidate-uat"
SOURCE_COMMIT = "0ef2fae9a06da7455a25017e5773caa52e7c8db6"
LOCAL_V1_RUNTIME_CANDIDATE = "ab4162d8f4b6d3f45a68f33316f4b765a45765db"
PIS_WAIT_ACTION = (
    "await_external_operator_target_and_signed_receipt_inputs_before_separate_"
    "collection_action_authority"
)
OUTCOME_IDS = tuple(f"E1-O{index}" for index in range(1, 7))
MILESTONE_IDS = tuple(f"E1-M{index}" for index in range(1, 7))
ALLOWED_STATUSES = {"not_started", "in_progress", "complete"}
EXPECTED_TITLES = (
    "Reproducible single-site deployment",
    "Versioned policy and Node-configuration distribution",
    "Safe upgrade, rollback, and recovery",
    "Authoritative mission and fleet operations cockpit",
    "Bounded operational evidence export",
    "Exact candidate qualification and UAT handoff",
)
EXPECTED_NONCLAIMS = {
    "production identity",
    "runtime PostgreSQL",
    "high availability",
    "hosted operation",
    "whole-host coverage",
    "SIEM custody",
    "hosted telemetry",
    "external notarization",
    "compliance automation",
    "enterprise production readiness",
    "Local v1 release acceptance",
    "human UAT completion",
}
EXPECTED_AUTHORITY_FIELDS = {
    "arbitrary_host_control_allowed",
    "docker_lifecycle_authority_allowed",
    "kubernetes_authority_allowed",
    "production_identity_allowed",
    "runtime_postgres_allowed",
    "hosted_telemetry_allowed",
    "remote_mcp_hosting_allowed",
    "sandbox_orchestration_allowed",
    "siem_delivery_allowed",
    "compliance_automation_allowed",
    "public_security_product_claims_allowed",
    "production_promotion_allowed",
    "enterprise_production_ready",
    "local_v1_release_accepted",
}


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
    contract = load_contract(repo_root / CONTRACT_REL, failures)
    failures.extend(validate_contract(contract, repo_root))
    doc = _read_text(repo_root / DOC_REL, failures)
    readme = _read_text(repo_root / "README.md", failures)
    makefile = _read_text(repo_root / "Makefile", failures)
    review_docs = _read_text(repo_root / "scripts/review_docs.py", failures)
    docs_site = _read_text(repo_root / "scripts/build_docs_site.py", failures)

    doc_path = DOC_REL.as_posix()
    if CONTRACT_REL.name not in doc:
        failures.append("E1 completion document does not link the machine contract")
    progress = contract.get("progress") if isinstance(contract, dict) else None
    outcome_count = progress.get("outcomes_complete") if isinstance(progress, dict) else "invalid"
    milestone_count = (
        progress.get("milestones_complete") if isinstance(progress, dict) else "invalid"
    )
    if (
        f"Outcomes complete: `{outcome_count}/6`" not in doc
        or f"Milestones complete: `{milestone_count}/6`" not in doc
    ):
        failures.append("E1 completion document does not use current count-based progress")
    if "%" in doc:
        failures.append("E1 completion document contains percentage-based progress")
    for identifier, title in zip(OUTCOME_IDS, EXPECTED_TITLES, strict=True):
        if identifier not in doc or title not in doc:
            failures.append(f"E1 completion document is missing {identifier} or its fixed title")
    if doc_path not in readme:
        failures.append("README.md does not link the E1 completion contract")
    if "Active enterprise delivery track: **Ithildin Enterprise Track E1**" not in readme:
        failures.append("README.md does not identify Enterprise Track E1")
    if "enterprise-e1-contract-check:" not in makefile:
        failures.append("Makefile does not wire enterprise-e1-contract-check")
    if "enterprise-e1-milestone-check:" not in makefile:
        failures.append("Makefile does not wire enterprise-e1-milestone-check")
    if doc_path not in review_docs:
        failures.append("E1 completion contract is missing from review docs")
    if doc_path not in docs_site:
        failures.append("E1 completion contract is missing from docs-site inputs")

    source_exists = _git_ok(repo_root, "cat-file", "-e", f"{SOURCE_COMMIT}^{{commit}}")
    source_is_ancestor = source_exists and _git_ok(
        repo_root, "merge-base", "--is-ancestor", SOURCE_COMMIT, "HEAD"
    )
    current_branch = _git_one(repo_root, "branch", "--show-current")
    if not source_exists:
        failures.append("E1 source commit is unavailable")
    if not source_is_ancestor:
        failures.append("E1 source commit is not an ancestor of HEAD")
    if current_branch in {"codex/lv1-007-candidate-uat", ""}:
        failures.append("E1 work is not on an isolated named branch")

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append("E1 governed tool count is not 24")

    outcomes = contract.get("outcomes") if isinstance(contract, dict) else []
    milestones = contract.get("milestones") if isinstance(contract, dict) else []
    outcome_statuses = _status_map(outcomes)
    milestone_statuses = _status_map(milestones)
    outcomes_complete = sum(status == "complete" for status in outcome_statuses.values())
    milestones_complete = sum(status == "complete" for status in milestone_statuses.values())
    return {
        "valid": not failures,
        "failures": failures,
        "track_id": (
            contract.get("track_id", "invalid") if isinstance(contract, dict) else "invalid"
        ),
        "source_commit": SOURCE_COMMIT,
        "source_commit_exists": source_exists,
        "source_commit_is_ancestor": source_is_ancestor,
        "current_branch": current_branch,
        "tool_count": tool_count,
        "outcomes_complete": outcomes_complete,
        "outcomes_total": len(outcome_statuses),
        "milestones_complete": milestones_complete,
        "milestones_total": len(milestone_statuses),
        "outcome_statuses": outcome_statuses,
        "milestone_statuses": milestone_statuses,
        "next_action": (
            contract.get("next_action", "invalid") if isinstance(contract, dict) else "invalid"
        ),
        "candidate_gate_complete": _nested_bool(
            contract, "qualification", "candidate_gate_complete"
        ),
        "independent_review_complete": _nested_bool(
            contract, "qualification", "independent_review_complete"
        ),
        "human_uat_packet_ready": _nested_bool(
            contract, "qualification", "human_uat_packet_ready"
        ),
        "human_uat_complete": _nested_bool(contract, "qualification", "human_uat_complete"),
        "pis_collection_action_authority": _nested_bool(
            contract, "pis_wait", "collection_action_authority"
        ),
    }


def load_contract(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        failures.append(f"E1 completion contract cannot be loaded: {exc}")
        return {}
    if not isinstance(document, dict):
        failures.append("E1 completion contract must be an object")
        return {}
    return document


def validate_contract(contract: dict[str, Any], repo_root: Path) -> list[str]:
    failures: list[str] = []
    expected_top = {
        "schema_version",
        "track_id",
        "title",
        "source",
        "tool_count",
        "milestone_order",
        "outcomes",
        "milestones",
        "progress",
        "pis_wait",
        "qualification",
        "authority",
        "nonclaims",
        "next_action",
    }
    if set(contract) != expected_top:
        failures.append("E1 completion contract top-level keys are not closed")
    if contract.get("schema_version") != "1" or contract.get("track_id") != "E1":
        failures.append("E1 completion contract identity is invalid")
    source = contract.get("source")
    expected_source = {
        "branch": SOURCE_BRANCH,
        "starting_commit": SOURCE_COMMIT,
        "local_v1_runtime_candidate": LOCAL_V1_RUNTIME_CANDIDATE,
    }
    if source != expected_source:
        failures.append("E1 source binding is not exact")
    if contract.get("tool_count") != 24:
        failures.append("E1 completion contract tool count is not 24")
    if contract.get("milestone_order") != list(MILESTONE_IDS):
        failures.append("E1 milestone order is not exact")

    outcomes = contract.get("outcomes")
    if not isinstance(outcomes, list) or len(outcomes) != 6:
        failures.append("E1 completion contract must contain exactly six outcomes")
        outcomes = []
    milestones = contract.get("milestones")
    if not isinstance(milestones, list) or len(milestones) != 6:
        failures.append("E1 completion contract must contain exactly six milestones")
        milestones = []
    outcome_statuses = _validate_outcomes(outcomes, repo_root, failures)
    milestone_statuses = _validate_milestones(milestones, failures)
    for index, milestone_id in enumerate(MILESTONE_IDS):
        if any(
            milestone_statuses.get(later) == "complete"
            for later in MILESTONE_IDS[index + 1 :]
        ) and milestone_statuses.get(milestone_id) != "complete":
            failures.append("E1 milestone completion is out of fixed order")
            break

    progress = contract.get("progress")
    expected_progress = {
        "outcomes_complete": sum(status == "complete" for status in outcome_statuses.values()),
        "outcomes_total": 6,
        "milestones_complete": sum(
            status == "complete" for status in milestone_statuses.values()
        ),
        "milestones_total": 6,
    }
    if progress != expected_progress:
        failures.append("E1 count-based progress does not match outcome and milestone states")
    pis_wait = contract.get("pis_wait")
    if pis_wait != {
        "next_action": PIS_WAIT_ACTION,
        "external_inputs_present": False,
        "collection_action_authority": False,
    }:
        failures.append("E1 contract does not preserve the exact PIS external-input wait")
    qualification = contract.get("qualification")
    expected_qualification_keys = {
        "candidate_commit",
        "candidate_gate_complete",
        "independent_review_complete",
        "human_uat_packet_ready",
        "human_uat_complete",
    }
    if not isinstance(qualification, dict) or set(qualification) != expected_qualification_keys:
        failures.append("E1 qualification keys are not closed")
        qualification = {}
    if qualification.get("human_uat_complete") is not False:
        failures.append("E1 human UAT must remain false in the implementation contract")
    if any(
        qualification.get(field) not in {False, None}
        for field in (
            "candidate_gate_complete",
            "independent_review_complete",
            "human_uat_packet_ready",
        )
    ):
        candidate = qualification.get("candidate_commit")
        if not isinstance(candidate, str) or len(candidate) != 40:
            failures.append("E1 qualification evidence requires an exact candidate commit")
    if outcome_statuses.get("E1-O6") == "complete" and not all(
        qualification.get(field) is True
        for field in (
            "candidate_gate_complete",
            "independent_review_complete",
            "human_uat_packet_ready",
        )
    ):
        failures.append("E1-O6 cannot be complete without candidate, review, and UAT packet gates")
    authority = contract.get("authority")
    if not isinstance(authority, dict) or set(authority) != EXPECTED_AUTHORITY_FIELDS:
        failures.append("E1 authority keys are not closed")
    elif any(value is not False for value in authority.values()):
        failures.append("E1 completion contract grants forbidden authority")
    nonclaims = contract.get("nonclaims")
    if not isinstance(nonclaims, list) or set(nonclaims) != EXPECTED_NONCLAIMS:
        failures.append("E1 nonclaims are not exact")
    expected_next = next(
        (
            milestone
            for milestone in MILESTONE_IDS
            if milestone_statuses.get(milestone) != "complete"
        ),
        "stop_for_human_uat",
    )
    if contract.get("next_action") != expected_next:
        failures.append("E1 next action does not match fixed milestone order")
    return failures


def _validate_outcomes(
    outcomes: list[Any],
    repo_root: Path,
    failures: list[str],
) -> dict[str, str]:
    statuses: dict[str, str] = {}
    expected_keys = {
        "id",
        "milestone_id",
        "title",
        "status",
        "existing_evidence",
        "remaining_requirements",
    }
    for index, item in enumerate(outcomes):
        if not isinstance(item, dict) or set(item) != expected_keys:
            failures.append("E1 outcome keys are not closed")
            continue
        identifier = item.get("id")
        expected_id = OUTCOME_IDS[index]
        expected_milestone = MILESTONE_IDS[index]
        if (
            identifier != expected_id
            or item.get("milestone_id") != expected_milestone
            or item.get("title") != EXPECTED_TITLES[index]
        ):
            failures.append(f"E1 outcome {index + 1} identity is not exact")
        status = item.get("status")
        if not isinstance(status, str) or status not in ALLOWED_STATUSES:
            failures.append(f"{expected_id} status is invalid")
        else:
            statuses[expected_id] = status
        evidence = item.get("existing_evidence")
        if not isinstance(evidence, list) or not evidence:
            failures.append(f"{expected_id} existing evidence is empty")
        else:
            for relative in evidence:
                if not isinstance(relative, str) or not (repo_root / relative).is_file():
                    failures.append(f"{expected_id} evidence path is missing: {relative}")
        remaining = item.get("remaining_requirements")
        if not isinstance(remaining, list) or (status != "complete" and not remaining):
            failures.append(f"{expected_id} remaining requirements are invalid")
    return statuses


def _validate_milestones(
    milestones: list[Any],
    failures: list[str],
) -> dict[str, str]:
    statuses: dict[str, str] = {}
    expected_keys = {"id", "outcome_id", "title", "status"}
    for index, item in enumerate(milestones):
        if not isinstance(item, dict) or set(item) != expected_keys:
            failures.append("E1 milestone keys are not closed")
            continue
        identifier = item.get("id")
        if identifier != MILESTONE_IDS[index] or item.get("outcome_id") != OUTCOME_IDS[index]:
            failures.append(f"E1 milestone {index + 1} identity is not exact")
        status = item.get("status")
        if not isinstance(status, str) or status not in ALLOWED_STATUSES:
            failures.append(f"{MILESTONE_IDS[index]} status is invalid")
        else:
            statuses[MILESTONE_IDS[index]] = status
    return statuses


def _status_map(items: Any) -> dict[str, str]:
    if not isinstance(items, list):
        return {}
    return {
        str(item["id"]): str(item["status"])
        for item in items
        if isinstance(item, dict) and "id" in item and "status" in item
    }


def _nested_bool(contract: dict[str, Any], section: str, field: str) -> bool:
    value = contract.get(section)
    return bool(isinstance(value, dict) and value.get(field) is True)


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _read_text(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        failures.append(f"cannot read {path}: {exc}")
        return ""


def _tool_count(path: Path) -> int:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        manifests = document.get("manifests")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        return -1
    return len(manifests) if isinstance(manifests, list) else -1


def _git_ok(repo_root: Path, *args: str) -> bool:
    return (
        subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _git_one(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Enterprise Track E1 completion contract check",
        f"valid: {str(report['valid']).lower()}",
        f"track_id: {report['track_id']}",
        f"source_commit: {report['source_commit']}",
        f"source_commit_is_ancestor: {str(report['source_commit_is_ancestor']).lower()}",
        f"current_branch: {report['current_branch']}",
        f"tool_count: {report['tool_count']}",
        f"outcomes_complete: {report['outcomes_complete']}/{report['outcomes_total']}",
        f"milestones_complete: {report['milestones_complete']}/{report['milestones_total']}",
        f"next_action: {report['next_action']}",
        f"candidate_gate_complete: {str(report['candidate_gate_complete']).lower()}",
        f"independent_review_complete: {str(report['independent_review_complete']).lower()}",
        f"human_uat_packet_ready: {str(report['human_uat_packet_ready']).lower()}",
        f"human_uat_complete: {str(report['human_uat_complete']).lower()}",
        (
            "pis_collection_action_authority: "
            f"{str(report['pis_collection_action_authority']).lower()}"
        ),
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

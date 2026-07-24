"""Validate the fixed-scope Ithildin Local v1.0 completion contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("docs/codex/local-v1-completion-contract.md")
DISPOSITION_REL = Path("docs/codex/local-v1-release-disposition.json")
OUTCOME_IDS = tuple(f"O{index}" for index in range(1, 9))
MILESTONE_IDS = tuple(f"LV1-{index:03d}" for index in range(8))
ALLOWED_OUTCOME_STATUSES = {
    "not_started",
    "in_progress",
    "blocked",
    "candidate_ready",
    "complete",
}
LOCAL_V1_CANDIDATE_TARGETS = (
    "local-v1-contract-check",
    "release-context",
    "manifest-lock-check",
    "release-guardrails",
    "tool-surface-invariant-gate",
    "no-new-powers-guardrail",
    "policy-test",
    "policy-parity",
    "filesystem-contract-check",
    "release-evidence-gate",
    "evidence-contracts-check",
    "determinism-check",
    "adversarial-corpus-check",
    "resource-limit-check",
    "local-v1-runtime-trust-check",
    "hermes-governance-poc-plan-check",
    "local-v1-hermes-evidence-check",
    "track-b-node-evidence-check",
    "track-b-node-configuration-evidence-check",
    "track-b-node-governed-access-evidence-check",
    "track-b-node-configuration-trust-rotation-evidence-check",
    "track-b-node-version-posture-evidence-check",
    "track-b-node-identity-key-rotation-evidence-check",
    "track-b-node-service-lifecycle-evidence-check",
    "track-b-node-release-artifact-evidence-check",
    "mission-command-control-plane-plan-check",
    "mission-command-control-plane-poc-check",
    "mission-command-control-plane-focused-gates",
    "test-fast",
    "lint",
    "typecheck",
    "ui-test",
    "local-v1-ui-production-build",
    "docs-site",
    "agent-workflow-check",
)
ALLOWED_DESCENDANT_PURPOSES = (
    "candidate_gate_record",
    "independent_review_record",
    "human_uat_record",
    "human_acceptance_record",
)
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_CONTRACT_PHRASES = (
    "Status: active fixed-scope delivery contract.",
    "Active delivery target: `Ithildin Local v1.0`",
    "Current governed tool count: `24`",
    "Release outcomes complete:",
    "Critical-path milestones complete:",
    "Latest completed milestone:",
    "Active next action:",
    "Local-v1 release gate:",
    "Human UAT:",
    "Release acceptance:",
    "Release Disposition Evidence",
    "docs/codex/local-v1-release-disposition.json",
    "Status prose cannot qualify a candidate or authorize release",
    "disposition parent is the immediate parent of the commit carrying the final record",
    "Outcome counts, not percentage bands, are the active delivery forecast.",
    "self-hosted, single-operator governance gateway and operations cockpit",
    "technically capable, security-conscious user",
    "bounded 24-tool surface",
    "does not sandbox the host, control arbitrary processes, or prove that an agent",
    "cannot act outside Ithildin",
    "Gateway policy, approval, execution, and audit remain authoritative",
    "Node connectivity, runner-reported state, and model-provider state",
    "Golden Scenario",
    "real Hermes MCP leg and the authenticated Node/Mission Command leg",
    "must not claim a real Hermes-through-Node mission",
    "PIS external target and signed-receipt wait remains valid enterprise lineage",
    "does not block Local v1.0",
    "`MCC-007` remains a later, separate bounded capability decision",
    "this contract does not authorize its implementation",
    "production PostgreSQL",
    "enterprise tenancy",
    "multi-user RBAC",
    "production credential",
    "hosted or remote-operation claims",
    "managed fleet rollout or Node self-update",
    "SIEM custody integrations",
    "compliance automation",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "filesystem non-bypass",
    "arbitrary shell, process, browser, network, or broad filesystem authority",
    "Kubernetes or Docker-socket control",
    "`ERG-009`, PIS completion, enterprise completion, and public security-product claims",
    "`required_for_local_v1`, `post_v1`, `optional`, or",
    "`externally_blocked`",
    "Changing the eight-outcome denominator, the 24-tool surface, a governed power",
    "explicit user direction",
    "All runtime, release, promotion, credential-custody, external-system, and UAT authorities",
    "remain false",
    "make local-v1-inner-check",
    "make local-v1-milestone-check",
    "make local-v1-candidate-check",
    "make local-v1-release-check",
    "fixed target inventory",
    "Evidence checkers do not reproduce live evidence",
    "make release-check",
    "While any required outcome remains incomplete",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--require-candidate",
        action="store_true",
        help="fail unless outcomes O1-O7 are complete and O8 is in candidate work",
    )
    parser.add_argument(
        "--require-release",
        action="store_true",
        help="fail unless all eight outcomes, human UAT, and release acceptance are complete",
    )
    args = parser.parse_args()

    report = build_report(
        ROOT,
        require_candidate=args.require_candidate,
        require_release=args.require_release,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(
    repo_root: Path,
    *,
    require_candidate: bool = False,
    require_release: bool = False,
    contract_override: str | None = None,
    disposition_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    contract = (
        contract_override
        if contract_override is not None
        else _read(repo_root / CONTRACT_REL, failures)
    )
    contract_failures, outcome_statuses, milestone_statuses = validate_contract_text(
        contract
    )
    failures.extend(contract_failures)
    disposition = (
        disposition_override
        if disposition_override is not None
        else _read_json(repo_root / DISPOSITION_REL, failures)
    )
    disposition_failures, disposition_state = validate_disposition(
        repo_root, disposition
    )
    failures.extend(disposition_failures)

    makefile = _read(repo_root / "Makefile", failures)
    readme = _read(repo_root / "README.md", failures)
    docs_site = _read(repo_root / "scripts/build_docs_site.py", failures)
    review_docs = _read(repo_root / "scripts/review_docs.py", failures)
    review_index = _read(repo_root / "docs/codex/review-docs-index.md", failures)
    lock = _read_json(repo_root / "tool-manifests.lock.json", failures)
    enterprise_progress = _read(
        repo_root / "docs/codex/enterprise-progress-model.md", failures
    )
    enterprise_roadmap = _read(
        repo_root / "docs/codex/enterprise-north-star-roadmap.md", failures
    )
    enterprise_checkpoint = _read(
        repo_root / "docs/codex/enterprise-current-checkpoint.md", failures
    )
    legacy_v1_status = _read(repo_root / "docs/codex/v1.0-rc-status.md", failures)
    legacy_v1_progress = _read(
        repo_root / "docs/codex/v1.0-progress-assessment.md", failures
    )
    legacy_mvp_board = _read(
        repo_root / "docs/codex/technical-mvp-execution-board.md", failures
    )

    contract_path = CONTRACT_REL.as_posix()
    if contract_path not in readme:
        failures.append("README.md does not link the Local-v1 completion contract")
    if "Active delivery target: **Ithildin Local v1.0**" not in readme:
        failures.append("README.md does not identify Local v1.0 as the active delivery target")
    if contract_path not in docs_site:
        failures.append("Local-v1 contract is missing from docs-site inputs")
    if contract_path not in review_docs:
        failures.append("Local-v1 contract is missing from review-doc inputs")
    if DISPOSITION_REL.as_posix() not in review_docs:
        failures.append("Local-v1 disposition is missing from review-doc inputs")
    if "Ithildin Local v1.0 Completion Contract" not in review_index:
        failures.append("Local-v1 contract is missing from the review-docs index")
    if "Local v1.0 Release Disposition" not in review_index:
        failures.append("Local-v1 disposition is missing from the review-docs index")
    active_index_entry = (
        "- [Ithildin Local v1.0 Completion Contract]"
        "(local-v1-completion-contract.md) - active delivery target."
    )
    if active_index_entry not in review_index:
        failures.append("Local-v1 contract is not the first active review-docs index entry")
    start_here = review_index.partition("## Start Here")[2].partition(
        "## Command Center Pilot Design"
    )[0]
    if not start_here.lstrip().startswith(active_index_entry):
        failures.append("review-docs Start Here does not begin with the Local-v1 contract")

    for label, text in (
        ("enterprise progress model", enterprise_progress),
        ("enterprise north-star roadmap", enterprise_roadmap),
        ("enterprise current checkpoint", enterprise_checkpoint),
    ):
        if "Local v1.0 is the active delivery target" not in text:
            failures.append(f"{label} does not defer to the active Local-v1 target")
        if "historical/deferred" not in text:
            failures.append(f"{label} does not label enterprise status historical/deferred")
    for label, text in (
        ("v1.0 RC status", legacy_v1_status),
        ("v1.0 progress assessment", legacy_v1_progress),
        ("technical MVP execution board", legacy_mvp_board),
    ):
        if "Local v1.0 is the active delivery target" not in text:
            failures.append(f"{label} does not defer to the active Local-v1 target")
        if "historical/deferred" not in text:
            failures.append(f"{label} does not label its status historical/deferred")
        if CONTRACT_REL.as_posix() not in text:
            failures.append(f"{label} does not link the Local-v1 contract")

    manifests = lock.get("manifests") if isinstance(lock, dict) else None
    tool_count = len(manifests) if isinstance(manifests, list) else None
    if tool_count != 24:
        failures.append(f"tool manifest lock contains {tool_count!r} tools, expected 24")

    expected_targets = {
        "local-v1-contract-check": (
            "uv run python scripts/local_v1_contract_check.py",
        ),
        "local-v1-inner-check": (
            "$(MAKE) local-v1-contract-check",
            "$(MAKE) manifest-lock-check",
            "$(MAKE) tool-surface-invariant-gate",
            "$(MAKE) no-new-powers-guardrail",
            "tests/test_local_v1_contract.py",
        ),
        "local-v1-milestone-check": (
            "$(MAKE) local-v1-inner-check",
            "$(MAKE) agent-workflow-check",
            "tests/test_docs_site.py",
            "$(MAKE) docs-site",
        ),
        "local-v1-release-check": (
            "$(MAKE) local-v1-milestone-check",
            "uv run python scripts/local_v1_contract_check.py --require-release",
        ),
        "local-v1-candidate-check": (
            "uv run python scripts/local_v1_contract_check.py --require-candidate",
            "$(MAKE) local-v1-milestone-check",
            "$(MAKE) local-v1-candidate-inventory",
            "candidate_tree_clean=true",
            "local_v1_candidate_gate_returncode=0",
        ),
        "local-v1-runtime-trust-check": (
            "tests/test_approval_workflow.py",
            "tests/test_audit_writer.py",
            "tests/test_redaction.py",
            "tests/test_security_regressions.py",
            "tests/test_mission_database_migration.py",
            "tests/test_storage_schema_import.py",
            "tests/test_nodes.py",
        ),
        "local-v1-hermes-evidence-check": (
            "uv run python scripts/hermes_poc_evidence_check.py",
        ),
        "local-v1-ui-production-build": (
            "npm run build --prefix apps/ui",
        ),
    }
    for target, phrases in expected_targets.items():
        body = _target_body(makefile, target)
        if not body:
            failures.append(f"Makefile is missing {target}")
            continue
        for phrase in phrases:
            if phrase not in body:
                failures.append(f"{target} is missing: {phrase}")

    failures.extend(validate_candidate_inventory(makefile))
    return _build_status(
        contract=contract,
        contract_path=contract_path,
        tool_count=tool_count,
        outcome_statuses=outcome_statuses,
        milestone_statuses=milestone_statuses,
        disposition_state=disposition_state,
        failures=failures,
        require_candidate=require_candidate,
        require_release=require_release,
    )


def validate_candidate_inventory(makefile: str) -> list[str]:
    failures: list[str] = []
    inventory_body = _target_body(makefile, "local-v1-candidate-inventory")
    inventory_targets = tuple(
        re.findall(r"^\t\$\(MAKE\) ([a-z0-9][a-z0-9-]*)$", inventory_body, re.MULTILINE)
    )
    if inventory_targets != LOCAL_V1_CANDIDATE_TARGETS:
        failures.append(
            "Local-v1 candidate inventory drifted: "
            f"{inventory_targets!r} != {LOCAL_V1_CANDIDATE_TARGETS!r}"
        )
    forbidden_inventory_fragments = (
        "release-check-slice",
        "production-identity-storage",
        "enterprise-",
        "sandbox-vm",
        "trusted-host",
        "mission-command-control-plane-poc\n",
        "hermes-poc-run",
        "compose-up",
        "compose-down",
    )
    for fragment in forbidden_inventory_fragments:
        if fragment in inventory_body:
            failures.append(f"Local-v1 candidate inventory contains forbidden target: {fragment}")
    return failures


def _build_status(
    *,
    contract: str,
    contract_path: str,
    tool_count: int | None,
    outcome_statuses: dict[str, str],
    milestone_statuses: dict[str, str],
    disposition_state: dict[str, bool],
    failures: list[str],
    require_candidate: bool,
    require_release: bool,
) -> dict[str, Any]:
    complete_count = sum(status == "complete" for status in outcome_statuses.values())
    milestone_complete_count = sum(
        status == "complete" for status in milestone_statuses.values()
    )
    declared_outcome_count = _count_metadata(contract, "Release outcomes complete")
    declared_milestone_count = _count_metadata(
        contract, "Critical-path milestones complete"
    )
    if declared_outcome_count != (complete_count, len(OUTCOME_IDS)):
        failures.append(
            "declared Local-v1 outcome count does not match the outcome table: "
            f"{declared_outcome_count!r} != {(complete_count, len(OUTCOME_IDS))!r}"
        )
    if declared_milestone_count != (milestone_complete_count, len(MILESTONE_IDS)):
        failures.append(
            "declared Local-v1 milestone count does not match the milestone table: "
            f"{declared_milestone_count!r} != "
            f"{(milestone_complete_count, len(MILESTONE_IDS))!r}"
        )
    latest_completed = _scalar_metadata(contract, "Latest completed milestone")
    completed_milestones = [
        milestone_id
        for milestone_id in MILESTONE_IDS
        if milestone_statuses.get(milestone_id) == "complete"
    ]
    expected_latest = completed_milestones[-1] if completed_milestones else "none"
    if latest_completed != expected_latest:
        failures.append(
            "latest completed Local-v1 milestone does not match the milestone table: "
            f"{latest_completed!r} != {expected_latest!r}"
        )
    active_next_action = _scalar_metadata(contract, "Active next action")
    expected_next_action = next(
        (
            milestone_id
            for milestone_id in MILESTONE_IDS
            if milestone_statuses.get(milestone_id) != "complete"
        ),
        "release_decision",
    )
    if active_next_action != expected_next_action:
        failures.append(
            "active Local-v1 next action does not match the first incomplete milestone: "
            f"{active_next_action!r} != {expected_next_action!r}"
        )
    candidate_status_ready = (
        all(outcome_statuses.get(outcome_id) == "complete" for outcome_id in OUTCOME_IDS[:-1])
        and outcome_statuses.get("O8") in {"in_progress", "candidate_ready", "complete"}
    )
    human_uat_status = _scalar_metadata(contract, "Human UAT")
    prose_human_uat_complete = human_uat_status == "complete"
    prose_release_accepted = _scalar_metadata(contract, "Release acceptance") == "true"
    release_status_ready = (
        len(outcome_statuses) == len(OUTCOME_IDS)
        and complete_count == len(OUTCOME_IDS)
        and prose_human_uat_complete
        and prose_release_accepted
    )
    release_ready = release_status_ready and disposition_state["release_evidence_complete"]
    if outcome_statuses.get("O8") == "complete" and not disposition_state[
        "release_evidence_complete"
    ]:
        failures.append("O8 cannot be complete without the bound release disposition evidence")
    if prose_human_uat_complete and not disposition_state["human_uat_evidence_complete"]:
        failures.append("status prose claims human UAT without bound UAT evidence")
    if prose_release_accepted and not disposition_state["human_acceptance_evidence_complete"]:
        failures.append("status prose claims release acceptance without bound human acceptance")
    if (
        _scalar_metadata(contract, "Local-v1 release gate") == "complete"
        and not disposition_state["release_evidence_complete"]
    ):
        failures.append("status prose claims a complete release gate without bound disposition")
    if require_candidate and not candidate_status_ready:
        failures.append(
            "Local-v1 candidate remains blocked: outcomes O1-O7 must be complete and "
            "O8 must record candidate work in progress"
        )
    if require_release and not release_ready:
        failures.append(
            "Local-v1 release remains blocked: all eight outcomes, genuine human UAT, "
            "and explicit release acceptance are required"
        )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "contract_path": contract_path,
        "active_delivery_target": "Ithildin Local v1.0",
        "tool_count": tool_count,
        "outcome_statuses": outcome_statuses,
        "milestone_statuses": milestone_statuses,
        "outcomes_complete": complete_count,
        "outcomes_total": len(OUTCOME_IDS),
        "milestones_complete": milestone_complete_count,
        "milestones_total": len(MILESTONE_IDS),
        "active_next_action": active_next_action,
        "candidate_check_requested": require_candidate,
        "candidate_ready": candidate_status_ready,
        "release_check_requested": require_release,
        "release_ready": release_ready,
        "human_uat_complete": disposition_state["human_uat_evidence_complete"],
        "release_accepted": disposition_state["human_acceptance_evidence_complete"],
        "disposition_path": DISPOSITION_REL.as_posix(),
        "disposition_valid": disposition_state["valid"],
        "candidate_evidence_complete": disposition_state["candidate_evidence_complete"],
        "independent_review_evidence_complete": disposition_state[
            "independent_review_evidence_complete"
        ],
        "release_disposition_complete": disposition_state["release_evidence_complete"],
        "runtime_authority_granted": False,
        "new_governed_powers_authorized": False,
        "pis_wait_blocks_local_v1": False,
    }


def validate_contract_text(
    text: str,
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    failures = [
        f"{CONTRACT_REL.as_posix()} missing phrase: {phrase}"
        for phrase in REQUIRED_CONTRACT_PHRASES
        if not _contains_phrase(text, phrase)
    ]
    if re.search(r"\b\d{1,3}\s*-\s*\d{1,3}%", text):
        failures.append("Local-v1 contract contains a percentage-band delivery estimate")

    outcome_statuses: dict[str, str] = {}
    outcome_pattern = re.compile(
        r"^\| `(O[1-8])` \| [^|]+ \| `([^`]+)` \|", re.MULTILINE
    )
    for outcome_id, status in outcome_pattern.findall(text):
        if outcome_id in outcome_statuses:
            failures.append(f"duplicate Local-v1 outcome row: {outcome_id}")
        outcome_statuses[outcome_id] = status
        if status not in ALLOWED_OUTCOME_STATUSES:
            failures.append(f"invalid Local-v1 outcome status for {outcome_id}: {status}")
    if tuple(sorted(outcome_statuses, key=lambda value: int(value[1:]))) != OUTCOME_IDS:
        failures.append("Local-v1 contract must contain exactly outcome rows O1 through O8")

    milestone_statuses: dict[str, str] = {}
    milestone_pattern = re.compile(
        r"^\| `(LV1-\d{3})` \| [^|]+ \| `([^`]+)` \|", re.MULTILINE
    )
    for milestone_id, status in milestone_pattern.findall(text):
        if milestone_id in milestone_statuses:
            failures.append(f"duplicate Local-v1 milestone row: {milestone_id}")
        milestone_statuses[milestone_id] = status
        if status not in ALLOWED_OUTCOME_STATUSES:
            failures.append(f"invalid Local-v1 milestone status for {milestone_id}: {status}")
    if set(milestone_statuses) != set(MILESTONE_IDS):
        failures.append("Local-v1 contract must contain exactly milestones LV1-000 through LV1-007")
    return failures, outcome_statuses, milestone_statuses


def validate_disposition(
    repo_root: Path, payload: dict[str, Any]
) -> tuple[list[str], dict[str, bool]]:
    failures: list[str] = []
    if not isinstance(payload, dict):
        return ["Local-v1 disposition is not an object"], _empty_disposition_state(False)

    _require_exact_keys(
        payload,
        {
            "schema_version",
            "record_type",
            "record_status",
            "candidate",
            "candidate_gate",
            "independent_review",
            "human_uat",
            "human_acceptance",
            "disposition_lineage",
            "authority",
        },
        "disposition",
        failures,
    )
    if payload.get("schema_version") != "1":
        failures.append("Local-v1 disposition schema_version must be 1")
    if payload.get("record_type") != "ithildin_local_v1_release_disposition":
        failures.append("Local-v1 disposition record_type is invalid")
    if payload.get("record_status") not in {
        "uninitialized",
        "candidate_recorded",
        "reviewed",
        "uat_complete",
        "accepted",
    }:
        failures.append("Local-v1 disposition record_status is invalid")

    candidate = _object(payload, "candidate", failures)
    gate = _object(payload, "candidate_gate", failures)
    review = _object(payload, "independent_review", failures)
    uat = _object(payload, "human_uat", failures)
    acceptance = _object(payload, "human_acceptance", failures)
    lineage = _object(payload, "disposition_lineage", failures)
    authority = _object(payload, "authority", failures)
    _require_exact_keys(
        candidate,
        {
            "frozen_commit",
            "identity_evidence_path",
            "identity_evidence_sha256",
            "clean_tree_observed",
            "clean_tree_observation_method",
            "clean_tree_observation_commit",
        },
        "candidate",
        failures,
    )
    _require_exact_keys(
        gate,
        {"passed", "candidate_commit", "transcript_path", "transcript_sha256"},
        "candidate_gate",
        failures,
    )
    _require_exact_keys(
        review,
        {
            "completed",
            "reviewed_candidate_commit",
            "disposition",
            "record_path",
            "record_sha256",
            "critical_findings",
            "high_findings",
            "medium_findings",
            "low_findings",
        },
        "independent_review",
        failures,
    )
    _require_exact_keys(
        uat,
        {
            "completed",
            "tested_candidate_commit",
            "result",
            "record_path",
            "record_sha256",
        },
        "human_uat",
        failures,
    )
    _require_exact_keys(
        acceptance,
        {
            "accepted",
            "accepted_candidate_commit",
            "record_path",
            "record_sha256",
        },
        "human_acceptance",
        failures,
    )
    _require_exact_keys(
        lineage,
        {
            "disposition_parent_commit",
            "declared_candidate_descendants",
            "allowed_descendant_purposes",
        },
        "disposition_lineage",
        failures,
    )
    _require_exact_keys(
        authority,
        {
            "candidate_qualified",
            "release_allowed",
            "promotion_allowed",
            "production_allowed",
            "uat_authority_inherited",
            "new_governed_powers_allowed",
        },
        "authority",
        failures,
    )
    for label, value in (
        ("candidate.clean_tree_observed", candidate.get("clean_tree_observed")),
        ("candidate_gate.passed", gate.get("passed")),
        ("independent_review.completed", review.get("completed")),
        ("human_uat.completed", uat.get("completed")),
        ("human_acceptance.accepted", acceptance.get("accepted")),
        *(
            (f"authority.{field}", authority.get(field))
            for field in (
                "candidate_qualified",
                "release_allowed",
                "promotion_allowed",
                "production_allowed",
                "uat_authority_inherited",
                "new_governed_powers_allowed",
            )
        ),
    ):
        if not isinstance(value, bool):
            failures.append(f"Local-v1 disposition boolean field is invalid: {label}")
    for label, value in (
        ("candidate.frozen_commit", candidate.get("frozen_commit")),
        ("candidate.identity_evidence_path", candidate.get("identity_evidence_path")),
        ("candidate.identity_evidence_sha256", candidate.get("identity_evidence_sha256")),
        (
            "candidate.clean_tree_observation_method",
            candidate.get("clean_tree_observation_method"),
        ),
        (
            "candidate.clean_tree_observation_commit",
            candidate.get("clean_tree_observation_commit"),
        ),
        ("candidate_gate.candidate_commit", gate.get("candidate_commit")),
        ("candidate_gate.transcript_path", gate.get("transcript_path")),
        ("candidate_gate.transcript_sha256", gate.get("transcript_sha256")),
        (
            "independent_review.reviewed_candidate_commit",
            review.get("reviewed_candidate_commit"),
        ),
        ("independent_review.disposition", review.get("disposition")),
        ("independent_review.record_path", review.get("record_path")),
        ("independent_review.record_sha256", review.get("record_sha256")),
        ("human_uat.tested_candidate_commit", uat.get("tested_candidate_commit")),
        ("human_uat.result", uat.get("result")),
        ("human_uat.record_path", uat.get("record_path")),
        ("human_uat.record_sha256", uat.get("record_sha256")),
        (
            "human_acceptance.accepted_candidate_commit",
            acceptance.get("accepted_candidate_commit"),
        ),
        ("human_acceptance.record_path", acceptance.get("record_path")),
        ("human_acceptance.record_sha256", acceptance.get("record_sha256")),
        (
            "disposition_lineage.disposition_parent_commit",
            lineage.get("disposition_parent_commit"),
        ),
    ):
        if value is not None and not isinstance(value, str):
            failures.append(f"Local-v1 disposition nullable string field is invalid: {label}")
    for field in (
        "critical_findings",
        "high_findings",
        "medium_findings",
        "low_findings",
    ):
        value = review.get(field)
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 0
        ):
            failures.append(
                f"Local-v1 disposition finding count is invalid: independent_review.{field}"
            )

    frozen_commit = candidate.get("frozen_commit")
    candidate_identity_valid = _bound_evidence_valid(
        repo_root,
        candidate.get("identity_evidence_path"),
        candidate.get("identity_evidence_sha256"),
        "candidate identity",
        failures,
    )
    candidate_fields_complete = (
        _is_commit(frozen_commit)
        and candidate.get("clean_tree_observed") is True
        and candidate.get("clean_tree_observation_method") == "candidate_gate_transcript"
        and candidate.get("clean_tree_observation_commit") == frozen_commit
        and candidate_identity_valid
    )
    gate_transcript_valid = _bound_evidence_valid(
        repo_root,
        gate.get("transcript_path"),
        gate.get("transcript_sha256"),
        "candidate gate transcript",
        failures,
    )
    gate_complete = (
        gate.get("passed") is True
        and gate.get("candidate_commit") == frozen_commit
        and gate_transcript_valid
    )
    if candidate_fields_complete and gate_complete:
        transcript = _evidence_text(repo_root, gate.get("transcript_path"))
        for phrase in (
            f"candidate_commit={frozen_commit}",
            "candidate_tree_clean=true",
            "local_v1_candidate_gate_returncode=0",
        ):
            if phrase not in transcript:
                failures.append(f"candidate gate transcript is missing binding: {phrase}")
                gate_complete = False
    candidate_evidence_complete = candidate_fields_complete and gate_complete

    review_record_valid = _bound_evidence_valid(
        repo_root,
        review.get("record_path"),
        review.get("record_sha256"),
        "independent review",
        failures,
    )
    finding_counts = [
        review.get("critical_findings"),
        review.get("high_findings"),
        review.get("medium_findings"),
        review.get("low_findings"),
    ]
    independent_review_evidence_complete = (
        review.get("completed") is True
        and review.get("reviewed_candidate_commit") == frozen_commit
        and review.get("disposition") == "GO"
        and finding_counts == [0, 0, 0, 0]
        and review_record_valid
    )
    if independent_review_evidence_complete and str(frozen_commit) not in _evidence_text(
        repo_root, review.get("record_path")
    ):
        failures.append("independent review record does not name the frozen candidate")
        independent_review_evidence_complete = False

    uat_record_valid = _bound_evidence_valid(
        repo_root, uat.get("record_path"), uat.get("record_sha256"), "human UAT", failures
    )
    human_uat_evidence_complete = (
        uat.get("completed") is True
        and uat.get("tested_candidate_commit") == frozen_commit
        and uat.get("result") == "PASS"
        and uat_record_valid
    )
    if human_uat_evidence_complete and str(frozen_commit) not in _evidence_text(
        repo_root, uat.get("record_path")
    ):
        failures.append("human UAT record does not name the frozen candidate")
        human_uat_evidence_complete = False

    acceptance_record_valid = _bound_evidence_valid(
        repo_root,
        acceptance.get("record_path"),
        acceptance.get("record_sha256"),
        "human acceptance",
        failures,
    )
    human_acceptance_evidence_complete = (
        acceptance.get("accepted") is True
        and acceptance.get("accepted_candidate_commit") == frozen_commit
        and acceptance_record_valid
    )
    if human_acceptance_evidence_complete and str(frozen_commit) not in _evidence_text(
        repo_root, acceptance.get("record_path")
    ):
        failures.append("human acceptance record does not name the frozen candidate")
        human_acceptance_evidence_complete = False

    lineage_valid = _validate_disposition_lineage(
        repo_root, frozen_commit, lineage, failures
    )
    full_release_evidence_complete = (
        candidate_evidence_complete
        and independent_review_evidence_complete
        and human_uat_evidence_complete
        and human_acceptance_evidence_complete
        and lineage_valid
        and authority.get("candidate_qualified") is True
        and authority.get("release_allowed") is True
        and authority.get("promotion_allowed") is False
        and authority.get("production_allowed") is False
        and authority.get("uat_authority_inherited") is False
        and authority.get("new_governed_powers_allowed") is False
    )
    expected_record_status = _expected_record_status(
        candidate_evidence_complete=candidate_evidence_complete,
        independent_review_evidence_complete=independent_review_evidence_complete,
        human_uat_evidence_complete=human_uat_evidence_complete,
        human_acceptance_evidence_complete=human_acceptance_evidence_complete,
        lineage_valid=lineage_valid,
        candidate_qualified=authority.get("candidate_qualified") is True,
        release_allowed=authority.get("release_allowed") is True,
    )
    declared_record_status = payload.get("record_status")
    if expected_record_status is None:
        failures.append(
            "Local-v1 disposition evidence and authority do not match any valid "
            "record_status lifecycle stage"
        )
    elif declared_record_status != expected_record_status:
        failures.append(
            "Local-v1 disposition record_status mismatch: "
            f"declared={declared_record_status!r} expected={expected_record_status!r}"
        )
    release_evidence_complete = (
        full_release_evidence_complete and declared_record_status == "accepted"
    )
    if authority.get("candidate_qualified") is True and not candidate_evidence_complete:
        failures.append("candidate authority is true without complete candidate evidence")
    if authority.get("release_allowed") is True and not release_evidence_complete:
        failures.append("release authority is true without complete release evidence")
    for field in (
        "promotion_allowed",
        "production_allowed",
        "uat_authority_inherited",
        "new_governed_powers_allowed",
    ):
        if authority.get(field) is not False:
            failures.append(f"Local-v1 disposition must keep authority false: {field}")

    return failures, {
        "valid": not failures,
        "candidate_evidence_complete": candidate_evidence_complete,
        "independent_review_evidence_complete": independent_review_evidence_complete,
        "human_uat_evidence_complete": human_uat_evidence_complete,
        "human_acceptance_evidence_complete": human_acceptance_evidence_complete,
        "release_evidence_complete": release_evidence_complete,
    }


def _expected_record_status(
    *,
    candidate_evidence_complete: bool,
    independent_review_evidence_complete: bool,
    human_uat_evidence_complete: bool,
    human_acceptance_evidence_complete: bool,
    lineage_valid: bool,
    candidate_qualified: bool,
    release_allowed: bool,
) -> str | None:
    lifecycle_state = (
        candidate_evidence_complete,
        independent_review_evidence_complete,
        human_uat_evidence_complete,
        human_acceptance_evidence_complete,
        lineage_valid,
        candidate_qualified,
        release_allowed,
    )
    exact_stages = {
        (False, False, False, False, False, False, False): "uninitialized",
        (True, False, False, False, False, True, False): "candidate_recorded",
        (True, True, False, False, False, True, False): "reviewed",
        (True, True, True, False, False, True, False): "uat_complete",
    }
    if lifecycle_state in exact_stages:
        return exact_stages[lifecycle_state]
    if lifecycle_state == (True, True, True, True, True, True, True):
        return "accepted"
    return None


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Local v1.0 completion contract check",
        f"valid: {str(report['valid']).lower()}",
        f"active_delivery_target: {report['active_delivery_target']}",
        f"tool_count: {report['tool_count']}",
        f"outcomes_complete: {report['outcomes_complete']}/{report['outcomes_total']}",
        f"milestones_complete: {report['milestones_complete']}/{report['milestones_total']}",
        f"active_next_action: {report['active_next_action']}",
        f"candidate_check_requested: {str(report['candidate_check_requested']).lower()}",
        f"candidate_ready: {str(report['candidate_ready']).lower()}",
        f"release_check_requested: {str(report['release_check_requested']).lower()}",
        f"release_ready: {str(report['release_ready']).lower()}",
        f"disposition_valid: {str(report['disposition_valid']).lower()}",
        "candidate_evidence_complete: "
        f"{str(report['candidate_evidence_complete']).lower()}",
        "independent_review_evidence_complete: "
        f"{str(report['independent_review_evidence_complete']).lower()}",
        "release_disposition_complete: "
        f"{str(report['release_disposition_complete']).lower()}",
        f"human_uat_complete: {str(report['human_uat_complete']).lower()}",
        f"release_accepted: {str(report['release_accepted']).lower()}",
        "runtime_authority_granted: false",
        "new_governed_powers_authorized: false",
        "pis_wait_blocks_local_v1: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _target_body(makefile: str, target: str) -> str:
    match = re.search(
        rf"^{re.escape(target)}:[ \t]*(?:[^\n]*)\n((?:\t[^\n]*\n?)*)",
        makefile,
        re.MULTILINE,
    )
    return match.group(1) if match else ""


def _contains_phrase(text: str, phrase: str) -> bool:
    return " ".join(phrase.split()) in " ".join(text.split())


def _count_metadata(text: str, label: str) -> tuple[int, int] | None:
    value = _scalar_metadata(text, label)
    match = re.fullmatch(r"(\d+)/(\d+)", value)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _scalar_metadata(text: str, label: str) -> str:
    match = re.search(
        rf"^- {re.escape(label)}: `([^`]+)`$",
        text,
        re.MULTILINE,
    )
    return match.group(1) if match else ""


def _empty_disposition_state(valid: bool) -> dict[str, bool]:
    return {
        "valid": valid,
        "candidate_evidence_complete": False,
        "independent_review_evidence_complete": False,
        "human_uat_evidence_complete": False,
        "human_acceptance_evidence_complete": False,
        "release_evidence_complete": False,
    }


def _object(
    payload: dict[str, Any], key: str, failures: list[str]
) -> dict[str, Any]:
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    failures.append(f"Local-v1 disposition field is not an object: {key}")
    return {}


def _require_exact_keys(
    payload: dict[str, Any],
    expected: set[str],
    label: str,
    failures: list[str],
) -> None:
    actual = set(payload)
    if actual != expected:
        failures.append(
            f"Local-v1 {label} keys drifted: "
            f"missing={sorted(expected - actual)!r} extra={sorted(actual - expected)!r}"
        )


def _is_commit(value: Any) -> bool:
    return isinstance(value, str) and COMMIT_PATTERN.fullmatch(value) is not None


def _bound_evidence_valid(
    repo_root: Path,
    path_value: Any,
    digest_value: Any,
    label: str,
    failures: list[str],
) -> bool:
    if path_value is None and digest_value is None:
        return False
    if not isinstance(path_value, str) or not path_value:
        failures.append(f"{label} path is missing or invalid")
        return False
    if not isinstance(digest_value, str) or SHA256_PATTERN.fullmatch(digest_value) is None:
        failures.append(f"{label} sha256 is missing or invalid")
        return False
    path = (repo_root / path_value).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError:
        failures.append(f"{label} path escapes the repository")
        return False
    if not path.is_file():
        failures.append(f"{label} path does not exist: {path_value}")
        return False
    actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_digest != digest_value:
        failures.append(f"{label} sha256 does not match: {path_value}")
        return False
    return True


def _evidence_text(repo_root: Path, path_value: Any) -> str:
    if not isinstance(path_value, str) or not path_value:
        return ""
    path = (repo_root / path_value).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _validate_disposition_lineage(
    repo_root: Path,
    frozen_commit: Any,
    lineage: dict[str, Any],
    failures: list[str],
) -> bool:
    allowed = lineage.get("allowed_descendant_purposes")
    if allowed != list(ALLOWED_DESCENDANT_PURPOSES):
        failures.append("Local-v1 disposition allowed descendant purposes drifted")
        return False
    descendants = lineage.get("declared_candidate_descendants")
    if not isinstance(descendants, list):
        failures.append("Local-v1 declared candidate descendants must be a list")
        return False
    parent = lineage.get("disposition_parent_commit")
    if parent is None and not descendants:
        return False
    if not _is_commit(frozen_commit) or not _is_commit(parent):
        failures.append("Local-v1 disposition lineage commits are missing or invalid")
        return False

    declared_commits: list[str] = []
    declared_purposes: list[str] = []
    for index, row in enumerate(descendants):
        if not isinstance(row, dict) or set(row) != {"commit", "purpose"}:
            failures.append(f"Local-v1 disposition descendant {index} has invalid keys")
            continue
        commit = row.get("commit")
        purpose = row.get("purpose")
        if not _is_commit(commit):
            failures.append(f"Local-v1 disposition descendant {index} commit is invalid")
            continue
        if purpose not in ALLOWED_DESCENDANT_PURPOSES:
            failures.append(f"Local-v1 disposition descendant {index} purpose is invalid")
            continue
        declared_commits.append(str(commit))
        declared_purposes.append(str(purpose))
    if len(declared_commits) != len(descendants):
        return False
    if len(declared_commits) != len(set(declared_commits)):
        failures.append("Local-v1 disposition descendant commits must be unique")
        return False
    if set(declared_purposes) != set(ALLOWED_DESCENDANT_PURPOSES):
        failures.append("Local-v1 disposition lineage is missing a required evidence purpose")
        return False
    if not _git_success(repo_root, "cat-file", "-e", f"{frozen_commit}^{{commit}}"):
        failures.append("Local-v1 frozen candidate commit is not present")
        return False
    if not _git_success(repo_root, "cat-file", "-e", f"{parent}^{{commit}}"):
        failures.append("Local-v1 disposition parent commit is not present")
        return False
    if not _git_success(
        repo_root, "merge-base", "--is-ancestor", str(frozen_commit), str(parent)
    ):
        failures.append("Local-v1 disposition parent is not a candidate descendant")
        return False
    actual_commits = _git_output(
        repo_root,
        "rev-list",
        "--reverse",
        "--ancestry-path",
        f"{frozen_commit}..{parent}",
    ).splitlines()
    if actual_commits != declared_commits:
        failures.append(
            "Local-v1 declared disposition descendants do not exactly match candidate lineage"
        )
        return False
    for commit in declared_commits:
        changed_paths = _git_output(
            repo_root,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            commit,
        ).splitlines()
        if not changed_paths or any(
            not path.startswith("docs/codex/local-v1-") for path in changed_paths
        ):
            failures.append(
                "Local-v1 disposition descendant changes paths outside "
                "docs/codex/local-v1-*"
            )
            return False
    current_head = _git_output(repo_root, "rev-parse", "HEAD")
    current_parent = _git_output(repo_root, "rev-parse", "HEAD^")
    if current_parent != parent:
        failures.append(
            "Local-v1 final disposition commit is not directly based on the declared parent"
        )
        return False
    final_paths = _git_output(
        repo_root,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        current_head,
    ).splitlines()
    allowed_final_paths = {
        CONTRACT_REL.as_posix(),
        DISPOSITION_REL.as_posix(),
    }
    if not final_paths or any(path not in allowed_final_paths for path in final_paths):
        failures.append("Local-v1 final disposition commit changes undeclared product paths")
        return False
    if _git_output(repo_root, "status", "--porcelain=v1", "--untracked-files=normal"):
        failures.append("Local-v1 final disposition validation requires a clean current checkout")
        return False
    return True


def _git_success(repo_root: Path, *args: str) -> bool:
    return (
        subprocess.run(
            ["git", *args],
            cwd=repo_root,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def _git_output(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _read(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        failures.append(f"unable to read {path}: {exc}")
        return ""


def _read_json(path: Path, failures: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"unable to read JSON {path}: {exc}")
        return {}


if __name__ == "__main__":
    raise SystemExit(main())

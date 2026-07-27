from __future__ import annotations

import copy

from scripts import enterprise_e1_contract_check


def test_live_enterprise_e1_contract_is_valid_and_bounded() -> None:
    report = enterprise_e1_contract_check.build_report(enterprise_e1_contract_check.ROOT)
    failures: list[str] = []
    contract = enterprise_e1_contract_check.load_contract(
        enterprise_e1_contract_check.ROOT / enterprise_e1_contract_check.CONTRACT_REL,
        failures,
    )
    expected_outcomes = sum(
        outcome["status"] == "complete" for outcome in contract["outcomes"]
    )
    expected_milestones = sum(
        milestone["status"] == "complete" for milestone in contract["milestones"]
    )

    assert failures == []
    assert report["valid"] is True, report["failures"]
    assert report["track_id"] == "E1"
    assert report["source_commit_is_ancestor"] is True
    assert report["current_branch"] == "codex/enterprise-single-site-operations"
    assert report["tool_count"] == 24
    assert report["outcomes_complete"] == expected_outcomes
    assert report["outcomes_total"] == 6
    assert report["milestones_complete"] == expected_milestones
    assert report["milestones_total"] == 6
    assert report["next_action"] in {"E1-M6", "stop_for_human_uat"}
    assert report["candidate_gate_complete"] is (
        contract["qualification"]["candidate_gate_complete"]
    )
    assert report["independent_review_complete"] is (
        contract["qualification"]["independent_review_complete"]
    )
    assert report["human_uat_packet_ready"] is (
        contract["qualification"]["human_uat_packet_ready"]
    )
    assert report["human_uat_complete"] is False
    assert report["pis_collection_action_authority"] is False


def test_enterprise_e1_contract_rejects_outcome_count_or_order_drift() -> None:
    failures: list[str] = []
    contract = enterprise_e1_contract_check.load_contract(
        enterprise_e1_contract_check.ROOT / enterprise_e1_contract_check.CONTRACT_REL,
        failures,
    )
    assert failures == []
    extra = copy.deepcopy(contract["outcomes"][0])
    extra["id"] = "E1-O7"
    contract["outcomes"].append(extra)
    contract["milestone_order"] = list(reversed(contract["milestone_order"]))

    validation = enterprise_e1_contract_check.validate_contract(
        contract,
        enterprise_e1_contract_check.ROOT,
    )

    assert "E1 completion contract must contain exactly six outcomes" in validation
    assert "E1 milestone order is not exact" in validation


def test_enterprise_e1_contract_rejects_authority_or_pis_wait_expansion() -> None:
    failures: list[str] = []
    contract = enterprise_e1_contract_check.load_contract(
        enterprise_e1_contract_check.ROOT / enterprise_e1_contract_check.CONTRACT_REL,
        failures,
    )
    assert failures == []
    contract["authority"]["runtime_postgres_allowed"] = True
    contract["pis_wait"]["collection_action_authority"] = True

    validation = enterprise_e1_contract_check.validate_contract(
        contract,
        enterprise_e1_contract_check.ROOT,
    )

    assert "E1 completion contract grants forbidden authority" in validation
    assert "E1 contract does not preserve the exact PIS external-input wait" in validation


def test_enterprise_e1_contract_rejects_false_qualification_completion() -> None:
    failures: list[str] = []
    contract = enterprise_e1_contract_check.load_contract(
        enterprise_e1_contract_check.ROOT / enterprise_e1_contract_check.CONTRACT_REL,
        failures,
    )
    assert failures == []
    contract["outcomes"][-1]["status"] = "complete"
    contract["milestones"][-1]["status"] = "complete"
    contract["progress"]["outcomes_complete"] = 1
    contract["progress"]["milestones_complete"] = 1
    contract["next_action"] = "stop_for_human_uat"

    validation = enterprise_e1_contract_check.validate_contract(
        contract,
        enterprise_e1_contract_check.ROOT,
    )

    assert "E1-O6 cannot be complete without candidate, review, and UAT packet gates" in validation
    assert (
        "E1 count-based progress does not match outcome and milestone states"
        in validation
    )

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts import enterprise_e1_candidate_preflight


def _contract_report() -> dict[str, Any]:
    return {
        "failures": [],
        "outcome_statuses": {
            "E1-O1": "complete",
            "E1-O2": "complete",
            "E1-O3": "complete",
            "E1-O4": "complete",
            "E1-O5": "complete",
            "E1-O6": "in_progress",
        },
        "milestone_statuses": {
            "E1-M1": "complete",
            "E1-M2": "complete",
            "E1-M3": "complete",
            "E1-M4": "complete",
            "E1-M5": "complete",
            "E1-M6": "in_progress",
        },
        "next_action": "E1-M6",
        "candidate_gate_complete": False,
        "independent_review_complete": False,
        "human_uat_packet_ready": False,
        "human_uat_complete": False,
        "pis_collection_action_authority": False,
        "source_commit_is_ancestor": True,
        "tool_count": 24,
        "outcomes_complete": 5,
        "milestones_complete": 5,
    }


def _fake_git(expected: str):
    def run(_root: Path, *args: str) -> tuple[int, str]:
        if args == ("rev-parse", "HEAD"):
            return 0, expected
        if args == ("rev-parse", "HEAD^{tree}"):
            return 0, "2" * 40
        if args == ("branch", "--show-current"):
            return 0, "codex/enterprise-single-site-operations"
        if args == ("status", "--porcelain=v1", "--untracked-files=normal"):
            return 0, ""
        return 1, ""

    return run


def test_enterprise_e1_candidate_preflight_binds_current_freeze_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = "1" * 40
    monkeypatch.setattr(enterprise_e1_candidate_preflight, "_git", _fake_git(head))
    monkeypatch.setattr(
        enterprise_e1_candidate_preflight.enterprise_e1_contract_check,
        "build_report",
        lambda _root: _contract_report(),
    )
    report = enterprise_e1_candidate_preflight.build_report(
        Path("/candidate"),
        head,
    )

    assert report["valid"] is True, report["failures"]
    assert report["candidate_commit"] == head
    assert report["branch"] == "codex/enterprise-single-site-operations"
    assert report["source_commit_is_ancestor"] is True
    assert report["tool_count"] == 24
    assert report["outcomes_complete"] == 5
    assert report["milestones_complete"] == 5
    assert report["next_action"] == "E1-M6"
    assert report["candidate_gate_complete"] is False
    assert report["independent_review_complete"] is False
    assert report["human_uat_packet_ready"] is False
    assert report["human_uat_complete"] is False
    assert report["pis_collection_action_authority"] is False


def test_enterprise_e1_candidate_preflight_rejects_wrong_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        enterprise_e1_candidate_preflight,
        "_git",
        _fake_git("1" * 40),
    )
    monkeypatch.setattr(
        enterprise_e1_candidate_preflight.enterprise_e1_contract_check,
        "build_report",
        lambda _root: _contract_report(),
    )
    report = enterprise_e1_candidate_preflight.build_report(
        Path("/candidate"),
        "0" * 40,
    )

    assert report["valid"] is False
    assert (
        "checkout HEAD does not match the expected E1 candidate" in report["failures"]
    )

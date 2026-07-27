from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts import enterprise_e1_inherited_local_v1_check


def _contract_report() -> dict[str, Any]:
    return {
        "valid": True,
        "failures": [],
        "tool_count": 24,
        "candidate_evidence_complete": True,
        "independent_review_evidence_complete": True,
        "human_uat_complete": False,
        "release_accepted": False,
        "runtime_authority_granted": False,
        "new_governed_powers_authorized": False,
    }


def _makefile() -> str:
    commands = "\n".join(
        f"\t$(MAKE) {target}"
        for target in enterprise_e1_inherited_local_v1_check.expected_descendant_targets()
    )
    return (
        f"{enterprise_e1_inherited_local_v1_check.DESCENDANT_INVENTORY_TARGET}:\n"
        f"{commands}\n"
    )


def _fake_git(
    _root: Path,
    *args: str,
) -> tuple[int, str]:
    if args == ("rev-parse", "HEAD"):
        return 0, "c" * 40
    if args == (
        "rev-parse",
        f"{enterprise_e1_inherited_local_v1_check.FROZEN_CANDIDATE}^{{tree}}",
    ):
        return 0, enterprise_e1_inherited_local_v1_check.FROZEN_TREE
    if args[:2] == ("merge-base", "--is-ancestor"):
        return 0, ""
    if args[:2] == ("diff", "--name-only"):
        return 0, ""
    return 1, ""


def test_inherited_local_v1_check_accepts_immutable_qualified_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "Makefile").write_text(_makefile(), encoding="utf-8")
    monkeypatch.setattr(
        enterprise_e1_inherited_local_v1_check,
        "_git",
        _fake_git,
    )
    monkeypatch.setattr(
        enterprise_e1_inherited_local_v1_check.local_v1_contract_check,
        "build_report",
        lambda _root: _contract_report(),
    )

    report = enterprise_e1_inherited_local_v1_check.build_report(tmp_path)

    assert report["valid"] is True, report["failures"]
    assert report["tool_count"] == 24
    assert report["candidate_evidence_complete"] is True
    assert report["independent_review_evidence_complete"] is True
    assert report["human_uat_complete"] is False
    assert report["release_accepted"] is False
    assert report["changed_protected_records"] == ()
    assert report["historical_exact_only_target_reexecuted"] is False


def test_inherited_local_v1_check_rejects_changed_record_and_inventory_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "Makefile").write_text(
        f"{enterprise_e1_inherited_local_v1_check.DESCENDANT_INVENTORY_TARGET}:\n"
        "\t$(MAKE) local-v1-o2-evidence-check\n",
        encoding="utf-8",
    )

    def drifted_git(root: Path, *args: str) -> tuple[int, str]:
        if args[:2] == ("diff", "--name-only"):
            return 0, enterprise_e1_inherited_local_v1_check.PROTECTED_LOCAL_V1_RECORDS[
                0
            ]
        return _fake_git(root, *args)

    monkeypatch.setattr(
        enterprise_e1_inherited_local_v1_check,
        "_git",
        drifted_git,
    )
    monkeypatch.setattr(
        enterprise_e1_inherited_local_v1_check.local_v1_contract_check,
        "build_report",
        lambda _root: _contract_report(),
    )

    report = enterprise_e1_inherited_local_v1_check.build_report(tmp_path)

    assert report["valid"] is False
    assert "protected Local v1 qualification records changed" in report["failures"]
    assert "Enterprise E1 Local v1 descendant inventory drifted" in report["failures"]

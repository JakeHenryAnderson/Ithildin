from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts import product_line_acceptance_checkpoint


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_live_product_line_acceptance_checkpoint_is_exact_and_bounded() -> None:
    report = product_line_acceptance_checkpoint.build_report(
        product_line_acceptance_checkpoint.ROOT
    )
    record = _load(
        product_line_acceptance_checkpoint.ROOT
        / product_line_acceptance_checkpoint.RECORD_REL
    )

    assert record == product_line_acceptance_checkpoint.EXPECTED_RECORD
    assert report["valid"] is True, report["failures"]
    assert report["record_status"] == "accepted_for_scoped_development_continuation"
    assert report["personal_candidate"] == product_line_acceptance_checkpoint.LOCAL_CANDIDATE
    assert report["personal_tree"] == product_line_acceptance_checkpoint.LOCAL_TREE
    assert report["enterprise_e1_candidate"] == product_line_acceptance_checkpoint.E1_CANDIDATE
    assert report["enterprise_e1_tree"] == product_line_acceptance_checkpoint.E1_TREE
    assert report["enterprise_e1_descends_from_local"] is True
    assert report["governed_tool_count"] == 24
    assert report["human_uat_executed"] is False


def test_checkpoint_rejects_extra_keys_or_authority_drift() -> None:
    record = copy.deepcopy(product_line_acceptance_checkpoint.EXPECTED_RECORD)
    record["unexpected"] = True
    assert product_line_acceptance_checkpoint.validate_record(record) == [
        "product-line acceptance checkpoint keys or values are not exact"
    ]

    record = copy.deepcopy(product_line_acceptance_checkpoint.EXPECTED_RECORD)
    record["authority_nonclaims"]["release_authority"] = True
    assert product_line_acceptance_checkpoint.validate_record(record) == [
        "product-line acceptance checkpoint keys or values are not exact"
    ]

    record = copy.deepcopy(product_line_acceptance_checkpoint.EXPECTED_RECORD)
    record["product_lines"]["enterprise_e1"]["candidate_tree"] = "0" * 40
    assert product_line_acceptance_checkpoint.validate_record(record) == [
        "product-line acceptance checkpoint keys or values are not exact"
    ]


def test_checkpoint_rejects_human_uat_waiver_expansion() -> None:
    record = copy.deepcopy(product_line_acceptance_checkpoint.EXPECTED_RECORD)
    record["product_lines"]["personal"]["human_uat"]["passed"] = True

    assert product_line_acceptance_checkpoint.validate_record(record) == [
        "product-line acceptance checkpoint keys or values are not exact"
    ]


def test_checkpoint_git_bindings_match_both_trees_and_ancestry() -> None:
    report = product_line_acceptance_checkpoint.validate_git_bindings(
        product_line_acceptance_checkpoint.ROOT
    )

    assert report["local_tree"] == product_line_acceptance_checkpoint.LOCAL_TREE
    assert report["e1_tree"] == product_line_acceptance_checkpoint.E1_TREE
    assert report["e1_descends_from_local"] is True
    assert report["failures"] == []


def test_checkpoint_rejects_source_contract_release_or_pis_drift() -> None:
    root = product_line_acceptance_checkpoint.ROOT
    local_disposition = _load(
        root / product_line_acceptance_checkpoint.LOCAL_DISPOSITION_REL
    )
    e1_contract = _load(root / product_line_acceptance_checkpoint.E1_CONTRACT_REL)
    local_disposition["human_acceptance"]["accepted"] = True
    e1_contract["pis_wait"]["collection_action_authority"] = True

    failures = product_line_acceptance_checkpoint.validate_source_contracts(
        local_disposition,
        e1_contract,
    )

    assert "Local-v1 release acceptance must remain false" in failures
    assert "E1 PIS external-input wait is not exact" in failures

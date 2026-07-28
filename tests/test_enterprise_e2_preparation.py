from __future__ import annotations

import copy
from typing import Any

from scripts import enterprise_e2_preparation_check


def _live_contract() -> dict[str, Any]:
    failures: list[str] = []
    contract = enterprise_e2_preparation_check.load_contract(
        enterprise_e2_preparation_check.ROOT
        / enterprise_e2_preparation_check.CONTRACT_REL,
        failures,
    )
    assert failures == []
    return contract


def test_live_enterprise_e2_preparation_is_valid_and_non_authorizing() -> None:
    report = enterprise_e2_preparation_check.build_report(
        enterprise_e2_preparation_check.ROOT
    )

    assert report["valid"] is True, report["failures"]
    assert report["track_id"] == "E2-PREP"
    assert report["tool_count"] == 24
    assert report["work_package_ids"] == list(
        enterprise_e2_preparation_check.WORK_PACKAGE_IDS
    )
    assert report["runtime_behavior_changes_allowed"] is False
    assert report["production_identity_allowed"] is False
    assert report["runtime_postgres_allowed"] is False
    assert report["e1_human_uat_complete"] is False
    assert report["pis_next_action"] == enterprise_e2_preparation_check.PIS_WAIT_ACTION
    assert report["next_action"] == enterprise_e2_preparation_check.NEXT_ACTION


def test_e2_contract_rejects_runtime_authority_or_pis_route_drift() -> None:
    contract = copy.deepcopy(_live_contract())
    authority = contract["authority"]
    standing = contract["standing_authority"]
    assert isinstance(authority, dict)
    assert isinstance(standing, dict)
    authority["production_identity_allowed"] = True
    standing["pis_next_action"] = "connect_to_postgres"

    failures = enterprise_e2_preparation_check.validate_contract(contract)

    assert "E2 preparation grants forbidden implementation authority" in failures
    assert "E2 preparation does not preserve current PIS authority" in failures


def test_e2_contract_rejects_scale_overclaim_or_work_package_reordering() -> None:
    contract = copy.deepcopy(_live_contract())
    scale = contract["scale_fixture"]
    identity = contract["identity_reconciliation"]
    assert isinstance(scale, dict)
    assert isinstance(identity, dict)
    scale["supported_scale_claim_allowed"] = True
    packages = identity["work_packages"]
    assert isinstance(packages, list)
    packages.reverse()

    failures = enterprise_e2_preparation_check.validate_contract(contract)

    assert "E2 scale fixture contract is not exact and bounded" in failures
    assert "E2 identity work packages are not exact and ordered" in failures

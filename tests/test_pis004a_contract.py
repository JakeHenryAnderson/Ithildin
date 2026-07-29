from __future__ import annotations

import copy
from typing import Any

from scripts import production_identity_storage_pis_004a_check as pis004a_check


def _live_contract() -> dict[str, Any]:
    failures: list[str] = []
    contract = pis004a_check.load_contract(
        pis004a_check.ROOT / pis004a_check.CONTRACT_REL,
        failures,
    )
    assert failures == []
    return contract


def test_live_pis004a_entry_contract_is_valid_and_bounded() -> None:
    report = pis004a_check.build_report(pis004a_check.ROOT)

    assert report["valid"] is True, report["failures"]
    assert report["decision_id"] == "PIS-004A"
    assert report["status"] == "candidate_implemented_review_required"
    assert report["tool_count"] == 24
    assert report["pis003_next_action"] == pis004a_check.PIS_WAIT_ACTION
    assert report["e1_human_uat_complete"] is False
    assert report["live_idp_allowed"] is False
    assert report["runtime_postgres_allowed"] is False


def test_contract_rejects_production_authority_and_pis_route_drift() -> None:
    contract = copy.deepcopy(_live_contract())
    authority = contract["authority"]
    standing = contract["standing_authority"]
    assert isinstance(authority, dict)
    assert isinstance(standing, dict)
    authority["production_identity_allowed"] = True
    authority["external_network_allowed"] = True
    standing["pis003_next_action"] = "connect_to_postgres"

    failures = pis004a_check.validate_contract(contract)

    assert "PIS-004A authority ceiling is invalid" in failures
    assert "PIS-004A standing authority competes with or bypasses PIS" in failures


def test_contract_rejects_work_package_or_allowed_path_expansion() -> None:
    contract = copy.deepcopy(_live_contract())
    packages = contract["work_packages"]
    allowed_paths = contract["allowed_paths"]
    assert isinstance(packages, list)
    assert isinstance(allowed_paths, list)
    packages[-1]["status"] = "authorized_in_pis_004a"
    allowed_paths.append("apps/mcp-server/src/ithildin_mcp_server/server.py")

    failures = pis004a_check.validate_contract(contract)

    assert "PIS-004A work-package scope is invalid" in failures
    assert "PIS-004A allowed paths are not exact and ordered" in failures


def test_contract_rejects_dependency_network_or_fallback_authority() -> None:
    contract = copy.deepcopy(_live_contract())
    dependency = contract["dependency_gate"]
    assert isinstance(dependency, dict)
    dependency["live_discovery_or_jwk_fetch_allowed"] = True
    dependency["hand_rolled_oidc_fallback_allowed"] = True

    failures = pis004a_check.validate_contract(contract)

    assert (
        "PIS-004A dependency gate permits forbidden behavior: "
        "live_discovery_or_jwk_fetch_allowed"
    ) in failures
    assert (
        "PIS-004A dependency gate permits forbidden behavior: "
        "hand_rolled_oidc_fallback_allowed"
    ) in failures


def test_contract_rejects_token_persistence_or_session_audit_authentication() -> None:
    contract = copy.deepcopy(_live_contract())
    persistence = contract["persistence"]
    safety = contract["safety_contract"]
    assert isinstance(persistence, dict)
    assert isinstance(safety, dict)
    persistence["raw_id_token_persisted"] = True
    safety["session_audit_id_authenticates"] = True

    failures = pis004a_check.validate_contract(contract)

    assert "PIS-004A persistence permits forbidden material: raw_id_token_persisted" in failures
    assert "PIS-004A safety contract permits forbidden authority" in failures

from __future__ import annotations

import copy
from typing import Any

import pytest

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
    assert report["status"] == "candidate_independent_review_complete_e2_id_005_blocked"
    assert report["tool_count"] == 24
    assert report["reviewed_candidate_commit"] == pis004a_check.REVIEWED_CANDIDATE_COMMIT
    assert report["independent_review_complete"] is True
    assert report["open_review_findings"] == 0
    assert report["pis003_next_action"] == pis004a_check.PIS_WAIT_ACTION
    assert report["e1_human_uat_complete"] is False
    assert report["live_idp_allowed"] is False
    assert report["runtime_postgres_allowed"] is False


@pytest.mark.parametrize(
    (
        "current_branch",
        "head_name",
        "head_oid",
        "authorized_candidate_oid",
        "porcelain",
    ),
    [
        (pis004a_check.BRANCH, pis004a_check.BRANCH, "a" * 40, "a" * 40, ""),
        ("", "HEAD", "a" * 40, "a" * 40, ""),
    ],
)
def test_original_pis004a_candidate_checkout_accepts_only_clean_exact_remote_candidate(
    current_branch: str,
    head_name: str,
    head_oid: str,
    authorized_candidate_oid: str,
    porcelain: str | None,
) -> None:
    assert (
        pis004a_check._candidate_checkout_failures(  # noqa: SLF001
            current_branch=current_branch,
            head_name=head_name,
            head_oid=head_oid,
            authorized_candidate_oid=authorized_candidate_oid,
            porcelain=porcelain,
        )
        == []
    )


@pytest.mark.parametrize(
    (
        "current_branch",
        "head_name",
        "local_oid",
        "local_tree",
    ),
    [
        (
            pis004a_check.PIS005A_SUCCESSOR_BRANCH,
            pis004a_check.PIS005A_SUCCESSOR_BRANCH,
            "c" * 40,
            "d" * 40,
        ),
        ("", "HEAD", "c" * 40, "d" * 40),
    ],
)
def test_pis005a_successor_accepts_named_implementation_and_detached_exact_candidate(
    current_branch: str,
    head_name: str,
    local_oid: str,
    local_tree: str,
) -> None:
    assert (
        pis004a_check._pis005a_successor_checkout_failures(  # noqa: SLF001
            current_branch=current_branch,
            head_name=head_name,
            head_oid="c" * 40,
            head_tree="d" * 40,
            local_successor_oid=local_oid,
            local_successor_tree=local_tree,
            remote_successor_oid="c" * 40,
            remote_successor_tree="d" * 40,
            porcelain="",
            shallow_state="false",
            contract_bindings_valid=True,
            successor_base_tree=pis004a_check.PIS005A_SUCCESSOR_BASE_TREE,
            repair_base_tree=pis004a_check.PIS005A_REPAIR_BASE_TREE,
            repair_base_remote_oid=pis004a_check.PIS005A_REPAIR_BASE_COMMIT,
            repair_base_is_ancestor=True,
            pis004a_remote_oid=pis004a_check.PIS004A_REVIEW_COMMIT,
        )
        == []
    )


def test_pis005a_successor_rejects_unrelated_detached_commit() -> None:
    failures = pis004a_check._pis005a_successor_checkout_failures(  # noqa: SLF001
        current_branch="",
        head_name="HEAD",
        head_oid="d" * 40,
        head_tree="e" * 40,
        local_successor_oid="",
        local_successor_tree="",
        remote_successor_oid="c" * 40,
        remote_successor_tree="e" * 40,
        porcelain="",
        shallow_state="false",
        contract_bindings_valid=True,
        successor_base_tree=pis004a_check.PIS005A_SUCCESSOR_BASE_TREE,
        repair_base_tree=pis004a_check.PIS005A_REPAIR_BASE_TREE,
        repair_base_remote_oid=pis004a_check.PIS005A_REPAIR_BASE_COMMIT,
        repair_base_is_ancestor=True,
        pis004a_remote_oid=pis004a_check.PIS004A_REVIEW_COMMIT,
    )

    assert (
        "PIS-004A detached PIS-005A successor does not match the fetched commit and tree"
        in failures
    )


@pytest.mark.parametrize(
    "rejected_predecessor",
    [
        "fce0a3668db5150cf0aa75de1fd914b296a2e099",
        "1542bd0469e18a0ae52cc48920f30b4e41518513",
        "afd13f98440d4cd9c032b6a996db133bdf78055d",
        pis004a_check.PIS005A_REPAIR_BASE_COMMIT,
    ],
)
def test_pis005a_successor_rejects_rejected_predecessor_and_contract_drift(
    rejected_predecessor: str,
) -> None:
    failures = pis004a_check._pis005a_successor_checkout_failures(  # noqa: SLF001
        current_branch="",
        head_name="HEAD",
        head_oid=rejected_predecessor,
        head_tree="e" * 40,
        local_successor_oid="",
        local_successor_tree="",
        remote_successor_oid="c" * 40,
        remote_successor_tree="e" * 40,
        porcelain="",
        shallow_state="false",
        contract_bindings_valid=False,
        successor_base_tree=pis004a_check.PIS005A_SUCCESSOR_BASE_TREE,
        repair_base_tree=pis004a_check.PIS005A_REPAIR_BASE_TREE,
        repair_base_remote_oid=pis004a_check.PIS005A_REPAIR_BASE_COMMIT,
        repair_base_is_ancestor=False,
        pis004a_remote_oid=pis004a_check.PIS004A_REVIEW_COMMIT,
    )

    assert "PIS-004A exact PIS-005A successor identity is invalid" in failures
    assert (
        "PIS-004A detached PIS-005A successor does not match the fetched commit and tree"
        in failures
    )


def test_pis005a_named_successor_rejects_missing_remote_dirty_original_reproduction() -> None:
    failures = pis004a_check._pis005a_successor_checkout_failures(  # noqa: SLF001
        current_branch=pis004a_check.PIS005A_SUCCESSOR_BRANCH,
        head_name=pis004a_check.PIS005A_SUCCESSOR_BRANCH,
        head_oid="c" * 40,
        head_tree="d" * 40,
        local_successor_oid="c" * 40,
        local_successor_tree="d" * 40,
        remote_successor_oid="",
        remote_successor_tree="",
        porcelain=" M apps/api/src/ithildin_api/database_migration_backup.py",
        shallow_state="false",
        contract_bindings_valid=True,
        successor_base_tree=pis004a_check.PIS005A_SUCCESSOR_BASE_TREE,
        repair_base_tree=pis004a_check.PIS005A_REPAIR_BASE_TREE,
        repair_base_remote_oid=pis004a_check.PIS005A_REPAIR_BASE_COMMIT,
        repair_base_is_ancestor=True,
        pis004a_remote_oid=pis004a_check.PIS004A_REVIEW_COMMIT,
    )

    assert (
        "PIS-004A named PIS-005A successor does not match local, fetched, and tree identity"
        in failures
    )
    assert "PIS-004A named PIS-005A successor is not clean" in failures


@pytest.mark.parametrize(
    ("head_tree", "remote_tree", "shallow_state", "expected_failure"),
    [
        (
            "d" * 40,
            "e" * 40,
            "false",
            "PIS-004A detached PIS-005A successor does not match the fetched commit and tree",
        ),
        (
            "d" * 40,
            "d" * 40,
            "true",
            "PIS-004A PIS-005A successor checkout is shallow or unverifiable",
        ),
    ],
)
def test_pis005a_detached_successor_rejects_wrong_tree_and_shallow_repository(
    head_tree: str,
    remote_tree: str,
    shallow_state: str,
    expected_failure: str,
) -> None:
    failures = pis004a_check._pis005a_successor_checkout_failures(  # noqa: SLF001
        current_branch="",
        head_name="HEAD",
        head_oid="c" * 40,
        head_tree=head_tree,
        local_successor_oid="",
        local_successor_tree="",
        remote_successor_oid="c" * 40,
        remote_successor_tree=remote_tree,
        porcelain="",
        shallow_state=shallow_state,
        contract_bindings_valid=True,
        successor_base_tree=pis004a_check.PIS005A_SUCCESSOR_BASE_TREE,
        repair_base_tree=pis004a_check.PIS005A_REPAIR_BASE_TREE,
        repair_base_remote_oid=pis004a_check.PIS005A_REPAIR_BASE_COMMIT,
        repair_base_is_ancestor=True,
        pis004a_remote_oid=pis004a_check.PIS004A_REVIEW_COMMIT,
    )

    assert expected_failure in failures


@pytest.mark.parametrize(
    (
        "current_branch",
        "local_oid",
        "local_tree",
        "head_parents",
        "head_parent_tree",
        "predecessor_topology_valid",
    ),
    [
        (
            pis004a_check.PIS005A_SUCCESSOR_BRANCH,
            "c" * 40,
            "d" * 40,
            ("a" * 40,),
            pis004a_check.PIS005A_REPAIR_BASE_TREE,
            True,
        ),
        (
            "",
            "",
            "",
            (pis004a_check.PIS005A_REPAIR_BASE_COMMIT,),
            pis004a_check.PIS005A_REPAIR_BASE_TREE,
            True,
        ),
        (
            "",
            "c" * 40,
            "d" * 40,
            (
                pis004a_check.PIS005A_REPAIR_BASE_COMMIT,
                "a" * 40,
            ),
            pis004a_check.PIS005A_REPAIR_BASE_TREE,
            True,
        ),
        (
            "",
            "c" * 40,
            "d" * 40,
            (pis004a_check.PIS005A_REPAIR_BASE_COMMIT,),
            "a" * 40,
            True,
        ),
        (
            "",
            "c" * 40,
            "d" * 40,
            (pis004a_check.PIS005A_REPAIR_BASE_COMMIT,),
            pis004a_check.PIS005A_REPAIR_BASE_TREE,
            False,
        ),
    ],
)
def test_pis005a_successor_pure_topology_negatives_fail_closed(
    current_branch: str,
    local_oid: str,
    local_tree: str,
    head_parents: tuple[str, ...],
    head_parent_tree: str,
    predecessor_topology_valid: bool,
) -> None:
    failures = pis004a_check._pis005a_successor_checkout_failures(  # noqa: SLF001
        current_branch=current_branch,
        head_name=(
            pis004a_check.PIS005A_SUCCESSOR_BRANCH if current_branch else "HEAD"
        ),
        head_oid="c" * 40,
        head_tree="d" * 40,
        local_successor_oid=local_oid,
        local_successor_tree=local_tree,
        remote_successor_oid="c" * 40,
        remote_successor_tree="d" * 40,
        porcelain="",
        shallow_state="false",
        contract_bindings_valid=True,
        successor_base_tree=pis004a_check.PIS005A_SUCCESSOR_BASE_TREE,
        repair_base_tree=pis004a_check.PIS005A_REPAIR_BASE_TREE,
        repair_base_remote_oid=pis004a_check.PIS005A_REPAIR_BASE_COMMIT,
        repair_base_is_ancestor=True,
        pis004a_remote_oid=pis004a_check.PIS004A_REVIEW_COMMIT,
        head_parents=head_parents,
        head_parent_tree=head_parent_tree,
        predecessor_topology_valid=predecessor_topology_valid,
    )

    if local_oid == "":
        assert (
            "PIS-004A detached PIS-005A successor does not match the fetched commit and tree"
            in failures
        )
    else:
        assert "PIS-004A exact PIS-005A successor identity is invalid" in failures


@pytest.mark.parametrize(
    (
        "current_branch",
        "head_name",
        "head_oid",
        "authorized_candidate_oid",
        "porcelain",
        "expected_failure",
    ),
    [
        (
            "main",
            "main",
            "a" * 40,
            "a" * 40,
            "",
            "PIS-004A is not on its exact isolated branch or detached for review",
        ),
        (
            "",
            "HEAD",
            "a" * 40,
            "b" * 40,
            "",
            "PIS-004A checkout does not match the fetched authorized branch tip",
        ),
        (
            "",
            "HEAD",
            "a" * 40,
            "",
            "",
            "PIS-004A checkout does not match the fetched authorized branch tip",
        ),
        (
            "",
            "HEAD",
            "a" * 40,
            "a" * 40,
            "?? untracked",
            "PIS-004A candidate worktree is not clean",
        ),
        (
            "",
            "HEAD",
            "a" * 40,
            "a" * 40,
            None,
            "PIS-004A checkout cleanliness could not be verified",
        ),
        (
            pis004a_check.BRANCH,
            pis004a_check.BRANCH,
            "a" * 40,
            "b" * 40,
            "",
            "PIS-004A checkout does not match the fetched authorized branch tip",
        ),
        (
            pis004a_check.BRANCH,
            pis004a_check.BRANCH,
            "a" * 40,
            "a" * 40,
            " M allowed.py",
            "PIS-004A candidate worktree is not clean",
        ),
    ],
)
def test_candidate_checkout_rejects_every_other_checkout(
    current_branch: str,
    head_name: str,
    head_oid: str,
    authorized_candidate_oid: str,
    porcelain: str | None,
    expected_failure: str,
) -> None:
    assert expected_failure in pis004a_check._candidate_checkout_failures(  # noqa: SLF001
        current_branch=current_branch,
        head_name=head_name,
        head_oid=head_oid,
        authorized_candidate_oid=authorized_candidate_oid,
        porcelain=porcelain,
    )


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


def test_contract_rejects_independent_review_identity_or_authority_drift() -> None:
    contract = copy.deepcopy(_live_contract())
    review = contract["independent_review"]
    assert isinstance(review, dict)
    review["reviewed_candidate_commit"] = "0" * 40
    review["high_findings"] = 1
    review["e2_id_005_entry_authorized"] = True

    failures = pis004a_check.validate_contract(contract)

    assert "PIS-004A independent-review disposition is invalid" in failures


def test_contract_rejects_dependency_network_or_fallback_authority() -> None:
    contract = copy.deepcopy(_live_contract())
    dependency = contract["dependency_gate"]
    assert isinstance(dependency, dict)
    dependency["live_discovery_or_jwk_fetch_allowed"] = True
    dependency["hand_rolled_oidc_fallback_allowed"] = True

    failures = pis004a_check.validate_contract(contract)

    assert (
        "PIS-004A dependency gate permits forbidden behavior: live_discovery_or_jwk_fetch_allowed"
    ) in failures
    assert (
        "PIS-004A dependency gate permits forbidden behavior: hand_rolled_oidc_fallback_allowed"
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


def test_contract_rejects_weakened_recent_authentication_ceiling() -> None:
    contract = copy.deepcopy(_live_contract())
    safety = contract["safety_contract"]
    assert isinstance(safety, dict)
    safety["recent_authentication_maximum_age_seconds"] = 601

    failures = pis004a_check.validate_contract(contract)

    assert "PIS-004A safety contract recent-auth ceiling is invalid" in failures


@pytest.mark.parametrize(
    "control",
    [
        "authentication_grant_provider_generation_revalidation_required",
        "approval_classification_server_owned",
        "self_approval_denied_for_all_classes",
    ],
)
def test_contract_rejects_weakened_enterprise_authority_controls(control: str) -> None:
    contract = copy.deepcopy(_live_contract())
    safety = contract["safety_contract"]
    assert isinstance(safety, dict)
    safety[control] = False

    failures = pis004a_check.validate_contract(contract)

    assert "PIS-004A safety contract weakens a required control" in failures


def test_contract_rejects_approval_effect_authority() -> None:
    contract = copy.deepcopy(_live_contract())
    safety = contract["safety_contract"]
    assert isinstance(safety, dict)
    safety["approval_request_effect_authority"] = True

    failures = pis004a_check.validate_contract(contract)

    assert "PIS-004A safety contract permits forbidden authority" in failures

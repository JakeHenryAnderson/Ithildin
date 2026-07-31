from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest

from scripts import enterprise_e2_preparation_check as e2_check
from scripts import production_identity_storage_pis_004a_check as pis004a_check
from scripts import production_identity_storage_pis_005a_check as pis005a_check


def _contract() -> dict[str, object]:
    return pis005a_check.load_contract(
        pis005a_check.ROOT / pis005a_check.CONTRACT_REL,
    )


def _failure_strings(report: Mapping[str, object]) -> list[str]:
    failures = report.get("failures")
    assert isinstance(failures, list)
    assert all(isinstance(failure, str) for failure in failures)
    return cast(list[str], failures)


def test_live_pis005a_entry_contract_is_valid_and_bounded() -> None:
    report = pis005a_check.build_report(pis005a_check.ROOT)

    assert report["valid"] is True, report["failures"]
    assert report["decision_id"] == "PIS-005A"
    assert report["tool_count"] == 24
    assert report["security_prerequisite_commit"] == pis005a_check.SECURITY_PREREQUISITE_COMMIT


def test_contract_rejects_release_claim_in_title() -> None:
    contract = copy.deepcopy(_contract())
    contract["title"] = "PIS-005A production identity released and promoted"

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A contract identity is invalid" in failures


def test_contract_rejects_status_inconsistent_next_action() -> None:
    contract = copy.deepcopy(_contract())
    contract["next_action"] = "release_and_promote"

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A next action is invalid" in failures


def test_contract_rejects_live_transport_and_effect_authority() -> None:
    contract = copy.deepcopy(_contract())
    authority = contract["authority"]
    safety = contract["safety_contract"]
    assert isinstance(authority, dict)
    assert isinstance(safety, dict)
    authority["live_mtls_allowed"] = True
    authority["new_api_route_allowed"] = True
    safety["request_effect_authority"] = True

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A authority ceiling permits forbidden behavior" in failures
    assert "PIS-005A safety contract permits forbidden authority" in failures


def test_contract_rejects_key_aliases_or_legacy_id_redefinition() -> None:
    contract = copy.deepcopy(_contract())
    crypto = contract["cryptographic_contract"]
    assert isinstance(crypto, dict)
    crypto["noncanonical_base64_allowed"] = True
    crypto["legacy_application_key_ids_changed"] = True
    crypto["application_key_fingerprint_scheme"] = "legacy_text_hash"

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A cryptographic identity or compatibility contract is invalid" in failures


def test_contract_rejects_secret_persistence_or_automatic_down_migration() -> None:
    contract = copy.deepcopy(_contract())
    persistence = contract["persistence"]
    assert isinstance(persistence, dict)
    persistence["raw_enrollment_secret_persisted"] = True
    persistence["certificate_private_key_persisted"] = True
    persistence["automatic_down_migration_allowed"] = True

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A persistence or rollback boundary is invalid" in failures


def test_contract_rejects_weakened_migration_guard_or_atomicity_overclaim() -> None:
    contract = copy.deepcopy(_contract())
    persistence = contract["persistence"]
    assert isinstance(persistence, dict)
    persistence["migration_backup_guard_owns_commit"] = False
    persistence["pre_migration_backup_device_inode_receipt_binding_required"] = False
    persistence["migration_commit_marker_keys"] = ["migration_backup_receipt_pre_v7_v1"]
    persistence["atomic_filesystem_and_sqlite_commit_claimed"] = True
    persistence[
        "continuous_protection_against_indefinitely_active_same_uid_directory_writer_claimed"
    ] = True

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A persistence or rollback boundary is invalid" in failures


def test_contract_keeps_live_remote_ticket_blocked() -> None:
    contract = copy.deepcopy(_contract())
    work_packages = contract["work_packages"]
    assert isinstance(work_packages, list)
    final_package = work_packages[-1]
    assert isinstance(final_package, dict)
    final_package["status"] = "authorized"

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A work-package scope is invalid" in failures


def test_contract_requires_negative_concurrency_migration_and_redaction_inventory() -> None:
    contract = copy.deepcopy(_contract())
    validation = contract["validation"]
    assert isinstance(validation, dict)
    validation["negative_inventory"] = ["noncanonical_application_public_key"]

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A negative-test inventory is incomplete" in failures


def test_contract_rejects_extra_keys_at_each_nested_authority_boundary() -> None:
    contract = copy.deepcopy(_contract())
    contract["unexpected"] = True
    crypto = contract["cryptographic_contract"]
    safety = contract["safety_contract"]
    assert isinstance(crypto, dict)
    assert isinstance(safety, dict)
    profile = crypto["certificate_profile"]
    assert isinstance(profile, dict)
    crypto["fallback_algorithm"] = "rsa"
    profile["dns_san_allowed"] = True
    safety["restore_revoked_node"] = True

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A top-level contract keys are not closed" in failures
    assert "PIS-005A cryptographic-contract keys are not closed" in failures
    assert "PIS-005A fixture certificate profile is invalid" in failures
    assert "PIS-005A safety-contract keys are not closed" in failures


def test_contract_rejects_dependency_schema_and_resource_bound_drift() -> None:
    contract = copy.deepcopy(_contract())
    dependency = contract["dependency_gate"]
    persistence = contract["persistence"]
    safety = contract["safety_contract"]
    assert isinstance(dependency, dict)
    assert isinstance(persistence, dict)
    assert isinstance(safety, dict)
    dependency["ca_or_kms_sdk_allowed"] = True
    persistence["schema_fingerprint"] = "sha256:" + ("0" * 64)
    safety["request_maximum_clock_skew_seconds"] = 3_600
    safety["request_body_maximum_bytes"] = 1_073_741_824

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A dependency gate is invalid" in failures
    assert "PIS-005A persistence or rollback boundary is invalid" in failures
    assert "PIS-005A local fixture resource bounds are invalid" in failures


def test_contract_rejects_dangerous_rollback_and_old_writer_claims() -> None:
    contract = copy.deepcopy(_contract())
    rollback = contract["rollback"]
    assert isinstance(rollback, dict)
    rollback.update(
        {
            "feature": "activate_runtime_feature_before_reverting_code",
            "database": "automatic_down_migration_allowed_then_restore_if_convenient",
            "data_loss": "destructive_table_removal_allowed",
            "compatibility": "schema_7_is_safe_for_schema_6_writers",
        }
    )

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A rollback and compatibility contract is invalid" in failures


def test_contract_rejects_duplicate_json_keys() -> None:
    duplicate = '{"schema_version":"1","schema_version":"2"}'
    with pytest.raises(ValueError, match="duplicate JSON key: schema_version"):
        json.loads(
            duplicate,
            object_pairs_hook=pis005a_check._reject_duplicate_keys,  # noqa: SLF001
        )


def test_contract_pins_each_standing_authority_path_and_digest_pair() -> None:
    redirected = copy.deepcopy(_contract())
    standing = redirected["standing_authority"]
    assert isinstance(standing, dict)
    standing["architecture_path"] = "README.md"
    standing["architecture_sha256"] = hashlib.sha256(
        (pis005a_check.ROOT / "README.md").read_bytes()
    ).hexdigest()

    substituted_digest = copy.deepcopy(_contract())
    substituted = substituted_digest["standing_authority"]
    assert isinstance(substituted, dict)
    substituted["pis004a_review_sha256"] = substituted["pis004a_contract_sha256"]

    for contract in (redirected, substituted_digest):
        assert (
            "PIS-005A standing authority is not the exact protected inventory"
            in pis005a_check.validate_contract(contract)
        )


def test_contract_pins_disjoint_safe_evidence_allow_and_forbid_inventories() -> None:
    contract = copy.deepcopy(_contract())
    safety = contract["safety_contract"]
    assert isinstance(safety, dict)
    allowed = safety["safe_evidence_allowed_fields"]
    forbidden = safety["safe_evidence_forbidden_fields"]
    assert isinstance(allowed, list)
    assert isinstance(forbidden, list)
    allowed.append("request_body")
    forbidden.remove("digest_key")

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A safe-evidence vocabulary is invalid" in failures


@pytest.mark.parametrize(
    "import_statement",
    [
        "import ithildin_api.enterprise_node_identity\n",
        "from .enterprise_node_identity import NodeWorkloadIdentityStore\n",
        "from . import enterprise_node_identity\n",
        "from ithildin_api import enterprise_node_identity\n",
        "importlib.import_module('ithildin_api.enterprise_node_identity')\n",
        "__import__('ithildin_api.enterprise_node_identity')\n",
    ],
)
def test_runtime_import_fence_rejects_ordinary_and_dynamic_import_forms(
    tmp_path: Path,
    import_statement: str,
) -> None:
    source_root = tmp_path / "apps/api/src/ithildin_api"
    source_root.mkdir(parents=True)
    (source_root / "consumer.py").write_text(import_statement, encoding="utf-8")

    failures = pis005a_check._runtime_import_failures(tmp_path)  # noqa: SLF001

    assert failures == [
        "PIS-005A introduced a runtime import in apps/api/src/ithildin_api/consumer.py"
    ]


def test_runtime_import_fence_allows_unrelated_relative_import(tmp_path: Path) -> None:
    source_root = tmp_path / "apps/api/src/ithildin_api"
    source_root.mkdir(parents=True)
    (source_root / "consumer.py").write_text(
        "from . import trusted_host_promotion_v2_migration\n",
        encoding="utf-8",
    )

    assert pis005a_check._runtime_import_failures(tmp_path) == []  # noqa: SLF001


def test_completed_review_record_rejects_pending_or_positive_authority_claims() -> None:
    reviewed_commit = "a" * 40
    reviewed_tree = "b" * 40
    review: dict[str, object] = {
        "reviewed_candidate_commit": reviewed_commit,
        "reviewed_candidate_tree": reviewed_tree,
    }
    valid_record = "\n".join(
        (
            "Status: independent implementation review complete; no open findings.",
            f"Reviewed exact implementation commit: `{reviewed_commit}`.",
            f"Reviewed exact tree: `{reviewed_tree}`.",
            "Review method: independent read-only Codex review in a clean detached worktree.",
            "Candidate freeze complete: `true`.",
            "Clean detached worktree verified: `true`.",
            "Remote identity verified: `true`.",
            "Focused gate passed: `true`.",
            "Implementation review complete: `true`.",
            "Human UAT complete: `false`.",
            "Live remote transport authorized: `false`.",
            "Release or promotion authorized: `false`.",
            "Critical findings: `0`.",
            "High findings: `0`.",
            "Medium findings: `0`.",
            "Low findings: `0`.",
            "Open findings: `0`.",
            "E2-NODE-005 status: blocked; separate entry decision required.",
            "Current governed tool count: exactly `24`.",
            "The exact implementation candidate was independently reviewed "
            "in a clean detached worktree.",
        )
    )

    assert (
        pis005a_check._review_record_failures(  # noqa: SLF001
            valid_record,
            status="candidate_independent_review_complete",
            review=review,
        )
        == []
    )

    duplicate_contradictory_record = "\n".join(
        (
            valid_record,
            "Status: independent implementation review pending; no review disposition recorded.",
            f"Reviewed exact implementation commit: `{'c' * 40}`.",
            "Clean detached worktree verified: `false`.",
            "Remote identity verified: `false`.",
            "Focused gate passed: `false`.",
            "Implementation review complete: `false`.",
            "Human UAT complete: `true`.",
            "Live remote transport authorized: `true`.",
            "Release or promotion authorized: `true`.",
            "Medium findings: `1`.",
            "The implementation candidate has not yet been frozen or reviewed.",
            "The exact implementation candidate is frozen and awaits independent review.",
        )
    )
    failures = pis005a_check._review_record_failures(  # noqa: SLF001
        duplicate_contradictory_record,
        status="candidate_independent_review_complete",
        review=review,
    )

    assert len(failures) == 12
    assert sum("is not exact and singular" in failure for failure in failures) == 10
    assert sum("contains stale lifecycle narrative" in failure for failure in failures) == 2


@pytest.mark.parametrize(
    ("status", "field", "value"),
    [
        (
            "candidate_independent_review_pending",
            "record_path",
            "docs/codex/not-a-review-record.md",
        ),
        (
            "candidate_independent_review_pending",
            "review_method",
            "self_attested",
        ),
        (
            "candidate_independent_review_complete",
            "record_path",
            "docs/codex/not-a-review-record.md",
        ),
        (
            "candidate_independent_review_complete",
            "review_method",
            "self_attested",
        ),
    ],
)
def test_contract_rejects_pending_or_complete_review_metadata_drift(
    status: str,
    field: str,
    value: str,
) -> None:
    contract = copy.deepcopy(_contract())
    contract["status"] = status
    review = contract["independent_review"]
    assert isinstance(review, dict)
    if status == "candidate_independent_review_complete":
        review.update(
            {
                "reviewed_candidate_commit": "a" * 40,
                "reviewed_candidate_tree": "b" * 40,
                "clean_detached_worktree_verified": True,
                "remote_identity_verified": True,
                "focused_gate_passed": True,
                "critical_findings": 0,
                "high_findings": 0,
                "medium_findings": 0,
                "low_findings": 0,
                "open_findings": 0,
                "implementation_review_complete": True,
            }
        )
    review[field] = value

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A independent-review metadata is invalid" in failures


def test_contract_rejects_non_hex_or_nonzero_completed_review_disposition() -> None:
    contract = copy.deepcopy(_contract())
    contract["status"] = "candidate_independent_review_complete"
    review = contract["independent_review"]
    assert isinstance(review, dict)
    review.update(
        {
            "reviewed_candidate_commit": "g" * 40,
            "reviewed_candidate_tree": "b" * 40,
            "clean_detached_worktree_verified": True,
            "remote_identity_verified": True,
            "focused_gate_passed": True,
            "critical_findings": 0,
            "high_findings": 0,
            "medium_findings": 1,
            "low_findings": 0,
            "open_findings": 1,
            "implementation_review_complete": True,
        }
    )

    failures = pis005a_check.validate_contract(contract)

    assert "PIS-005A completed independent-review disposition is invalid" in failures


def test_completed_review_checkout_accepts_ancestor_candidate_and_only_review_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    topology = _initialize_exact_candidate_repository(repository, monkeypatch)
    candidate = topology["candidate"]
    candidate_tree = topology["candidate_tree"]

    for relative in pis005a_check._EXPECTED_POST_REVIEW_PATHS:  # noqa: SLF001
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("review record projection\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-q", "-m", "record independent review")
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{pis005a_check.BRANCH}",
        "HEAD",
    )
    review: dict[str, object] = {
        "reviewed_candidate_commit": candidate,
        "reviewed_candidate_tree": candidate_tree,
    }

    assert (
        pis005a_check._candidate_checkout_failures(  # noqa: SLF001
            repository,
            status="candidate_independent_review_complete",
            review=review,
        )
        == []
    )

    registration_script = repository / "scripts/build_docs_site.py"
    registration_script.parent.mkdir(parents=True, exist_ok=True)
    registration_script.write_text(
        "arbitrary_unreviewed_code = True\n",
        encoding="utf-8",
    )
    _git(repository, "add", registration_script.relative_to(repository).as_posix())
    _git(repository, "commit", "-q", "-m", "forbidden post-review executable change")
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{pis005a_check.BRANCH}",
        "HEAD",
    )

    failures = pis005a_check._candidate_checkout_failures(  # noqa: SLF001
        repository,
        status="candidate_independent_review_complete",
        review=review,
    )

    assert any(
        failure.startswith("PIS-005A post-review record changed implementation paths:")
        for failure in failures
    )


def test_completed_review_checkout_does_not_relabel_structurally_valid_sibling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    topology = _initialize_exact_candidate_repository(repository, monkeypatch)
    reviewed_candidate = topology["candidate"]
    reviewed_tree = topology["candidate_tree"]
    _git(repository, "checkout", "-q", "--detach", topology["repair_base"])
    _git(
        repository,
        "checkout",
        "-q",
        "-B",
        pis005a_check.BRANCH,
        topology["repair_base"],
    )
    history = repository / "history.txt"
    history.write_text(
        history.read_text(encoding="utf-8") + "sibling candidate\n",
        encoding="utf-8",
    )
    _git(repository, "add", history.name)
    _git(repository, "commit", "-q", "-m", "separate structurally valid sibling")
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{pis005a_check.BRANCH}",
        "HEAD",
    )

    failures = pis005a_check._candidate_checkout_failures(  # noqa: SLF001
        repository,
        status="candidate_independent_review_complete",
        review={
            "reviewed_candidate_commit": reviewed_candidate,
            "reviewed_candidate_tree": reviewed_tree,
        },
    )

    assert (
        "PIS-005A reviewed candidate is unavailable or not an ancestor of HEAD"
        in failures
    )


def test_candidate_checkout_rejects_missing_remote_and_dirty_original_reproduction(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "PIS-005A fixture")
    _git(repository, "config", "user.email", "pis005a@example.invalid")
    _git(repository, "checkout", "-q", "-b", pis005a_check.BRANCH)
    implementation = repository / "implementation.py"
    implementation.write_text("candidate = True\n", encoding="utf-8")
    _git(repository, "add", implementation.name)
    _git(repository, "commit", "-q", "-m", "candidate")
    implementation.write_text("candidate = 'dirty'\n", encoding="utf-8")

    failures = pis005a_check._candidate_checkout_failures(  # noqa: SLF001
        repository,
        status="candidate_independent_review_pending",
        review=None,
    )

    assert "PIS-005A fetched candidate identity is unavailable" in failures
    assert "PIS-005A candidate worktree is not clean" in failures


@pytest.mark.parametrize("detached", [False, True])
def test_candidate_checkout_accepts_clean_exact_named_and_detached_topologies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    detached: bool,
) -> None:
    repository = tmp_path / "repository"
    _initialize_exact_candidate_repository(repository, monkeypatch)
    if detached:
        _git(repository, "checkout", "-q", "--detach", "HEAD")

    assert (
        pis005a_check._candidate_checkout_failures(  # noqa: SLF001
            repository,
            status="candidate_independent_review_pending",
            review=None,
        )
        == []
    )


def test_candidate_checkout_rejects_wrong_remote_commit_and_tree(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "PIS-005A fixture")
    _git(repository, "config", "user.email", "pis005a@example.invalid")
    _git(repository, "checkout", "-q", "-b", pis005a_check.BRANCH)
    implementation = repository / "implementation.py"
    implementation.write_text("candidate = 'remote'\n", encoding="utf-8")
    _git(repository, "add", implementation.name)
    _git(repository, "commit", "-q", "-m", "remote candidate")
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{pis005a_check.BRANCH}",
        "HEAD",
    )
    implementation.write_text("candidate = 'head'\n", encoding="utf-8")
    _git(repository, "add", implementation.name)
    _git(repository, "commit", "-q", "-m", "wrong head")

    failures = pis005a_check._candidate_checkout_failures(  # noqa: SLF001
        repository,
        status="candidate_independent_review_pending",
        review=None,
    )

    assert (
        "PIS-005A checkout does not match the fetched authorized commit and tree"
        in failures
    )


def test_candidate_checkout_rejects_shallow_repository(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "PIS-005A fixture")
    _git(repository, "config", "user.email", "pis005a@example.invalid")
    _git(repository, "checkout", "-q", "-b", pis005a_check.BRANCH)
    (repository / "implementation.py").write_text("candidate = True\n", encoding="utf-8")
    _git(repository, "add", "implementation.py")
    _git(repository, "commit", "-q", "-m", "candidate")
    head = _git(repository, "rev-parse", "HEAD")
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{pis005a_check.BRANCH}",
        head,
    )
    git_directory = repository / _git(repository, "rev-parse", "--git-dir")
    (git_directory / "shallow").write_text(f"{head}\n", encoding="utf-8")

    failures = pis005a_check._candidate_checkout_failures(  # noqa: SLF001
        repository,
        status="candidate_independent_review_pending",
        review=None,
    )

    assert "PIS-005A candidate repository is shallow or unverifiable" in failures


def test_candidate_checkout_rejects_exact_rejected_topology(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "PIS-005A fixture")
    _git(repository, "config", "user.email", "pis005a@example.invalid")
    _git(repository, "checkout", "-q", "-b", pis005a_check.BRANCH)
    (repository / "implementation.py").write_text("candidate = True\n", encoding="utf-8")
    _git(repository, "add", "implementation.py")
    _git(repository, "commit", "-q", "-m", "candidate")
    head = _git(repository, "rev-parse", "HEAD")
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{pis005a_check.BRANCH}",
        head,
    )
    monkeypatch.setattr(pis005a_check, "REJECTED_CANDIDATE_COMMITS", {head})

    failures = pis005a_check._candidate_checkout_failures(  # noqa: SLF001
        repository,
        status="candidate_independent_review_pending",
        review=None,
    )

    assert "PIS-005A candidate is not the exact direct child of repair-8" in failures


def test_candidate_identity_pure_arbitrary_agreeing_descendant_fails_closed() -> None:
    agreeing_commit = "c" * 40
    agreeing_tree = "d" * 40

    failures = pis005a_check._candidate_identity_failures(  # noqa: SLF001
        branch=pis005a_check.BRANCH,
        head_name=pis005a_check.BRANCH,
        head=agreeing_commit,
        head_tree=agreeing_tree,
        local=agreeing_commit,
        local_tree=agreeing_tree,
        remote=agreeing_commit,
        remote_tree=agreeing_tree,
        candidate_commit=agreeing_commit,
        candidate_parents=("a" * 40,),
        candidate_parent_tree=pis005a_check.REPAIR_BASE_TREE,
        predecessor_topology_valid=True,
        shallow_state="false",
        porcelain="",
    )

    assert "PIS-005A candidate is not the exact direct child of repair-8" in failures


@pytest.mark.parametrize(
    ("mutation", "expected_failure"),
    [
        (
            "extra_commit",
            "PIS-005A candidate is not the exact direct child of repair-8",
        ),
        (
            "same_tree_extra_commit",
            "PIS-005A candidate is not the exact direct child of repair-8",
        ),
        (
            "merge_parent",
            "PIS-005A candidate is not the exact direct child of repair-8",
        ),
        (
            "missing_detached_local_ref",
            "PIS-005A exact local candidate identity is unavailable",
        ),
        (
            "wrong_parent_tree",
            "PIS-005A candidate is not the exact direct child of repair-8",
        ),
        (
            "repair_base_ref_drift",
            "PIS-005A accepted or rejected predecessor identity changed",
        ),
        (
            "missing_remote_ref",
            "PIS-005A fetched candidate identity is unavailable",
        ),
        (
            "untracked_file",
            "PIS-005A candidate worktree is not clean",
        ),
    ],
)
def test_candidate_checkout_real_repository_topology_reproductions_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    expected_failure: str,
) -> None:
    repository = tmp_path / "repository"
    topology = _initialize_exact_candidate_repository(repository, monkeypatch)
    if mutation == "extra_commit":
        history = repository / "history.txt"
        history.write_text(history.read_text(encoding="utf-8") + "extra\n", encoding="utf-8")
        _git(repository, "add", history.name)
        _git(repository, "commit", "-q", "-m", "unreviewed extra descendant")
        _git(
            repository,
            "update-ref",
            f"refs/remotes/origin/{pis005a_check.BRANCH}",
            "HEAD",
        )
    elif mutation == "same_tree_extra_commit":
        _git(repository, "commit", "--allow-empty", "-q", "-m", "same-tree extra descendant")
        _git(
            repository,
            "update-ref",
            f"refs/remotes/origin/{pis005a_check.BRANCH}",
            "HEAD",
        )
    elif mutation == "merge_parent":
        _git(repository, "checkout", "-q", "-b", "fixture-side", topology["repair_base"])
        (repository / "side.txt").write_text("side\n", encoding="utf-8")
        _git(repository, "add", "side.txt")
        _git(repository, "commit", "-q", "-m", "side parent")
        _git(repository, "checkout", "-q", pis005a_check.BRANCH)
        _git(repository, "merge", "-q", "--no-ff", "fixture-side", "-m", "nonlinear merge")
        _git(
            repository,
            "update-ref",
            f"refs/remotes/origin/{pis005a_check.BRANCH}",
            "HEAD",
        )
    elif mutation == "missing_detached_local_ref":
        _git(repository, "checkout", "-q", "--detach", "HEAD")
        _git(repository, "update-ref", "-d", f"refs/heads/{pis005a_check.BRANCH}")
    elif mutation == "wrong_parent_tree":
        monkeypatch.setattr(pis005a_check, "REPAIR_BASE_TREE", "0" * 40)
    elif mutation == "repair_base_ref_drift":
        _git(
            repository,
            "update-ref",
            f"refs/heads/{pis005a_check.REPAIR_BASE_BRANCH}",
            topology["candidate"],
        )
    elif mutation == "missing_remote_ref":
        _git(
            repository,
            "update-ref",
            "-d",
            f"refs/remotes/origin/{pis005a_check.BRANCH}",
        )
    elif mutation == "untracked_file":
        (repository / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    else:  # pragma: no cover - closed parameter inventory
        raise AssertionError(f"unknown fixture mutation: {mutation}")

    failures = pis005a_check._candidate_checkout_failures(  # noqa: SLF001
        repository,
        status="candidate_independent_review_pending",
        review=None,
    )

    assert expected_failure in failures


@pytest.mark.parametrize("checkout_mode", ["named", "detached", "linked"])
def test_full_report_builders_accept_clean_exact_repair9(
    tmp_path: Path,
    checkout_mode: str,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    checkout = repository
    if checkout_mode == "detached":
        _git(repository, "checkout", "-q", "--detach", "HEAD")
    elif checkout_mode == "linked":
        checkout = tmp_path / "linked-pis005a-review"
        _git(repository, "worktree", "add", "-q", "--detach", str(checkout), "HEAD")

    for report in (
        pis005a_check.build_report(checkout),
        pis004a_check.build_report(checkout),
    ):
        assert report["valid"] is True, report["failures"]


def test_full_report_builders_accept_exact_three_file_completed_review_disposition(
    tmp_path: Path,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    _record_completed_review(repository)

    for report in (
        pis005a_check.build_report(repository),
        pis004a_check.build_report(repository),
    ):
        assert report["valid"] is True, report["failures"]
    e2_report = e2_check.build_report(repository)
    assert e2_report["status"] == "preparation_complete_implementation_not_authorized"
    assert e2_report["production_identity_allowed"] is False

    _git(repository, "checkout", "-q", "--detach", "HEAD")

    for report in (
        pis005a_check.build_report(repository),
        pis004a_check.build_report(repository),
    ):
        assert report["valid"] is True, report["failures"]
    detached_e2_report = e2_check.build_report(repository)
    assert detached_e2_report["status"] == (
        "preparation_complete_implementation_not_authorized"
    )
    assert detached_e2_report["production_identity_allowed"] is False


@pytest.mark.parametrize(
    "relative",
    [
        "README.md",
        "Makefile",
        "scripts/production_identity_storage_pis_004a_check.py",
        "tests/test_pis004a_contract.py",
        "apps/api/src/ithildin_api/enterprise_node_identity.py",
    ],
)
def test_full_report_builders_reject_completed_review_with_any_fourth_file(
    tmp_path: Path,
    relative: str,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    _write_completed_review_files(repository)
    extra = repository / relative
    extra.write_text(
        extra.read_text(encoding="utf-8") + "\n# forbidden disposition edit\n",
        encoding="utf-8",
    )
    _commit_disposition(repository)

    pis005a_failures = _failure_strings(pis005a_check.build_report(repository))
    pis004a_failures = _failure_strings(pis004a_check.build_report(repository))

    assert any(
        failure.startswith("PIS-005A post-review record changed implementation paths:")
        and relative in failure
        for failure in pis005a_failures
    )
    assert (
        f"PIS-004A PIS-005A review disposition changed forbidden paths: {relative}"
        in pis004a_failures
    )


@pytest.mark.parametrize("mutation", ["deletion", "rename"])
def test_full_report_builders_reject_completed_review_deletion_or_rename(
    tmp_path: Path,
    mutation: str,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    _write_completed_review_files(repository)
    review_relative = pis005a_check.REVIEW_RECORD_REL.as_posix()
    if mutation == "deletion":
        (repository / review_relative).unlink()
    else:
        _git(
            repository,
            "mv",
            review_relative,
            "docs/codex/pis005a-review-renamed.md",
        )
    _commit_disposition(repository)

    pis005a_report = pis005a_check.build_report(repository)
    pis004a_report = pis004a_check.build_report(repository)

    assert pis005a_report["valid"] is False
    assert pis004a_report["valid"] is False
    if mutation == "rename":
        assert (
            "PIS-004A PIS-005A review disposition changed forbidden paths: "
            "docs/codex/pis005a-review-renamed.md"
            in _failure_strings(pis004a_report)
        )


@pytest.mark.parametrize(
    "mutation",
    ["empty_second_descendant", "same_tree_descendant", "merge", "branch_movement"],
)
@pytest.mark.parametrize("checkout_mode", ["named", "detached"])
def test_completed_review_full_report_rejects_nonexact_disposition_topology(
    tmp_path: Path,
    mutation: str,
    checkout_mode: str,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    topology = _record_completed_review(repository)
    if mutation in {"empty_second_descendant", "same_tree_descendant"}:
        message = (
            "empty second disposition"
            if mutation == "empty_second_descendant"
            else "same-tree disposition descendant"
        )
        _git(repository, "commit", "--allow-empty", "-q", "-m", message)
        _git(
            repository,
            "update-ref",
            f"refs/remotes/origin/{pis005a_check.BRANCH}",
            "HEAD",
        )
    elif mutation == "merge":
        _git(
            repository,
            "checkout",
            "-q",
            "-b",
            "disposition-side",
            topology["candidate"],
        )
        side = repository / "docs/codex/disposition-side.md"
        side.write_text("side\n", encoding="utf-8")
        _git(repository, "add", side.relative_to(repository).as_posix())
        _git(repository, "commit", "-q", "-m", "side disposition")
        _git(repository, "checkout", "-q", pis005a_check.BRANCH)
        _git(
            repository,
            "merge",
            "-q",
            "--no-ff",
            "disposition-side",
            "-m",
            "merge disposition",
        )
        _git(
            repository,
            "update-ref",
            f"refs/remotes/origin/{pis005a_check.BRANCH}",
            "HEAD",
        )
    else:
        _git(
            repository,
            "update-ref",
            f"refs/remotes/origin/{pis005a_check.BRANCH}",
            topology["candidate"],
        )
    if checkout_mode == "detached":
        _git(repository, "checkout", "-q", "--detach", "HEAD")

    pis005a_failures = _failure_strings(pis005a_check.build_report(repository))
    pis004a_failures = _failure_strings(pis004a_check.build_report(repository))

    if mutation == "branch_movement":
        assert (
            "PIS-004A completed PIS-005A disposition does not match local, fetched, "
            "HEAD, and tree identity"
            in pis004a_failures
        )
    else:
        assert (
            "PIS-005A completed review must have exactly one disposition commit "
            "whose sole raw parent is the reviewed candidate"
            in pis005a_failures
        )
        assert (
            "PIS-004A completed PIS-005A review topology is invalid"
            in pis004a_failures
        )


@pytest.mark.parametrize("identity_mutation", ["reviewed_commit", "reviewed_tree"])
@pytest.mark.parametrize("checkout_mode", ["named", "detached"])
def test_completed_review_full_report_rejects_wrong_reviewed_identity(
    tmp_path: Path,
    identity_mutation: str,
    checkout_mode: str,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    _write_completed_review_files(repository)
    contract_path = repository / pis005a_check.CONTRACT_REL
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    review = contract["independent_review"]
    assert isinstance(review, dict)
    review[
        "reviewed_candidate_commit"
        if identity_mutation == "reviewed_commit"
        else "reviewed_candidate_tree"
    ] = "0" * 40
    contract_path.write_text(
        json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _commit_disposition(repository)
    if checkout_mode == "detached":
        _git(repository, "checkout", "-q", "--detach", "HEAD")

    pis005a_report = pis005a_check.build_report(repository)
    pis004a_report = pis004a_check.build_report(repository)

    assert pis005a_report["valid"] is False
    assert pis004a_report["valid"] is False
    if identity_mutation == "reviewed_commit":
        assert (
            "PIS-005A reviewed candidate is unavailable or not an ancestor of HEAD"
            in _failure_strings(pis005a_report)
        )
    else:
        assert (
            "PIS-005A reviewed candidate tree identity changed"
            in _failure_strings(pis005a_report)
        )
    assert (
        "PIS-004A completed PIS-005A review topology is invalid"
        in _failure_strings(pis004a_report)
    )


@pytest.mark.parametrize("checkout_mode", ["named", "detached"])
def test_completed_review_full_report_rejects_structurally_valid_sibling(
    tmp_path: Path,
    checkout_mode: str,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    topology = _record_completed_review(repository)
    disposition_tree = _git(repository, "rev-parse", "HEAD^{tree}")
    sibling_candidate = _git(
        repository,
        "commit-tree",
        topology["candidate_tree"],
        "-p",
        pis005a_check.REPAIR_BASE_COMMIT,
        stdin="structurally valid sibling candidate\n",
    )
    sibling_disposition = _git(
        repository,
        "commit-tree",
        disposition_tree,
        "-p",
        sibling_candidate,
        stdin="sibling review disposition\n",
    )
    _git(
        repository,
        "update-ref",
        f"refs/heads/{pis005a_check.BRANCH}",
        sibling_disposition,
        topology["disposition"],
    )
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{pis005a_check.BRANCH}",
        sibling_disposition,
        topology["disposition"],
    )
    if checkout_mode == "detached":
        _git(repository, "checkout", "-q", "--detach", "HEAD")

    pis005a_failures = _failure_strings(pis005a_check.build_report(repository))
    pis004a_failures = _failure_strings(pis004a_check.build_report(repository))

    assert (
        "PIS-005A reviewed candidate is unavailable or not an ancestor of HEAD"
        in pis005a_failures
    )
    assert (
        "PIS-004A completed PIS-005A review topology is invalid"
        in pis004a_failures
    )


@pytest.mark.parametrize(
    "redirect_kind",
    [
        "core_worktree",
        "include",
        "include_if",
        "worktree_config",
        "config_symlink",
        "alternate_objects",
    ],
)
def test_full_report_builders_reject_repository_local_git_redirection(
    tmp_path: Path,
    redirect_kind: str,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    alternate = tmp_path / f"pristine-{redirect_kind}"
    shutil.copytree(
        repository,
        alternate,
        ignore=shutil.ignore_patterns(".git"),
    )
    contamination = repository / "forbidden-untracked-review-file.txt"
    contamination.write_text("must be observed in the supplied root\n", encoding="utf-8")
    included = tmp_path / f"{redirect_kind}.config"
    included.write_text(
        f"[core]\n\tworktree = {alternate}\n",
        encoding="utf-8",
    )
    if redirect_kind == "core_worktree":
        _git(repository, "config", "--local", "core.worktree", str(alternate))
    elif redirect_kind == "include":
        _git(repository, "config", "--local", "include.path", str(included))
    elif redirect_kind == "include_if":
        git_directory = _git(
            repository,
            "rev-parse",
            "--path-format=absolute",
            "--git-dir",
        )
        _git(
            repository,
            "config",
            "--local",
            f"includeIf.gitdir:{git_directory}/.path",
            str(included),
        )
    elif redirect_kind == "worktree_config":
        _git(repository, "config", "--local", "extensions.worktreeConfig", "true")
        _git(repository, "config", "--worktree", "core.worktree", str(alternate))
    elif redirect_kind == "config_symlink":
        common_directory = Path(
            _git(
                repository,
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
            )
        )
        config_path = common_directory / "config"
        redirected_config = tmp_path / "redirected-local-config"
        shutil.copy2(config_path, redirected_config)
        config_path.unlink()
        config_path.symlink_to(redirected_config)
    else:
        alternate_objects_repository = tmp_path / "alternate-objects-repository"
        alternate_objects_repository.mkdir()
        _git(alternate_objects_repository, "init", "-q")
        common_directory = Path(
            _git(
                repository,
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
            )
        )
        alternates_path = common_directory / "objects/info/alternates"
        alternates_path.parent.mkdir(parents=True, exist_ok=True)
        alternates_path.write_text(
            str(alternate_objects_repository / ".git/objects") + "\n",
            encoding="utf-8",
        )

    reports = (
        pis005a_check.build_report(repository),
        pis004a_check.build_report(repository),
        e2_check.build_report(repository),
    )

    assert contamination.is_file()
    assert reports[0]["valid"] is False
    assert (
        "PIS-005A repository-local Git redirection or worktree binding is unsafe"
        in _failure_strings(reports[0])
    )
    assert reports[1]["valid"] is False
    assert (
        "PIS-004A repository-local Git redirection or worktree binding is unsafe"
        in _failure_strings(reports[1])
    )
    assert reports[2]["valid"] is False
    assert (
        "E2 preparation repository-local Git redirection or worktree binding is unsafe"
        in _failure_strings(reports[2])
    )


def test_pending_contract_rejects_disposition_topology_in_full_report(
    tmp_path: Path,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    review_path = repository / pis005a_check.REVIEW_RECORD_REL
    review_path.write_text(
        review_path.read_text(encoding="utf-8") + "\npending topology drift\n",
        encoding="utf-8",
    )
    _git(repository, "add", review_path.relative_to(repository).as_posix())
    _git(repository, "commit", "-q", "-m", "unreviewed disposition descendant")
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{pis005a_check.BRANCH}",
        "HEAD",
    )

    pis005a_failures = _failure_strings(pis005a_check.build_report(repository))
    pis004a_failures = _failure_strings(pis004a_check.build_report(repository))

    assert (
        "PIS-005A candidate is not the exact direct child of repair-8"
        in pis005a_failures
    )
    assert "PIS-004A exact PIS-005A successor identity is invalid" in pis004a_failures


def test_full_report_builders_reject_confirmed_same_tree_replace_laundering(
    tmp_path: Path,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    candidate = _git(repository, "rev-parse", "HEAD")
    _git(repository, "commit", "--allow-empty", "-q", "-m", "same-tree extra descendant")
    extra = _git(repository, "rev-parse", "HEAD")
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{pis005a_check.BRANCH}",
        extra,
    )
    _git(repository, "replace", extra, candidate)

    assert _git(repository, "show", "-s", "--format=%P", extra) == pis005a_check.REPAIR_BASE_COMMIT
    assert (
        _git_no_replace(repository, "show", "-s", "--format=%P", extra)
        == candidate
    )

    pis005a_report = pis005a_check.build_report(repository)
    pis004a_report = pis004a_check.build_report(repository)
    pis005a_failures = _failure_strings(pis005a_report)
    pis004a_failures = _failure_strings(pis004a_report)

    assert pis005a_report["valid"] is False
    assert "PIS-005A replacement-ref topology metadata is present" in pis005a_failures
    assert (
        "PIS-005A candidate is not the exact direct child of repair-8"
        in pis005a_failures
    )
    assert pis004a_report["valid"] is False
    assert "PIS-004A replacement-ref topology metadata is present" in pis004a_failures
    assert "PIS-004A exact PIS-005A successor identity is invalid" in pis004a_failures


def test_full_report_builders_reject_raw_same_tree_extra_descendant(
    tmp_path: Path,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    _git(repository, "commit", "--allow-empty", "-q", "-m", "raw same-tree extra descendant")
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{pis005a_check.BRANCH}",
        "HEAD",
    )

    pis005a_report = pis005a_check.build_report(repository)
    pis004a_report = pis004a_check.build_report(repository)
    pis005a_failures = _failure_strings(pis005a_report)
    pis004a_failures = _failure_strings(pis004a_report)

    assert (
        "PIS-005A candidate is not the exact direct child of repair-8"
        in pis005a_failures
    )
    assert "PIS-005A replacement-ref topology metadata is present" not in pis005a_failures
    assert "PIS-004A exact PIS-005A successor identity is invalid" in pis004a_failures
    assert "PIS-004A replacement-ref topology metadata is present" not in pis004a_failures


def test_full_report_builders_reject_unrelated_replacement_ref(tmp_path: Path) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    first_blob_path = tmp_path / "unrelated-first.txt"
    second_blob_path = tmp_path / "unrelated-second.txt"
    first_blob_path.write_text("first\n", encoding="utf-8")
    second_blob_path.write_text("second\n", encoding="utf-8")
    first_blob = _git(repository, "hash-object", "-w", str(first_blob_path))
    second_blob = _git(repository, "hash-object", "-w", str(second_blob_path))
    _git(repository, "replace", first_blob, second_blob)

    pis005a_report = pis005a_check.build_report(repository)
    pis004a_report = pis004a_check.build_report(repository)
    pis005a_failures = _failure_strings(pis005a_report)
    pis004a_failures = _failure_strings(pis004a_report)

    assert "PIS-005A replacement-ref topology metadata is present" in pis005a_failures
    assert (
        "PIS-005A candidate is not the exact direct child of repair-8"
        not in pis005a_failures
    )
    assert "PIS-004A replacement-ref topology metadata is present" in pis004a_failures
    assert "PIS-004A exact PIS-005A successor identity is invalid" not in pis004a_failures


def test_full_report_builders_reject_redirected_replacement_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    candidate = _git(repository, "rev-parse", "HEAD")
    _git(repository, "commit", "--allow-empty", "-q", "-m", "redirected same-tree descendant")
    extra = _git(repository, "rev-parse", "HEAD")
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{pis005a_check.BRANCH}",
        extra,
    )
    replacement_base = "refs/hidden-replacements"
    _git(repository, "update-ref", f"{replacement_base}/{extra}", candidate)
    monkeypatch.setenv("GIT_REPLACE_REF_BASE", replacement_base)

    assert _git(repository, "show", "-s", "--format=%P", extra) == pis005a_check.REPAIR_BASE_COMMIT
    assert (
        _git_no_replace(repository, "show", "-s", "--format=%P", extra)
        == candidate
    )

    pis005a_report = pis005a_check.build_report(repository)
    pis004a_report = pis004a_check.build_report(repository)
    pis005a_failures = _failure_strings(pis005a_report)
    pis004a_failures = _failure_strings(pis004a_report)

    assert any(
        failure.startswith("PIS-005A inherited Git object or topology environment is unsafe:")
        for failure in pis005a_failures
    )
    assert (
        "PIS-005A candidate is not the exact direct child of repair-8"
        in pis005a_failures
    )
    assert any(
        failure.startswith("PIS-004A inherited Git object or topology environment is unsafe:")
        for failure in pis004a_failures
    )
    assert "PIS-004A exact PIS-005A successor identity is invalid" in pis004a_failures


@pytest.mark.parametrize(
    "environment_name",
    [
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_INDEX_FILE",
        "GIT_NAMESPACE",
        "GIT_CONFIG_COUNT",
    ],
)
def test_git_trust_path_rejects_and_sanitizes_inherited_object_resolution_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
) -> None:
    repository = tmp_path / "repository"
    topology = _initialize_exact_candidate_repository(repository, monkeypatch)
    monkeypatch.setenv(environment_name, str(tmp_path / "redirected"))

    assert (
        pis005a_check._git(repository, "rev-parse", "HEAD")  # noqa: SLF001
        == topology["candidate"]
    )
    assert (
        pis004a_check._git_one(repository, "rev-parse", "HEAD")  # noqa: SLF001
        == topology["candidate"]
    )
    assert any(
        failure.startswith("PIS-005A inherited Git object or topology environment is unsafe:")
        for failure in pis005a_check._git_topology_metadata_failures(  # noqa: SLF001
            repository
        )
    )
    assert any(
        failure.startswith("PIS-004A inherited Git object or topology environment is unsafe:")
        for failure in pis004a_check._git_topology_metadata_failures(  # noqa: SLF001
            repository
        )
    )


@pytest.mark.parametrize("linked_worktree", [False, True])
def test_full_report_builders_reject_common_directory_grafts(
    tmp_path: Path,
    linked_worktree: bool,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    checkout = repository
    if linked_worktree:
        checkout = tmp_path / "linked-review"
        _git(repository, "worktree", "add", "-q", "--detach", str(checkout), "HEAD")

    for report in (
        pis005a_check.build_report(checkout),
        pis004a_check.build_report(checkout),
    ):
        assert report["valid"] is True, report["failures"]

    common_directory = Path(
        _git(
            checkout,
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        )
    )
    graft_path = common_directory / "info/grafts"
    graft_path.parent.mkdir(parents=True, exist_ok=True)
    graft_path.write_text(
        f"{_git(checkout, 'rev-parse', 'HEAD')} {pis005a_check.REPAIR_BASE_COMMIT}\n",
        encoding="utf-8",
    )

    pis005a_report = pis005a_check.build_report(checkout)
    pis004a_report = pis004a_check.build_report(checkout)

    assert "PIS-005A legacy graft topology metadata is present" in _failure_strings(
        pis005a_report
    )
    assert "PIS-004A legacy graft topology metadata is present" in _failure_strings(
        pis004a_report
    )


@pytest.mark.parametrize("mutation", ["missing_local", "missing_remote", "predecessor_drift"])
def test_full_report_builders_reject_candidate_ref_absence_and_predecessor_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    repository = _initialize_full_report_candidate_repository(tmp_path)
    if mutation == "missing_local":
        _git(repository, "checkout", "-q", "--detach", "HEAD")
        _git(repository, "update-ref", "-d", f"refs/heads/{pis005a_check.BRANCH}")
    elif mutation == "missing_remote":
        _git(
            repository,
            "update-ref",
            "-d",
            f"refs/remotes/origin/{pis005a_check.BRANCH}",
        )
    else:
        _git(
            repository,
            "update-ref",
            f"refs/heads/{pis005a_check.REPAIR_BASE_BRANCH}",
            "HEAD",
        )

    pis005a_report = pis005a_check.build_report(repository)
    pis004a_report = pis004a_check.build_report(repository)
    pis005a_failures = _failure_strings(pis005a_report)
    pis004a_failures = _failure_strings(pis004a_report)

    assert pis005a_report["valid"] is False
    assert pis004a_report["valid"] is False
    if mutation == "missing_local":
        assert (
            "PIS-005A exact local candidate identity is unavailable"
            in pis005a_failures
        )
        assert (
            "PIS-004A detached PIS-005A successor does not match the fetched commit and tree"
            in pis004a_failures
        )
    elif mutation == "missing_remote":
        assert "PIS-005A fetched candidate identity is unavailable" in pis005a_failures
        assert (
            "PIS-004A named PIS-005A successor does not match local, fetched, and tree identity"
            in pis004a_failures
        )
    else:
        assert (
            "PIS-005A accepted or rejected predecessor identity changed"
            in pis005a_failures
        )
        assert "PIS-004A exact PIS-005A successor identity is invalid" in pis004a_failures


def _write_completed_review_files(repository: Path) -> dict[str, str]:
    candidate = _git(repository, "rev-parse", "HEAD^{commit}")
    candidate_tree = _git(repository, "rev-parse", "HEAD^{tree}")
    contract_path = repository / pis005a_check.CONTRACT_REL
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["status"] = "candidate_independent_review_complete"
    contract["next_action"] = "stop_before_separate_e2_node_005_entry_decision"
    review = contract["independent_review"]
    assert isinstance(review, dict)
    review.update(
        {
            "reviewed_candidate_commit": candidate,
            "reviewed_candidate_tree": candidate_tree,
            "clean_detached_worktree_verified": True,
            "remote_identity_verified": True,
            "focused_gate_passed": True,
            "critical_findings": 0,
            "high_findings": 0,
            "medium_findings": 0,
            "low_findings": 0,
            "open_findings": 0,
            "implementation_review_complete": True,
        }
    )
    contract_path.write_text(
        json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    review_path = repository / pis005a_check.REVIEW_RECORD_REL
    review_path.write_text(
        "\n".join(
            (
                "# PIS-005A Independent Implementation Review",
                "",
                "Status: independent implementation review complete; no open findings.",
                f"Reviewed exact implementation commit: `{candidate}`.",
                f"Reviewed exact tree: `{candidate_tree}`.",
                "Review method: independent read-only Codex review in a clean detached worktree.",
                "Candidate freeze complete: `true`.",
                "Clean detached worktree verified: `true`.",
                "Remote identity verified: `true`.",
                "Focused gate passed: `true`.",
                "Implementation review complete: `true`.",
                "Human UAT complete: `false`.",
                "Live remote transport authorized: `false`.",
                "Release or promotion authorized: `false`.",
                "Critical findings: `0`.",
                "High findings: `0`.",
                "Medium findings: `0`.",
                "Low findings: `0`.",
                "Open findings: `0`.",
                "E2-NODE-005 status: blocked; separate entry decision required.",
                "Current governed tool count: exactly `24`.",
                "",
                "The exact implementation candidate was independently reviewed "
                "in a clean detached worktree.",
                "",
            )
        ),
        encoding="utf-8",
    )

    foundation_path = repository / pis005a_check.DOC_REL
    foundation = foundation_path.read_text(encoding="utf-8").replace(
        "Status: exact implementation candidate frozen; independent review pending.",
        "Status: independent implementation review complete; no open findings.",
        1,
    )
    foundation_path.write_text(
        foundation
        + "\n"
        + f"Reviewed exact implementation commit: `{candidate}`.\n"
        + f"Reviewed exact tree: `{candidate_tree}`.\n",
        encoding="utf-8",
    )
    return {
        "candidate": candidate,
        "candidate_tree": candidate_tree,
    }


def _commit_disposition(repository: Path) -> str:
    _git(repository, "add", "-A")
    _git(repository, "commit", "-q", "-m", "record exact independent review")
    disposition = _git(repository, "rev-parse", "HEAD^{commit}")
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{pis005a_check.BRANCH}",
        disposition,
    )
    return disposition


def _record_completed_review(repository: Path) -> dict[str, str]:
    topology = _write_completed_review_files(repository)
    topology["disposition"] = _commit_disposition(repository)
    return topology


def _initialize_full_report_candidate_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "full-report-repository"
    git_executable = shutil.which("git", path=os.defpath)
    assert git_executable is not None
    subprocess.run(
        [
            git_executable,
            "clone",
            "--quiet",
            str(pis005a_check.ROOT),
            str(repository),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    _git(repository, "config", "user.name", "PIS-005A full report fixture")
    _git(repository, "config", "user.email", "pis005a-full-report@example.invalid")
    _git(
        repository,
        "checkout",
        "-q",
        "-B",
        pis005a_check.BRANCH,
        pis005a_check.REPAIR_BASE_COMMIT,
    )

    candidate_paths: set[str] = set()
    for arguments in (
        ("diff", "--name-only", f"{pis005a_check.REPAIR_BASE_COMMIT}..HEAD"),
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        candidate_paths.update(
            line
            for line in _git(pis005a_check.ROOT, *arguments).splitlines()
            if line
        )
    for relative in sorted(candidate_paths):
        source = pis005a_check.ROOT / relative
        destination = repository / relative
        if source.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        elif destination.exists():
            destination.unlink()

    _git(repository, "add", "-A")
    _git(repository, "commit", "-q", "-m", "PIS-005A repair-9 full report fixture")
    candidate = _git(repository, "rev-parse", "HEAD")
    for branch, commit, _tree in pis005a_check._PREDECESSOR_REFS:  # noqa: SLF001
        _git(repository, "update-ref", f"refs/heads/{branch}", commit)
        _git(repository, "update-ref", f"refs/remotes/origin/{branch}", commit)
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{pis005a_check.BRANCH}",
        candidate,
    )
    return repository


def _initialize_exact_candidate_repository(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, str]:
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "PIS-005A fixture")
    _git(repository, "config", "user.email", "pis005a@example.invalid")
    accepted_branch = "codex/enterprise-e2-pis004a-review-repair"
    branch_order = (
        accepted_branch,
        pis005a_check._ORIGINAL_BRANCH,  # noqa: SLF001
        pis005a_check._REPAIR_2_BRANCH,  # noqa: SLF001
        pis005a_check._REPAIR_3_BRANCH,  # noqa: SLF001
        pis005a_check._REPAIR_4_BRANCH,  # noqa: SLF001
        pis005a_check._REPAIR_5_BRANCH,  # noqa: SLF001
        pis005a_check._REPAIR_6_BRANCH,  # noqa: SLF001
        pis005a_check._REPAIR_7_BRANCH,  # noqa: SLF001
        pis005a_check.REPAIR_BASE_BRANCH,
        pis005a_check.BRANCH,
    )
    labels = (
        "accepted",
        "original",
        "repair-2",
        "repair-3",
        "repair-4",
        "repair-5",
        "repair-6",
        "repair-7",
        "repair-8",
        "candidate",
    )
    history = repository / "history.txt"
    commits: list[str] = []
    trees: list[str] = []
    for index, (branch, label) in enumerate(zip(branch_order, labels, strict=True)):
        if index == 0:
            _git(repository, "checkout", "-q", "-b", branch)
        else:
            _git(repository, "checkout", "-q", "-b", branch, commits[-1])
        prior_history = history.read_text(encoding="utf-8") if history.exists() else ""
        history.write_text(
            prior_history + f"{label}\n",
            encoding="utf-8",
        )
        _git(repository, "add", history.name)
        if label == "candidate":
            for relative in pis005a_check._EXPECTED_POST_REVIEW_PATHS:  # noqa: SLF001
                review_path = repository / relative
                review_path.parent.mkdir(parents=True, exist_ok=True)
                review_path.write_text(
                    "pending review projection\n",
                    encoding="utf-8",
                )
                _git(repository, "add", relative)
        _git(repository, "commit", "-q", "-m", label)
        commits.append(_git(repository, "rev-parse", "HEAD"))
        trees.append(_git(repository, "rev-parse", "HEAD^{tree}"))
    for branch, commit in zip(branch_order, commits, strict=True):
        _git(repository, "update-ref", f"refs/remotes/origin/{branch}", commit)

    monkeypatch.setattr(pis005a_check, "SOURCE_COMMIT", commits[0])
    monkeypatch.setattr(pis005a_check, "SOURCE_TREE", trees[0])
    monkeypatch.setattr(pis005a_check, "_ORIGINAL_COMMIT", commits[1])
    monkeypatch.setattr(pis005a_check, "_ORIGINAL_TREE", trees[1])
    monkeypatch.setattr(pis005a_check, "_REPAIR_2_COMMIT", commits[2])
    monkeypatch.setattr(pis005a_check, "_REPAIR_2_TREE", trees[2])
    monkeypatch.setattr(pis005a_check, "_REPAIR_3_COMMIT", commits[3])
    monkeypatch.setattr(pis005a_check, "_REPAIR_3_TREE", trees[3])
    monkeypatch.setattr(pis005a_check, "_REPAIR_4_COMMIT", commits[4])
    monkeypatch.setattr(pis005a_check, "_REPAIR_4_TREE", trees[4])
    monkeypatch.setattr(pis005a_check, "_REPAIR_5_COMMIT", commits[5])
    monkeypatch.setattr(pis005a_check, "_REPAIR_5_TREE", trees[5])
    monkeypatch.setattr(pis005a_check, "_REPAIR_6_COMMIT", commits[6])
    monkeypatch.setattr(pis005a_check, "_REPAIR_6_TREE", trees[6])
    monkeypatch.setattr(pis005a_check, "_REPAIR_7_COMMIT", commits[7])
    monkeypatch.setattr(pis005a_check, "_REPAIR_7_TREE", trees[7])
    monkeypatch.setattr(pis005a_check, "REPAIR_BASE_COMMIT", commits[8])
    monkeypatch.setattr(pis005a_check, "REPAIR_BASE_TREE", trees[8])
    monkeypatch.setattr(
        pis005a_check,
        "_PREDECESSOR_REFS",
        tuple(zip(branch_order[:-1], commits[:-1], trees[:-1], strict=True)),
    )
    monkeypatch.setattr(
        pis005a_check,
        "_REPAIR_PARENT_CHAIN",
        tuple((commits[index], commits[index - 1]) for index in range(2, 9)),
    )
    monkeypatch.setattr(pis005a_check, "REJECTED_CANDIDATE_COMMITS", set(commits[1:9]))
    return {
        "candidate": commits[9],
        "candidate_tree": trees[9],
        "repair_base": commits[8],
        "repair_base_tree": trees[8],
    }


def _git(
    root: Path,
    *arguments: str,
    stdin: str | None = None,
) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        input=stdin,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_no_replace(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "--no-replace-objects", *arguments],
        cwd=root,
        env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"},
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()

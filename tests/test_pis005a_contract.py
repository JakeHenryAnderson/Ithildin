from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts import production_identity_storage_pis_005a_check as pis005a_check


def _contract() -> dict[str, object]:
    return pis005a_check.load_contract(
        pis005a_check.ROOT / pis005a_check.CONTRACT_REL,
    )


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
    candidate = _git(repository, "rev-parse", "HEAD")
    candidate_tree = _git(repository, "rev-parse", "HEAD^{tree}")

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


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts import e2_lineage_reconciliation_check as reconciliation


def _record() -> dict[str, object]:
    return reconciliation.load_record(reconciliation.ROOT / reconciliation.RECORD_REL)


def test_live_reconciliation_candidate_is_exact_and_bounded() -> None:
    report = reconciliation.build_report(
        reconciliation.ROOT,
        run_external_gates=False,
        verify_live_refs=False,
    )

    assert report["valid"] is True, report["failures"]
    assert report["record_status"] == "candidate_independent_review_pending"
    assert report["candidate_branch"] == reconciliation.BRANCH
    assert report["raw_parents"] == [reconciliation.M_COMMIT]
    assert report["governed_tool_count"] == 24
    assert report["runtime_authority"] == "Gateway"
    assert report["human_uat_complete"] is False
    assert report["release_allowed"] is False
    assert report["e2_id_005a_implementation_authorized"] is False


def test_record_is_closed_and_rejects_extra_keys() -> None:
    record = _record()
    assert record == reconciliation.EXPECTED_RECORD
    record["unexpected"] = True

    assert reconciliation.validate_record(record) == [
        "E2 lineage reconciliation record keys or values are not exact"
    ]


@pytest.mark.parametrize(
    "field",
    [
        "e2_id_005a_implementation_authorized",
        "pis_collection_action_authorized",
        "remote_transport_allowed",
        "production_identity_allowed",
        "runtime_postgres_allowed",
        "release_allowed",
        "production_allowed",
        "production_promotion_allowed",
        "human_uat_complete",
    ],
)
def test_record_rejects_any_true_authority_field(field: str) -> None:
    record = copy.deepcopy(_record())
    authority = record["authority"]
    assert isinstance(authority, dict)
    authority[field] = True

    assert reconciliation.validate_record(record) == [
        "E2 lineage reconciliation record keys or values are not exact"
    ]


def test_record_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema_version":"1","schema_version":"2"}\n')

    with pytest.raises(ValueError, match="duplicate JSON key: schema_version"):
        reconciliation.load_record(duplicate)


def test_frozen_artifact_validation_rejects_product_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = reconciliation._git_blob  # noqa: SLF001

    def drifted(root: Path, revision: str, relative: str) -> bytes:
        value = original(root, revision, relative)
        if relative == reconciliation.PRODUCT_ARTIFACTS[0]:
            return value + b"drift"
        return value

    monkeypatch.setattr(reconciliation, "_git_blob", drifted)

    assert any(
        failure.startswith("product checkpoint artifact drifted:")
        for failure in reconciliation.validate_frozen_artifacts(reconciliation.ROOT)
    )


def test_protected_ref_validation_rejects_local_or_tracking_movement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reconciliation, "_git_or_none", lambda *_args: "0" * 40)

    failures = reconciliation._protected_ref_failures(  # noqa: SLF001
        reconciliation.ROOT,
        verify_live_refs=False,
    )

    assert len(failures) == len(reconciliation.PROTECTED_REFS)
    assert all("protected local or tracking ref moved" in failure for failure in failures)


def test_git_validation_rejects_wrong_merge_parent_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reconciliation, "M_COMMIT", "0" * 40)

    report = reconciliation.validate_git_bindings(
        reconciliation.ROOT,
        verify_live_refs=False,
    )

    assert report["failures"]
    assert any(
        "reconciliation candidate branch, identity, or sole parent is invalid" in failure
        for failure in report["failures"]
    )

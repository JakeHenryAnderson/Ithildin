from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from scripts import enterprise_e2_scale_fixture


def test_scale_fixture_is_deterministic_bounded_and_semantically_complete() -> None:
    first = enterprise_e2_scale_fixture.build_fixture()
    second = enterprise_e2_scale_fixture.build_fixture()
    report = enterprise_e2_scale_fixture.build_report(first)

    assert first == second
    assert enterprise_e2_scale_fixture.canonical_bytes(first) == (
        enterprise_e2_scale_fixture.canonical_bytes(second)
    )
    assert report["valid"] is True, report["failures"]
    assert report["tool_count"] == 24
    assert report["counts"] == enterprise_e2_scale_fixture.EXPECTED_COUNTS
    assert report["runtime_import_allowed"] is False
    assert report["production_identity_allowed"] is False
    assert report["supported_scale_claim_allowed"] is False
    assert report["human_uat_complete"] is False


def test_scale_fixture_rejects_authority_truth_source_and_sensitive_field_drift() -> None:
    fixture: dict[str, Any] = copy.deepcopy(
        enterprise_e2_scale_fixture.build_fixture()
    )
    fixture["authority"]["runtime_import_allowed"] = True
    fixture["missions"][0]["model_provider_state"] = "healthy"
    fixture["nodes"][0]["runner_health_state"] = "healthy"
    fixture["approvals"][0]["client_secret"] = "must-not-appear"
    fixture["evidence"][0]["unexpected_metadata"] = "not-closed"

    failures = enterprise_e2_scale_fixture.validate_fixture(fixture)

    assert "fixture authority boundary is not exact" in failures
    assert "mission fixture overclaims model-provider state" in failures
    assert "Node fixture overclaims runner health" in failures
    assert any("forbidden key" in failure for failure in failures)
    assert "fixture collection keys are not closed: approvals" in failures
    assert "fixture collection keys are not closed: evidence" in failures


def test_scale_fixture_round_trip_is_exclusive(tmp_path: Path) -> None:
    output = tmp_path / "enterprise-e2-scale-fixture.json"

    enterprise_e2_scale_fixture.write_fixture(output)
    loaded = enterprise_e2_scale_fixture.load_fixture(output)

    assert enterprise_e2_scale_fixture.validate_fixture(loaded) == []
    with pytest.raises(enterprise_e2_scale_fixture.ScaleFixtureError):
        enterprise_e2_scale_fixture.write_fixture(output)

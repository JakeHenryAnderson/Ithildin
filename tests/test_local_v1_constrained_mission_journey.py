from __future__ import annotations

import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest
from ithildin_schemas import JsonObject, sha256_digest

from scripts import local_v1_constrained_mission_journey as journey
from scripts import local_v1_constrained_mission_journey_check as checker

CANDIDATE = "a" * 40
TREE = "b" * 40
RUN_ID = "20260724T180000Z-1234abcd"


def _receipts() -> tuple[JsonObject, JsonObject]:
    profile = json.loads(journey.PROFILE_PATH.read_text(encoding="utf-8"))
    assert isinstance(profile, dict)
    profile_object: JsonObject = profile
    profile_digest = sha256_digest(profile_object)
    hermes = profile_object["hermes"]
    assert isinstance(hermes, dict)
    platforms = hermes["platform_digests"]
    assert isinstance(platforms, dict)
    tmpfs = profile_object["limits"]
    assert isinstance(tmpfs, dict)
    tmpfs_limits = tmpfs["tmpfs"]
    assert isinstance(tmpfs_limits, dict)
    build: JsonObject = {
        "candidate_commit": CANDIDATE,
        "candidate_tree": TREE,
        "clean_before_bridge_build": True,
        "clean_after_bridge_build": True,
        "clean_before_node_build": True,
        "clean_after_node_build": True,
        "bridge_source_digest": journey.source_digest(journey.BRIDGE_SOURCE_PATHS),
        "node_source_digest": journey.source_digest(journey.NODE_SOURCE_PATHS),
        "dependency_lock_digest": journey.file_digest(journey.ROOT / "uv.lock"),
        "hermes_oci_index_digest": hermes["oci_index_digest"],
        "hermes_platform_digest": platforms["linux/arm64"],
        "profile_digest": profile_digest,
        "bridge_image_digest": "sha256:" + ("1" * 64),
        "node_image_digest": "sha256:" + ("2" * 64),
        "platform": "linux/arm64",
        "image_artifact_inventory_digest": "sha256:" + ("3" * 64),
        "license_source_inventory_digest": "sha256:" + ("4" * 64),
    }
    mission_id = "mission_" + ("5" * 32)
    claim_id = "mclaim_" + ("6" * 32)
    envelope_digest = "sha256:" + ("7" * 64)
    session_id = f"mission:{mission_id}:{claim_id}:{'7' * 16}"
    run_id = "run_" + ("9" * 32)
    observed: JsonObject = {
        "candidate_commit": CANDIDATE,
        "candidate_tree": TREE,
        "mission_id": mission_id,
        "claim_id": claim_id,
        "envelope_digest": envelope_digest,
        "profile_digest": profile_digest,
        "handoff_nonce_digest": "sha256:" + ("8" * 64),
        "authority": "gateway_agent_run_evidence",
        "correlation_basis": "gateway_validated_claim_session",
        "rejected_correlation_count": 0,
        "mission_session_id": session_id,
        "gateway_agent_runs": [
            {
                "run_id": run_id,
                "session_id": session_id,
                "mission_id": mission_id,
                "claim_id": claim_id,
                "envelope_digest": envelope_digest,
                "authority": "gateway_agent_run_evidence",
                "correlation_basis": "gateway_validated_claim_session",
                "tool_call_count": 2,
                "status": "active",
            }
        ],
        "gateway_operation_bindings": [
            {
                "operation_index": index,
                "event_id": "evt_" + (str(index) * 32),
                "event_hash": "sha256:" + (str(index + 1) * 64),
                "event_type": "tool.execution.completed",
                "tool_name": tool_name,
                "request_id": "req_" + (str(index) * 32),
                "run_id": run_id,
                "session_id": session_id,
                "mission_id": mission_id,
                "claim_id": claim_id,
                "envelope_digest": envelope_digest,
                "authority": "gateway_agent_run_evidence",
                "correlation_basis": "gateway_validated_claim_session",
                "status": "completed",
            }
            for index, tool_name in enumerate(
                ["project.structure.summary", "project.test.summary"],
                start=1,
            )
        ],
        "gateway_lifecycle_state": "runner_reported_succeeded",
        "runner_state_authority": "runner_reported_only",
        "model_provider_state_known": False,
        "container_absent": True,
        "volumes_absent": True,
        "network_absent": True,
        "persistent_profile_volume_absent": True,
        "run_specific_images_absent": True,
        "runtime_plaintext_absent": True,
        "read_only_root": True,
        "logging_driver": "none",
        "tmpfs_limits": tmpfs_limits,
    }
    return build, observed


def test_constrained_journey_binds_candidate_sources_profile_agent_run_and_cleanup() -> None:
    build, observed = _receipts()
    report = journey.build_report(
        build,
        observed,
        expected_candidate=CANDIDATE,
        expected_tree=TREE,
        observed_at=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        run_id=RUN_ID,
    )

    assert report["candidate_commit"] == CANDIDATE
    assert report["candidate_tree"] == TREE
    limits = report["evidence_limits"]
    assert isinstance(limits, dict)
    assert all(value is False for value in limits.values())
    assert "project.structure.summary" in json.dumps(report)
    assert "project.test.summary" in json.dumps(report)
    assert "governed_result" not in json.dumps(report)
    journey.validate_report(report, expected_candidate=CANDIDATE)


@pytest.mark.parametrize(
    ("section", "field", "value", "reason"),
    [
        ("build", "candidate_tree", "c" * 40, "candidate or tree identity differs"),
        ("build", "clean_after_node_build", False, "dirty source observation"),
        (
            "build",
            "profile_digest",
            "sha256:" + ("f" * 64),
            "profile_digest differs",
        ),
        (
            "journey",
            "authority",
            "runner_reported_only",
            "authority or correlation is invalid",
        ),
        (
            "journey",
            "correlation_basis",
            "unvalidated_session",
            "authority or correlation is invalid",
        ),
        (
            "journey",
            "rejected_correlation_count",
            1,
            "authority or correlation is invalid",
        ),
        (
            "journey",
            "rejected_correlation_count",
            False,
            "authority or correlation is invalid",
        ),
        ("journey", "container_absent", False, "cleanup is incomplete"),
    ],
)
def test_constrained_journey_rejects_identity_drift_dirty_build_and_incomplete_evidence(
    section: str,
    field: str,
    value: object,
    reason: str,
) -> None:
    build, observed = _receipts()
    target = build if section == "build" else observed
    target[field] = value  # type: ignore[assignment]
    with pytest.raises(journey.ConstrainedJourneyError, match=reason):
        journey.build_report(
            build,
            observed,
            expected_candidate=CANDIDATE,
            expected_tree=TREE,
            run_id=RUN_ID,
        )


@pytest.mark.parametrize(
    ("section", "field", "value", "reason"),
    [
        (
            "run",
            "authority",
            "runner_reported_only",
            "Agent Run binding is invalid",
        ),
        (
            "run",
            "tool_call_count",
            1,
            "Agent Run binding is invalid",
        ),
        (
            "run",
            "tool_call_count",
            2.0,
            "Agent Run binding is invalid",
        ),
        (
            "run",
            "tool_call_count",
            "2",
            "Agent Run binding is invalid",
        ),
        (
            "run",
            "tool_call_count",
            True,
            "Agent Run binding is invalid",
        ),
        (
            "binding",
            "operation_index",
            True,
            "operation binding is invalid",
        ),
        (
            "binding",
            "run_id",
            "run_" + ("f" * 32),
            "operation binding is invalid",
        ),
        (
            "binding",
            "session_id",
            "mission:" + ("f" * 16),
            "operation binding is invalid",
        ),
        (
            "binding",
            "tool_name",
            "fs.read",
            "operation binding is invalid",
        ),
        (
            "binding",
            "event_id",
            "evt_" + ("f" * 31),
            "operation binding is invalid",
        ),
        (
            "binding",
            "event_hash",
            "sha256:" + ("f" * 63),
            "operation binding is invalid",
        ),
        (
            "binding",
            "event_type",
            "tool.execution.started",
            "operation binding is invalid",
        ),
        (
            "binding",
            "status",
            "failed",
            "operation binding is invalid",
        ),
    ],
)
def test_constrained_journey_rejects_agent_run_and_operation_false_positive_mutations(
    section: str,
    field: str,
    value: object,
    reason: str,
) -> None:
    build, observed = _receipts()
    entries = observed[
        "gateway_agent_runs" if section == "run" else "gateway_operation_bindings"
    ]
    assert isinstance(entries, list)
    entry = entries[0]
    assert isinstance(entry, dict)
    entry[field] = value

    with pytest.raises(journey.ConstrainedJourneyError, match=reason):
        journey.build_report(
            build,
            observed,
            expected_candidate=CANDIDATE,
            expected_tree=TREE,
            run_id=RUN_ID,
        )


def test_constrained_journey_rejects_duplicate_gateway_event_identity() -> None:
    build, observed = _receipts()
    bindings = observed["gateway_operation_bindings"]
    assert isinstance(bindings, list)
    first, second = bindings
    assert isinstance(first, dict)
    assert isinstance(second, dict)
    second["event_id"] = first["event_id"]

    with pytest.raises(journey.ConstrainedJourneyError, match="event binding is ambiguous"):
        journey.build_report(
            build,
            observed,
            expected_candidate=CANDIDATE,
            expected_tree=TREE,
            run_id=RUN_ID,
        )


def test_constrained_journey_checker_requires_selected_private_canonical_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_base = tmp_path / "var" / "local-v1-constrained-mission-journey"
    monkeypatch.setattr(journey, "REPORT_BASE", report_base)
    monkeypatch.setattr(checker, "REPORT_BASE", report_base)
    build, observed = _receipts()
    report = journey.build_report(
        build,
        observed,
        expected_candidate=CANDIDATE,
        expected_tree=TREE,
        run_id=RUN_ID,
    )
    report_root = journey.write_report(report)

    checked = checker.check_report(report_root, expected_candidate=CANDIDATE)

    assert checked == report
    assert stat.S_IMODE(report_root.stat().st_mode) == 0o700
    assert stat.S_IMODE((report_root / journey.REPORT_JSON).stat().st_mode) == 0o600
    with pytest.raises(checker.ConstrainedJourneyCheckError, match="outside"):
        checker.check_report(tmp_path, expected_candidate=CANDIDATE)


def test_evidence_receipt_reader_rejects_unsafe_parent_mode_and_symlink(
    tmp_path: Path,
) -> None:
    receipt_parent = tmp_path / "receipts"
    receipt_parent.mkdir(mode=0o700)
    receipt = receipt_parent / "build.json"
    receipt.write_text("{}", encoding="utf-8")
    receipt.chmod(0o600)
    receipt_parent.chmod(0o755)

    with pytest.raises(journey.ConstrainedJourneyError, match="directory is unsafe"):
        journey.read_closed_receipt(receipt)

    receipt_parent.chmod(0o700)
    symlink = receipt_parent / "selected.json"
    os.symlink(receipt.name, symlink)
    with pytest.raises(journey.ConstrainedJourneyError, match="receipt is unavailable"):
        journey.read_closed_receipt(symlink)

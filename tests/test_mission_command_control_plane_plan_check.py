import json
import shutil
from pathlib import Path

import pytest

from scripts import mission_command_control_plane_plan_check


def test_mission_command_control_plane_plan_is_bounded_and_valid() -> None:
    report = mission_command_control_plane_plan_check.build_report(Path("."))

    assert report["valid"], report["failures"]
    assert report["tool_count"] == 24
    assert report["mission_admission_implementation_authorized"] is True
    assert report["node_signed_delivery_implementation_authorized"] is True
    assert report["runner_bridge_authorized"] is False
    assert report["runner_lifecycle_authority"] is False
    assert report["model_provider_authority"] is False
    assert report["arbitrary_host_control_authorized"] is False
    assert report["production_identity_authorized"] is False
    assert report["uat_required_now"] is False
    assert report["runner_bridge_candidate"] == "fixed_hermes_runner_bridge"
    assert (
        report["runner_bridge_candidate_disposition"]
        == "design_only_candidate_ready_for_exact_review"
    )
    assert report["runner_bridge_implementation_authorized"] is False
    assert report["separate_runner_bridge_capability_decision_required"] is True


def test_contract_rejects_duplicate_members() -> None:
    text = """
<!-- mission-command-contract:start -->
{"document_type":"architecture","document_type":"capability_decision"}
<!-- mission-command-contract:end -->
"""

    with pytest.raises(
        mission_command_control_plane_plan_check.ContractError,
        match="unambiguous JSON",
    ):
        mission_command_control_plane_plan_check._contract(text)


def test_plan_rejects_substituted_digest_bound_input(tmp_path: Path) -> None:
    repo = _packet_copy(tmp_path)
    architecture = repo / mission_command_control_plane_plan_check.ARCHITECTURE
    architecture.write_text(
        architecture.read_text(encoding="utf-8") + "\nsubstituted\n",
        encoding="utf-8",
    )

    report = mission_command_control_plane_plan_check.build_report(repo)

    assert report["valid"] is False
    assert any("architecture_sha256" in failure for failure in report["failures"])


def test_plan_reads_actual_tool_surface(tmp_path: Path) -> None:
    repo = _packet_copy(tmp_path)
    lock_path = repo / "tool-manifests.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["manifests"] = lock["manifests"][:-1]
    lock_path.write_text(json.dumps(lock), encoding="utf-8")

    report = mission_command_control_plane_plan_check.build_report(repo)

    assert report["valid"] is False
    assert report["tool_count"] == 23
    assert "actual governed tool count changed: 23" in report["failures"]


def test_runner_bridge_evaluation_fails_closed_if_authority_rises(tmp_path: Path) -> None:
    repo = _packet_copy(tmp_path)
    evaluation_path = (
        repo / mission_command_control_plane_plan_check.RUNNER_BRIDGE_EVALUATION
    )
    text = evaluation_path.read_text(encoding="utf-8")
    evaluation_path.write_text(
        text.replace(
            '"implementation_authorized":false',
            '"implementation_authorized":true',
            1,
        ),
        encoding="utf-8",
    )

    report = mission_command_control_plane_plan_check.build_report(repo)

    assert report["valid"] is False
    assert report["runner_bridge_implementation_authorized"] is True
    assert any(
        "implementation_authorized must equal False" in failure
        for failure in report["failures"]
    )


def test_runner_bridge_evaluation_rejects_unknown_authority_field(tmp_path: Path) -> None:
    repo = _packet_copy(tmp_path)
    evaluation_path = (
        repo / mission_command_control_plane_plan_check.RUNNER_BRIDGE_EVALUATION
    )
    text = evaluation_path.read_text(encoding="utf-8")
    evaluation_path.write_text(
        text.replace(
            '"capability_selected":false',
            '"host_shutdown_authorized":true,"capability_selected":false',
            1,
        ),
        encoding="utf-8",
    )

    report = mission_command_control_plane_plan_check.build_report(repo)

    assert report["valid"] is False
    assert any("contract fields are not closed" in failure for failure in report["failures"])


def _packet_copy(tmp_path: Path) -> Path:
    for relative in (
        *mission_command_control_plane_plan_check.DOCS,
        "tool-manifests.lock.json",
        "Makefile",
        "README.md",
        "scripts/build_docs_site.py",
        "scripts/review_docs.py",
        "docs/codex/review-docs-index.md",
    ):
        source = Path(relative)
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return tmp_path

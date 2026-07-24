from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts import mission_command_runner_bridge_decision_check as decision_check


def test_live_runner_bridge_decision_is_selected_but_not_authorized() -> None:
    report = decision_check.build_report(Path("."))
    contract = decision_check._contract(  # noqa: SLF001
        Path(decision_check.DECISION).read_text(encoding="utf-8")
    )

    assert report["valid"] is True, report["failures"]
    assert report["tool_count"] == 24
    assert report["capability_selected"] is True
    assert report["implementation_authorized"] is False
    assert report["runner_bridge_authorized"] is False
    assert report["new_governed_tool"] is False
    assert report["arbitrary_host_control_authorized"] is False
    assert report["exact_candidate_review_required"] is True
    assert report["post_review_authorization_required"] is True
    assert contract["same_candidate_equality_fields"] == [
        "candidate_commit",
        "candidate_tree",
    ]
    assert contract["runner_root_filesystem_read_only"] is True
    assert contract["runner_persistent_session_volume"] is False
    assert contract["runner_logging_driver"] == "none"
    assert contract["failed_cleanup_blocks_retry"] is True


def test_runner_bridge_decision_rejects_authority_rise(tmp_path: Path) -> None:
    repo = _copy_inputs(tmp_path)
    path = repo / decision_check.DECISION
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            '"implementation_authorized":false',
            '"implementation_authorized":true',
            1,
        ),
        encoding="utf-8",
    )

    report = decision_check.build_report(repo)

    assert report["valid"] is False
    assert report["implementation_authorized"] is True
    assert any(
        "implementation_authorized must remain false" in failure
        for failure in report["failures"]
    )


def test_runner_bridge_decision_rejects_unknown_contract_field(tmp_path: Path) -> None:
    repo = _copy_inputs(tmp_path)
    path = repo / decision_check.DECISION
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            '"capability_selected":true',
            '"host_shutdown_authorized":false,"capability_selected":true',
            1,
        ),
        encoding="utf-8",
    )

    report = decision_check.build_report(repo)

    assert report["valid"] is False
    assert "runner-bridge decision contract fields are not closed" in report["failures"]


def test_runner_bridge_decision_binds_antecedent_hashes(tmp_path: Path) -> None:
    repo = _copy_inputs(tmp_path)
    path = repo / decision_check.EVALUATION
    path.write_text(
        path.read_text(encoding="utf-8") + "\nsubstituted\n",
        encoding="utf-8",
    )

    report = decision_check.build_report(repo)

    assert report["valid"] is False
    assert any("candidate_evaluation_sha256" in failure for failure in report["failures"])


def test_runner_bridge_decision_reads_actual_tool_count(tmp_path: Path) -> None:
    repo = _copy_inputs(tmp_path)
    lock_path = repo / "tool-manifests.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["manifests"] = lock["manifests"][:-1]
    lock_path.write_text(json.dumps(lock), encoding="utf-8")

    report = decision_check.build_report(repo)

    assert report["valid"] is False
    assert report["tool_count"] == 23
    assert "actual governed tool count changed: 23" in report["failures"]


def test_runner_bridge_decision_requires_local_v1_milestone_wiring(
    tmp_path: Path,
) -> None:
    repo = _copy_inputs(tmp_path)
    makefile_path = repo / "Makefile"
    makefile_path.write_text(
        makefile_path.read_text(encoding="utf-8").replace(
            "\t$(MAKE) mission-command-runner-bridge-decision-check\n",
            "",
            1,
        ),
        encoding="utf-8",
    )

    report = decision_check.build_report(repo)

    assert report["valid"] is False
    assert any("local-v1-milestone-check" in failure for failure in report["failures"])


def test_runner_bridge_decision_requires_exact_release_wiring(tmp_path: Path) -> None:
    repo = _copy_inputs(tmp_path)
    makefile_path = repo / "Makefile"
    makefile_path.write_text(
        makefile_path.read_text(encoding="utf-8").replace(
            "release-check: mission-command-runner-bridge-decision-check\n",
            "unrelated-check: mission-command-runner-bridge-decision-check\n",
            1,
        ),
        encoding="utf-8",
    )

    report = decision_check.build_report(repo)

    assert report["valid"] is False
    assert any("release-check dependency" in failure for failure in report["failures"])


def test_runner_bridge_decision_requires_existing_package_mapping(tmp_path: Path) -> None:
    repo = _copy_inputs(tmp_path)
    pyproject_path = repo / "pyproject.toml"
    pyproject_path.write_text(
        pyproject_path.read_text(encoding="utf-8").replace(
            'ithildin_mcp_server = "apps/mcp-server/src/ithildin_mcp_server"',
            'ithildin_mcp_server = "apps/mcp-server/src/substituted"',
            1,
        ),
        encoding="utf-8",
    )

    report = decision_check.build_report(repo)

    assert report["valid"] is False
    assert any("package mapping is unavailable" in failure for failure in report["failures"])


def _copy_inputs(tmp_path: Path) -> Path:
    paths = (
        decision_check.DECISION,
        decision_check.EVALUATION,
        decision_check.EVALUATION_REVIEW,
        "deploy/hermes-poc/Dockerfile",
        "pyproject.toml",
        "tool-manifests.lock.json",
        "Makefile",
        "README.md",
        "scripts/build_docs_site.py",
        "scripts/review_docs.py",
        "docs/codex/review-docs-index.md",
    )
    for relative in paths:
        source = Path(relative)
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return tmp_path

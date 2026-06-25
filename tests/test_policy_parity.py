from __future__ import annotations

import json
from pathlib import Path

import pytest
from ithildin_api.policy_parity import (
    PolicyParityError,
    load_policy_parity_tests,
    run_policy_parity,
)

from scripts import policy_parity as policy_parity_script


def test_committed_policy_parity_fixtures_pass(tmp_path: Path) -> None:
    run = run_policy_parity(repo_root=Path("."), work_dir=tmp_path)

    assert run.failed == 0
    assert run.passed == 24
    decisions = {case.id: case.preview_decision for case in run.cases}
    assert decisions["read_preview_matches_runtime"] == "allow"
    assert decisions["write_preview_matches_runtime"] == "require_approval"
    assert decisions["git_commit_metadata_preview_matches_runtime"] == "allow"
    assert decisions["git_ref_summary_preview_matches_runtime"] == "allow"
    assert decisions["git_tag_metadata_preview_matches_runtime"] == "allow"
    assert decisions["project_manifest_summary_preview_matches_runtime"] == "allow"
    assert decisions["project_dependency_summary_preview_matches_runtime"] == "allow"
    assert decisions["project_structure_summary_preview_matches_runtime"] == "allow"
    assert decisions["project_test_summary_preview_matches_runtime"] == "allow"
    assert decisions["project_docs_summary_preview_matches_runtime"] == "allow"
    assert decisions["project_language_summary_preview_matches_runtime"] == "allow"
    assert decisions["project_config_summary_preview_matches_runtime"] == "allow"
    assert decisions["project_ci_summary_preview_matches_runtime"] == "allow"
    assert decisions["project_release_summary_preview_matches_runtime"] == "allow"
    assert decisions["project_risk_summary_preview_matches_runtime"] == "allow"
    assert decisions["out_of_scope_network_preview_matches_runtime"] == "deny"
    assert decisions["invalid_arguments_preview_matches_runtime"] == "deny"
    assert decisions["invalid_http_arguments_preview_matches_runtime"] == "deny"
    assert decisions["readonly_network_visibility_matches_runtime"] == "deny"
    assert decisions["empty_principal_preview_matches_runtime"] == "deny"


def test_policy_parity_detects_expected_decision_mismatch(tmp_path: Path) -> None:
    fixture = tmp_path / "parity.yaml"
    fixture.write_text(
        """
version: test
cases:
  - id: mismatch
    tool_name: fs.list
    arguments: {path: "."}
    principal: {id: agent:mcp-local}
    session_id: mismatch
    expect_decision: deny
""",
        encoding="utf-8",
    )

    run = run_policy_parity(
        repo_root=Path("."),
        work_dir=tmp_path / "work",
        tests_path=fixture,
    )

    assert run.failed == 1
    assert "expected deny" in run.cases[0].failures[0]


def test_policy_parity_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    fixture = tmp_path / "parity.yaml"
    fixture.write_text(
        """
version: test
cases:
  - id: duplicate
    tool_name: fs.list
    principal: {id: agent:mcp-local}
    session_id: one
  - id: duplicate
    tool_name: fs.list
    principal: {id: agent:mcp-local}
    session_id: two
""",
        encoding="utf-8",
    )

    with pytest.raises(PolicyParityError, match="duplicate"):
        load_policy_parity_tests(fixture)


def test_policy_parity_cli_json_emits_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = policy_parity_script.main(
        [
            "--repo-root",
            ".",
            "--work-dir",
            str(tmp_path),
            "--json",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert status == 0
    assert output["failed"] == 0
    assert output["passed"] == 24

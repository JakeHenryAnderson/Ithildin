from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from ithildin_api.policy_testing import PolicyTestError, load_policy_tests, run_policy_tests


def write_policy(path: Path) -> None:
    path.write_text(
        """
version: test-policy-v1
rules:
  - id: deny_shell
    decision: deny
    reason: shell denied
    match:
      tool.name_prefix:
        - shell.
    obligations:
      audit_level: full

  - id: allow_reads
    decision: allow
    reason: reads allowed
    match:
      tool.risk: read
      resource.in_scope: true
    obligations:
      audit_level: full
      max_execution_seconds: 30
      review:
        mode: sampled
        owner: security

  - id: approve_writes
    decision: require_approval
    reason: writes need review
    match:
      tool.risk: write
    obligations:
      audit_level: full
      approval_required: true
""",
        encoding="utf-8",
    )


def write_fixture(path: Path, *, decision: str = "allow") -> None:
    path.write_text(
        f"""
version: test-fixtures-v1
cases:
  - id: read_case
    policy_input:
      principal:
        id: "agent:test"
        roles:
          - AgentDeveloper
      tool:
        name: fs.read
        risk: read
        version: "0.1.0"
      resource:
        type: file
        path: README.md
        in_scope: true
      context:
        session_id: policy-test
    expect:
      decision: {decision}
      matched_rules:
        - allow_reads
      reason_contains: reads
      obligations_contains:
        review:
          mode: sampled
""",
        encoding="utf-8",
    )


def test_committed_default_policy_fixtures_pass() -> None:
    result = run_policy_tests(
        policy_path=Path("policies/default.yaml"),
        tests_path=Path("policies/tests/default.yaml"),
    )

    assert result.failed == 0
    assert result.passed == 10
    assert result.policy_hash.startswith("sha256:")


def test_policy_test_harness_reports_mismatched_decision(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    tests_path = tmp_path / "tests.yaml"
    write_policy(policy_path)
    write_fixture(tests_path, decision="deny")

    result = run_policy_tests(policy_path=policy_path, tests_path=tests_path)

    assert result.failed == 1
    assert "decision expected deny, got allow" in result.cases[0].failures


def test_policy_test_harness_reports_mismatched_matched_rules(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    tests_path = tmp_path / "tests.yaml"
    write_policy(policy_path)
    write_fixture(tests_path)
    contents = tests_path.read_text(encoding="utf-8").replace("allow_reads", "other_rule")
    tests_path.write_text(contents, encoding="utf-8")

    result = run_policy_tests(policy_path=policy_path, tests_path=tests_path)

    assert result.failed == 1
    assert "matched_rules expected ['other_rule'], got ['allow_reads']" in result.cases[0].failures


def test_policy_test_harness_rejects_missing_required_fixture_fields(tmp_path: Path) -> None:
    tests_path = tmp_path / "tests.yaml"
    tests_path.write_text(
        """
version: test-fixtures-v1
cases:
  - id: missing_expect
    policy_input:
      principal: {}
      tool: {}
      resource: {}
      context: {}
""",
        encoding="utf-8",
    )

    with pytest.raises(PolicyTestError, match="invalid policy test fixture schema"):
        load_policy_tests(tests_path)


def test_policy_test_harness_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    tests_path = tmp_path / "tests.yaml"
    tests_path.write_text(
        """
version: test-fixtures-v1
cases:
  - id: duplicate
    policy_input:
      principal: {id: "agent:test"}
      tool: {name: fs.read, risk: read}
      resource: {in_scope: true}
      context: {}
    expect:
      decision: allow
  - id: duplicate
    policy_input:
      principal: {id: "agent:test"}
      tool: {name: fs.read, risk: read}
      resource: {in_scope: true}
      context: {}
    expect:
      decision: allow
""",
        encoding="utf-8",
    )

    with pytest.raises(PolicyTestError, match="duplicate policy test case id: duplicate"):
        load_policy_tests(tests_path)


def test_policy_test_harness_reports_policy_load_errors(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    tests_path = tmp_path / "tests.yaml"
    policy_path.write_text("version: [", encoding="utf-8")
    write_fixture(tests_path)

    with pytest.raises(PolicyTestError, match="invalid YAML policy"):
        run_policy_tests(policy_path=policy_path, tests_path=tests_path)


def test_policy_test_harness_matches_nested_obligation_subsets(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    tests_path = tmp_path / "tests.yaml"
    write_policy(policy_path)
    write_fixture(tests_path)

    result = run_policy_tests(policy_path=policy_path, tests_path=tests_path)

    assert result.failed == 0


def test_policy_test_json_output_is_stable() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/policy_test.py",
            "--policy-path",
            "policies/default.yaml",
            "--tests-path",
            "policies/tests/default.yaml",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["version"] == "default-policy-tests-v1"
    assert payload["passed"] == 10
    assert payload["failed"] == 0
    assert payload["policy_path"] == "policies/default.yaml"
    assert [case["id"] for case in payload["cases"]][:2] == [
        "allow_agent_in_scope_read",
        "allow_readonly_agent_in_scope_read",
    ]


def test_policy_test_cli_exits_nonzero_for_failures(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    tests_path = tmp_path / "tests.yaml"
    write_policy(policy_path)
    write_fixture(tests_path, decision="deny")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/policy_test.py",
            "--policy-path",
            str(policy_path),
            "--tests-path",
            str(tests_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "Policy tests: 0/1 passed" in completed.stdout
    assert "decision expected deny, got allow" in completed.stderr

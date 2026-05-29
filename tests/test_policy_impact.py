from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest
from ithildin_api.policy_impact import PolicyImpactError, PolicyImpactService
from ithildin_schemas import JsonObject


def write_policy(path: Path, *, decision: str = "allow", rule_id: str = "allow_reads") -> None:
    path.write_text(
        f"""
version: test-policy-v1
rules:
  - id: {rule_id}
    decision: {decision}
    reason: fixture decision
    match:
      tool.risk: read
    obligations:
      audit_level: full
""",
        encoding="utf-8",
    )


def write_fixtures(path: Path) -> None:
    path.write_text(
        """
version: test-fixtures-v1
cases:
  - id: read_case
    policy_input:
      principal: {id: "agent:test", roles: ["AgentDeveloper"]}
      tool: {name: fs.read, risk: read, version: "0.1.0"}
      resource: {type: file, path: README.md, in_scope: true}
      context: {session_id: policy-test}
    expect:
      decision: allow
      matched_rules: [allow_reads]
""",
        encoding="utf-8",
    )


def test_policy_impact_reports_changed_decision_and_fixture_failure(tmp_path: Path) -> None:
    current_path = tmp_path / "current.yaml"
    candidate_path = tmp_path / "candidate.yaml"
    tests_path = tmp_path / "tests.yaml"
    write_policy(current_path)
    write_policy(candidate_path, decision="deny", rule_id="deny_reads")
    write_fixtures(tests_path)
    service = PolicyImpactService(current_policy_path=current_path, tests_path=tests_path)

    result = service.preview_candidate_path(candidate_path)
    current = cast(JsonObject, result["current"])
    candidate = cast(JsonObject, result["candidate"])

    assert current["failed"] == 0
    assert candidate["failed"] == 1
    assert result["changed_cases"] == [
        {
            "id": "read_case",
            "changes": ["decision", "matched_rules"],
            "current": {
                "decision": "allow",
                "matched_rules": ["allow_reads"],
                "reason": "fixture decision",
                "obligations": {"audit_level": "full"},
                "passed": True,
                "failures": [],
            },
            "candidate": {
                "decision": "deny",
                "matched_rules": ["deny_reads"],
                "reason": "fixture decision",
                "obligations": {"audit_level": "full"},
                "passed": False,
                "failures": [
                    "decision expected allow, got deny",
                    "matched_rules expected ['allow_reads'], got ['deny_reads']",
                ],
            },
        }
    ]


def test_policy_impact_rejects_invalid_candidate_policy(tmp_path: Path) -> None:
    current_path = tmp_path / "current.yaml"
    candidate_path = tmp_path / "candidate.yaml"
    tests_path = tmp_path / "tests.yaml"
    write_policy(current_path)
    candidate_path.write_text("version: [", encoding="utf-8")
    write_fixtures(tests_path)
    service = PolicyImpactService(current_policy_path=current_path, tests_path=tests_path)

    with pytest.raises(PolicyImpactError, match="invalid YAML policy"):
        service.preview_candidate_path(candidate_path)


def test_policy_impact_cli_json_output_is_stable(tmp_path: Path) -> None:
    current_path = tmp_path / "current.yaml"
    candidate_path = tmp_path / "candidate.yaml"
    tests_path = tmp_path / "tests.yaml"
    write_policy(current_path)
    write_policy(candidate_path)
    write_fixtures(tests_path)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/policy_impact.py",
            "--policy-path",
            str(current_path),
            "--tests-path",
            str(tests_path),
            "--candidate-path",
            str(candidate_path),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["current"]["failed"] == 0
    assert payload["candidate"]["failed"] == 0
    assert payload["changed_cases"] == []

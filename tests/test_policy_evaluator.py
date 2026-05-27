from __future__ import annotations

from pathlib import Path

import pytest
from ithildin_policy_core import PolicyError, PolicyEvaluator
from ithildin_schemas import PolicyDecisionValue, PolicyInput


def write_policy(path: Path) -> None:
    path.write_text(
        """
version: test-v1
rules:
  - id: deny_dangerous_tool_names
    decision: deny
    reason: dangerous tools denied
    match:
      tool.name_prefix:
        - shell.
        - docker.
        - secrets.
        - fs.delete
    obligations:
      audit_level: full

  - id: deny_destructive_risk
    decision: deny
    reason: destructive tools denied
    match:
      tool.risk: destructive
    obligations:
      audit_level: full

  - id: require_approval_for_writes
    decision: require_approval
    reason: writes require approval
    match:
      tool.risk: write
    obligations:
      audit_level: full
      approval_required: true
      max_execution_seconds: 30

  - id: allow_in_scope_reads
    decision: allow
    reason: in-scope read allowed
    match:
      tool.risk: read
      resource.in_scope: true
    obligations:
      audit_level: full
      max_execution_seconds: 30
""",
        encoding="utf-8",
    )


def policy_input(tool_name: str, tool_risk: str, in_scope: bool = True) -> PolicyInput:
    return PolicyInput(
        principal={"id": "agent:local-dev", "roles": ["AgentDeveloper"]},
        tool={"name": tool_name, "risk": tool_risk, "version": "1.0.0"},
        resource={"type": "file", "path": "/workspace/README.md", "in_scope": in_scope},
        context={"session_id": "sess_123"},
    )


def test_policy_allows_in_scope_reads(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    evaluator = PolicyEvaluator.load(policy_path)

    decision = evaluator.evaluate(policy_input("fs.read", "read"))

    assert decision.decision == PolicyDecisionValue.ALLOW
    assert decision.matched_rules == ["allow_in_scope_reads"]
    assert decision.policy_version.startswith("sha256:")
    assert decision.obligations["audit_level"] == "full"
    assert evaluator.status() == {
        "engine": "yaml",
        "document_version": "test-v1",
        "policy_hash": evaluator.policy_hash,
        "rule_count": 4,
    }


def test_policy_requires_approval_for_writes(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    evaluator = PolicyEvaluator.load(policy_path)

    decision = evaluator.evaluate(policy_input("fs.apply_patch", "write"))

    assert decision.decision == PolicyDecisionValue.REQUIRE_APPROVAL
    assert decision.matched_rules == ["require_approval_for_writes"]
    assert decision.obligations["approval_required"] is True


@pytest.mark.parametrize(
    ("tool_name", "tool_risk"),
    [
        ("shell.run", "write"),
        ("docker.create", "write"),
        ("secrets.read", "read"),
        ("fs.delete", "write"),
        ("fs.remove", "destructive"),
    ],
)
def test_policy_denies_dangerous_tools(
    tmp_path: Path,
    tool_name: str,
    tool_risk: str,
) -> None:
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    evaluator = PolicyEvaluator.load(policy_path)

    decision = evaluator.evaluate(policy_input(tool_name, tool_risk))

    assert decision.decision == PolicyDecisionValue.DENY
    assert decision.matched_rules[0].startswith("deny_")


def test_policy_defaults_to_deny_when_no_rule_matches(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    evaluator = PolicyEvaluator.load(policy_path)

    decision = evaluator.evaluate(policy_input("fs.read", "read", in_scope=False))

    assert decision.decision == PolicyDecisionValue.DENY
    assert decision.reason == "no matching policy rule"
    assert decision.matched_rules == []


def test_policy_can_match_principal_role_membership(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
version: test-v1
rules:
  - id: allow_developer_reads
    decision: allow
    reason: developer reads allowed
    match:
      tool.risk: read
      principal.roles_contains:
        - Developer
        - AgentDeveloper
""",
        encoding="utf-8",
    )
    evaluator = PolicyEvaluator.load(policy_path)

    allowed = evaluator.evaluate(policy_input("fs.read", "read"))
    denied = evaluator.evaluate(
        PolicyInput(
            principal={"id": "agent:readonly", "roles": ["AgentReadOnly"]},
            tool={"name": "fs.read", "risk": "read", "version": "1.0.0"},
            resource={"type": "file", "path": "README.md", "in_scope": True},
            context={"session_id": "sess_123"},
        )
    )

    assert allowed.decision == PolicyDecisionValue.ALLOW
    assert allowed.matched_rules == ["allow_developer_reads"]
    assert denied.decision == PolicyDecisionValue.DENY


def test_invalid_policy_fails_closed(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("version: test\n", encoding="utf-8")

    with pytest.raises(PolicyError):
        PolicyEvaluator.load(policy_path)


def test_invalid_policy_yaml_fails_closed(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("version: [", encoding="utf-8")

    with pytest.raises(PolicyError):
        PolicyEvaluator.load(policy_path)

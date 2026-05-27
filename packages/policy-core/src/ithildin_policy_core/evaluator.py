"""Deterministic YAML policy evaluator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from ithildin_schemas import (
    JsonObject,
    JsonValue,
    PolicyDecision,
    PolicyDecisionValue,
    PolicyInput,
    sha256_digest,
)
from ithildin_schemas.models import StrictBaseModel
from pydantic import Field, ValidationError


class PolicyError(RuntimeError):
    """Raised when policy cannot be loaded or evaluated safely."""


class PolicyRule(StrictBaseModel):
    id: str
    decision: PolicyDecisionValue
    reason: str
    match: JsonObject = Field(default_factory=dict)
    obligations: JsonObject = Field(default_factory=dict)


class PolicyDocument(StrictBaseModel):
    version: str
    rules: list[PolicyRule]


class PolicyEvaluator:
    engine_name = "yaml"

    def __init__(self, policy: PolicyDocument, policy_hash: str) -> None:
        self.policy = policy
        self.policy_hash = policy_hash

    @property
    def document_version(self) -> str:
        return self.policy.version

    @property
    def rule_count(self) -> int:
        return len(self.policy.rules)

    def status(self) -> JsonObject:
        return {
            "engine": self.engine_name,
            "document_version": self.document_version,
            "policy_hash": self.policy_hash,
            "rule_count": self.rule_count,
        }

    @classmethod
    def load(cls, policy_path: Path) -> PolicyEvaluator:
        try:
            raw_policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise PolicyError(f"policy file not found: {policy_path}") from exc
        except yaml.YAMLError as exc:
            raise PolicyError(f"invalid YAML policy: {policy_path}") from exc

        if not isinstance(raw_policy, dict):
            raise PolicyError(f"policy must be a mapping: {policy_path}")

        policy_data = _json_object(raw_policy)
        try:
            policy = PolicyDocument.model_validate(policy_data)
        except ValidationError as exc:
            raise PolicyError(f"invalid policy schema: {policy_path}") from exc

        return cls(policy=policy, policy_hash=sha256_digest(policy_data))

    def evaluate(self, policy_input: PolicyInput) -> PolicyDecision:
        for rule in self.policy.rules:
            if _matches(rule.match, policy_input):
                return PolicyDecision(
                    decision=rule.decision,
                    reason=rule.reason,
                    policy_version=self.policy_hash,
                    matched_rules=[rule.id],
                    obligations=rule.obligations,
                )

        return PolicyDecision(
            decision=PolicyDecisionValue.DENY,
            reason="no matching policy rule",
            policy_version=self.policy_hash,
            matched_rules=[],
            obligations={"audit_level": "full"},
        )


def _matches(matchers: JsonObject, policy_input: PolicyInput) -> bool:
    input_data = policy_input.model_dump(mode="json")
    return all(_matcher_matches(input_data, key, expected) for key, expected in matchers.items())


def _matcher_matches(input_data: dict[str, Any], key: str, expected: JsonValue) -> bool:
    if key == "tool.name_prefix":
        actual_name = _lookup(input_data, "tool.name")
        if not isinstance(actual_name, str):
            return False
        prefixes = expected if isinstance(expected, list) else [expected]
        return any(
            isinstance(prefix, str) and actual_name.startswith(prefix) for prefix in prefixes
        )

    actual = _lookup(input_data, key)
    if isinstance(expected, list):
        return bool(actual in expected)
    return bool(actual == expected)


def _lookup(input_data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = input_data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _json_object(value: dict[Any, Any]) -> JsonObject:
    result: JsonObject = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise PolicyError("policy keys must be strings")
        result[key] = item
    return result

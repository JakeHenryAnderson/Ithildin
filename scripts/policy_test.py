"""Run offline policy decision fixtures against the YAML policy evaluator."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml
from ithildin_policy_core import PolicyError, PolicyEvaluator
from ithildin_schemas import JsonObject, JsonValue, PolicyDecisionValue, PolicyInput
from ithildin_schemas.models import StrictBaseModel
from pydantic import Field, ValidationError


class PolicyTestError(RuntimeError):
    """Raised when policy fixtures cannot be loaded or evaluated safely."""


class PolicyExpectation(StrictBaseModel):
    decision: PolicyDecisionValue
    matched_rules: list[str] | None = None
    reason_contains: str | None = None
    obligations_contains: JsonObject = Field(default_factory=dict)


class PolicyTestCase(StrictBaseModel):
    id: str
    description: str | None = None
    policy_input: PolicyInput
    expect: PolicyExpectation


class PolicyTestDocument(StrictBaseModel):
    version: str
    cases: list[PolicyTestCase]


@dataclass(frozen=True)
class PolicyCaseResult:
    id: str
    passed: bool
    failures: list[str]
    decision: str
    matched_rules: list[str]
    reason: str

    def as_dict(self) -> JsonObject:
        return cast(
            JsonObject,
            {
                "id": self.id,
                "passed": self.passed,
                "failures": self.failures,
                "decision": self.decision,
                "matched_rules": self.matched_rules,
                "reason": self.reason,
            },
        )


@dataclass(frozen=True)
class PolicyTestRun:
    version: str
    policy_path: Path
    tests_path: Path
    policy_hash: str
    cases: list[PolicyCaseResult]

    @property
    def passed(self) -> int:
        return sum(1 for result in self.cases if result.passed)

    @property
    def failed(self) -> int:
        return len(self.cases) - self.passed

    def as_dict(self) -> JsonObject:
        return {
            "version": self.version,
            "policy_path": self.policy_path.as_posix(),
            "tests_path": self.tests_path.as_posix(),
            "policy_hash": self.policy_hash,
            "passed": self.passed,
            "failed": self.failed,
            "cases": [result.as_dict() for result in self.cases],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-path", type=Path, default=Path("policies/default.yaml"))
    parser.add_argument("--tests-path", type=Path, default=Path("policies/tests/default.yaml"))
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON results")
    args = parser.parse_args()

    try:
        run = run_policy_tests(policy_path=args.policy_path, tests_path=args.tests_path)
    except PolicyTestError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, sort_keys=True, indent=2))
        else:
            print(f"policy test error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(run.as_dict(), sort_keys=True, indent=2))
    else:
        print(f"Policy tests: {run.passed}/{len(run.cases)} passed")
        for result in run.cases:
            if not result.passed:
                print(f"- {result.id}: {'; '.join(result.failures)}", file=sys.stderr)
    return 0 if run.failed == 0 else 1


def run_policy_tests(*, policy_path: Path, tests_path: Path) -> PolicyTestRun:
    try:
        evaluator = PolicyEvaluator.load(policy_path)
    except PolicyError as exc:
        raise PolicyTestError(str(exc)) from exc
    document = load_policy_tests(tests_path)
    results = [_run_case(evaluator, case) for case in document.cases]
    return PolicyTestRun(
        version=document.version,
        policy_path=policy_path,
        tests_path=tests_path,
        policy_hash=evaluator.policy_hash,
        cases=results,
    )


def load_policy_tests(tests_path: Path) -> PolicyTestDocument:
    try:
        raw_tests = yaml.safe_load(tests_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PolicyTestError(f"policy tests file not found: {tests_path}") from exc
    except yaml.YAMLError as exc:
        raise PolicyTestError(f"invalid policy tests YAML: {tests_path}") from exc

    if not isinstance(raw_tests, dict):
        raise PolicyTestError(f"policy tests must be a mapping: {tests_path}")
    try:
        document = PolicyTestDocument.model_validate(_json_object(raw_tests))
    except ValidationError as exc:
        raise PolicyTestError(f"invalid policy test fixture schema: {tests_path}") from exc

    seen: set[str] = set()
    for case in document.cases:
        if case.id in seen:
            raise PolicyTestError(f"duplicate policy test case id: {case.id}")
        seen.add(case.id)
    return document


def _run_case(evaluator: PolicyEvaluator, case: PolicyTestCase) -> PolicyCaseResult:
    decision = evaluator.evaluate(case.policy_input)
    failures: list[str] = []

    if decision.decision != case.expect.decision:
        failures.append(
            f"decision expected {case.expect.decision.value}, got {decision.decision.value}"
        )
    if (
        case.expect.matched_rules is not None
        and decision.matched_rules != case.expect.matched_rules
    ):
        failures.append(
            f"matched_rules expected {case.expect.matched_rules}, got {decision.matched_rules}"
        )
    if (
        case.expect.reason_contains is not None
        and case.expect.reason_contains not in decision.reason
    ):
        failures.append(f"reason did not contain {case.expect.reason_contains!r}")
    if case.expect.obligations_contains and not _json_subset(
        expected=case.expect.obligations_contains,
        actual=decision.obligations,
    ):
        failures.append(
            "obligations did not contain "
            f"{json.dumps(case.expect.obligations_contains, sort_keys=True)}"
        )

    return PolicyCaseResult(
        id=case.id,
        passed=not failures,
        failures=failures,
        decision=decision.decision.value,
        matched_rules=decision.matched_rules,
        reason=decision.reason,
    )


def _json_subset(*, expected: JsonObject, actual: JsonObject) -> bool:
    for key, expected_value in expected.items():
        if key not in actual:
            return False
        actual_value = actual[key]
        if isinstance(expected_value, dict):
            if not isinstance(actual_value, dict):
                return False
            if not _json_subset(expected=expected_value, actual=actual_value):
                return False
        elif actual_value != expected_value:
            return False
    return True


def _json_object(value: dict[Any, Any]) -> JsonObject:
    result: JsonObject = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise PolicyTestError("policy test keys must be strings")
        result[key] = cast(JsonValue, item)
    return result


if __name__ == "__main__":
    raise SystemExit(main())

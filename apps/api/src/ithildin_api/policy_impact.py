"""Offline policy impact preview helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import cast

from ithildin_schemas import JsonObject

from scripts.policy_test import PolicyCaseResult, PolicyTestError, PolicyTestRun, run_policy_tests


class PolicyImpactError(RuntimeError):
    """Raised when a policy impact preview cannot be produced safely."""


class PolicyImpactService:
    def __init__(self, *, current_policy_path: Path, tests_path: Path) -> None:
        self.current_policy_path = current_policy_path
        self.tests_path = tests_path

    def preview_candidate_yaml(self, candidate_policy_yaml: str) -> JsonObject:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yaml") as candidate:
            candidate.write(candidate_policy_yaml)
            candidate.flush()
            return self.preview_candidate_path(Path(candidate.name))

    def preview_candidate_path(self, candidate_policy_path: Path) -> JsonObject:
        try:
            current = run_policy_tests(
                policy_path=self.current_policy_path,
                tests_path=self.tests_path,
            )
            candidate = run_policy_tests(
                policy_path=candidate_policy_path,
                tests_path=self.tests_path,
            )
        except PolicyTestError as exc:
            raise PolicyImpactError(str(exc)) from exc

        return cast(
            JsonObject,
            {
                "current": _run_summary(current),
                "candidate": _run_summary(candidate),
                "changed_cases": _changed_cases(current, candidate),
            },
        )


def _run_summary(run: PolicyTestRun) -> JsonObject:
    return cast(
        JsonObject,
        {
            "version": run.version,
            "policy_path": run.policy_path.as_posix(),
            "tests_path": run.tests_path.as_posix(),
            "policy_hash": run.policy_hash,
            "passed": run.passed,
            "failed": run.failed,
            "case_count": len(run.cases),
            "failures": [
                {"id": result.id, "failures": result.failures}
                for result in run.cases
                if not result.passed
            ],
        },
    )


def _changed_cases(current: PolicyTestRun, candidate: PolicyTestRun) -> list[JsonObject]:
    current_by_id = {result.id: result for result in current.cases}
    changed: list[JsonObject] = []
    for candidate_case in candidate.cases:
        current_case = current_by_id.get(candidate_case.id)
        if current_case is None:
            changed.append(
                cast(
                    JsonObject,
                    {
                        "id": candidate_case.id,
                        "changes": ["case_added"],
                        "current": None,
                        "candidate": _case_snapshot(candidate_case),
                    },
                )
            )
            continue
        changes = _case_changes(current_case, candidate_case)
        if changes:
            changed.append(
                cast(
                    JsonObject,
                    {
                        "id": candidate_case.id,
                        "changes": changes,
                        "current": _case_snapshot(current_case),
                        "candidate": _case_snapshot(candidate_case),
                    },
                )
            )
    return changed


def _case_changes(current: PolicyCaseResult, candidate: PolicyCaseResult) -> list[str]:
    changes: list[str] = []
    if current.decision != candidate.decision:
        changes.append("decision")
    if current.matched_rules != candidate.matched_rules:
        changes.append("matched_rules")
    if current.reason != candidate.reason:
        changes.append("reason")
    if current.obligations != candidate.obligations:
        changes.append("obligations")
    return changes


def _case_snapshot(result: PolicyCaseResult) -> JsonObject:
    return cast(
        JsonObject,
        {
            "decision": result.decision,
            "matched_rules": result.matched_rules,
            "reason": result.reason,
            "obligations": result.obligations,
            "passed": result.passed,
            "failures": result.failures,
        },
    )

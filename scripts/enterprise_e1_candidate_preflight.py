"""Validate exact, clean Enterprise E1 candidate identity before and after its gate."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from scripts import enterprise_e1_contract_check

ROOT = Path(__file__).resolve().parents[1]
COMMIT = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_BRANCH = "codex/enterprise-single-site-operations"


def _git(root: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip()


def build_report(
    root: Path,
    expected_candidate: str,
) -> dict[str, Any]:
    failures: list[str] = []
    head_code, head = _git(root, "rev-parse", "HEAD")
    tree_code, tree = _git(root, "rev-parse", "HEAD^{tree}")
    branch_code, branch = _git(root, "branch", "--show-current")
    status_code, status = _git(
        root, "status", "--porcelain=v1", "--untracked-files=normal"
    )
    if not COMMIT.fullmatch(expected_candidate):
        failures.append("expected candidate must be 40 lowercase hex characters")
    if head_code != 0 or head != expected_candidate:
        failures.append("checkout HEAD does not match the expected E1 candidate")
    if tree_code != 0 or not COMMIT.fullmatch(tree):
        failures.append("candidate tree identity is unavailable")
    if branch_code != 0 or branch != EXPECTED_BRANCH:
        failures.append("candidate is not on the isolated E1 branch")
    if status_code != 0:
        failures.append("candidate checkout status is unavailable")
    if status:
        failures.append("candidate checkout is not clean")

    contract = enterprise_e1_contract_check.build_report(root)
    failures.extend(
        f"completion contract: {failure}" for failure in contract["failures"]
    )
    expected_outcome_statuses = {
        "E1-O1": "complete",
        "E1-O2": "complete",
        "E1-O3": "complete",
        "E1-O4": "complete",
        "E1-O5": "complete",
        "E1-O6": "in_progress",
    }
    expected_milestone_statuses = {
        "E1-M1": "complete",
        "E1-M2": "complete",
        "E1-M3": "complete",
        "E1-M4": "complete",
        "E1-M5": "complete",
        "E1-M6": "in_progress",
    }
    if contract.get("outcome_statuses") != expected_outcome_statuses:
        failures.append("candidate outcome states are not at the 5/6 freeze boundary")
    if contract.get("milestone_statuses") != expected_milestone_statuses:
        failures.append("candidate milestone states are not at the 5/6 freeze boundary")
    if contract.get("next_action") != "E1-M6":
        failures.append("candidate next action is not E1-M6")
    if any(
        contract.get(key) is not False
        for key in (
            "candidate_gate_complete",
            "independent_review_complete",
            "human_uat_packet_ready",
            "human_uat_complete",
            "pis_collection_action_authority",
        )
    ):
        failures.append("candidate qualification or PIS authority is already asserted")
    if contract.get("tool_count") != 24:
        failures.append("candidate governed tool count is not 24")
    return {
        "valid": not failures,
        "failures": failures,
        "candidate_commit": head,
        "candidate_tree": tree,
        "candidate_tree_clean": status == "",
        "branch": branch,
        "source_commit_is_ancestor": contract.get("source_commit_is_ancestor"),
        "tool_count": contract.get("tool_count"),
        "outcomes_complete": contract.get("outcomes_complete"),
        "milestones_complete": contract.get("milestones_complete"),
        "next_action": contract.get("next_action"),
        "candidate_gate_complete": contract.get("candidate_gate_complete"),
        "independent_review_complete": contract.get("independent_review_complete"),
        "human_uat_packet_ready": contract.get("human_uat_packet_ready"),
        "human_uat_complete": contract.get("human_uat_complete"),
        "pis_collection_action_authority": contract.get(
            "pis_collection_action_authority"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-candidate", required=True)
    args = parser.parse_args()
    report = build_report(ROOT, args.expected_candidate)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

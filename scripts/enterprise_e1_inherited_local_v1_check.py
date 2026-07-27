"""Validate frozen Local v1 qualification as immutable Enterprise E1 lineage."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import local_v1_contract_check

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "0ef2fae9a06da7455a25017e5773caa52e7c8db6"
FROZEN_CANDIDATE = "ab4162d8f4b6d3f45a68f33316f4b765a45765db"
FROZEN_TREE = "25be9f049ca3ff3ccf6721100944e36baa0c3b05"
LOCAL_V1_EXACT_ONLY_TARGET = "local-v1-o2-evidence-check"
DESCENDANT_LINEAGE_TARGET = "enterprise-e1-inherited-local-v1-check"
DESCENDANT_INVENTORY_TARGET = "enterprise-e1-local-v1-descendant-inventory"
PROTECTED_LOCAL_V1_RECORDS = (
    "docs/codex/local-v1-completion-contract.md",
    "docs/codex/local-v1-release-disposition.json",
    "docs/codex/local-v1-candidate-identity.md",
    "docs/codex/local-v1-candidate-gate.md",
    "docs/codex/local-v1-independent-review.md",
    "docs/codex/local-v1-human-uat-packet.md",
    "docs/codex/local-v1-human-uat-record-template.md",
    "docs/codex/local-v1-lv1-007-o2-disposition.json",
    "docs/codex/local-v1-lv1-007-o2-disposition.md",
)


def _git(root: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip()


def _target_body(makefile: str, target: str) -> str:
    match = re.search(
        rf"^{re.escape(target)}:[ \t]*(?:[^\n]*)\n((?:\t[^\n]*\n?)*)",
        makefile,
        re.MULTILINE,
    )
    return match.group(1) if match else ""


def expected_descendant_targets() -> tuple[str, ...]:
    return tuple(
        DESCENDANT_LINEAGE_TARGET
        if target == LOCAL_V1_EXACT_ONLY_TARGET
        else target
        for target in local_v1_contract_check.LOCAL_V1_CANDIDATE_TARGETS
    )


def build_report(root: Path) -> dict[str, Any]:
    failures: list[str] = []
    head_code, head = _git(root, "rev-parse", "HEAD")
    tree_code, frozen_tree = _git(
        root,
        "rev-parse",
        f"{FROZEN_CANDIDATE}^{{tree}}",
    )
    source_ancestor_code, _ = _git(
        root,
        "merge-base",
        "--is-ancestor",
        SOURCE_COMMIT,
        head,
    )
    frozen_ancestor_code, _ = _git(
        root,
        "merge-base",
        "--is-ancestor",
        FROZEN_CANDIDATE,
        SOURCE_COMMIT,
    )
    protected_diff_code, protected_diff = _git(
        root,
        "diff",
        "--name-only",
        SOURCE_COMMIT,
        "--",
        *PROTECTED_LOCAL_V1_RECORDS,
    )

    if head_code != 0 or not re.fullmatch(r"[0-9a-f]{40}", head):
        failures.append("current Enterprise E1 commit identity is unavailable")
    if source_ancestor_code != 0:
        failures.append("required Enterprise E1 source commit is not an ancestor")
    if frozen_ancestor_code != 0:
        failures.append("frozen Local v1 candidate is not an ancestor of the E1 source")
    if tree_code != 0 or frozen_tree != FROZEN_TREE:
        failures.append("frozen Local v1 candidate tree identity drifted")
    if protected_diff_code != 0:
        failures.append("protected Local v1 record comparison failed")
    changed_protected_records = tuple(
        path for path in protected_diff.splitlines() if path
    )
    if changed_protected_records:
        failures.append("protected Local v1 qualification records changed")

    contract = local_v1_contract_check.build_report(root)
    failures.extend(
        f"Local v1 completion contract: {failure}"
        for failure in contract.get("failures", ())
    )
    expected_contract_state = {
        "valid": True,
        "tool_count": 24,
        "candidate_evidence_complete": True,
        "independent_review_evidence_complete": True,
        "human_uat_complete": False,
        "release_accepted": False,
        "runtime_authority_granted": False,
        "new_governed_powers_authorized": False,
    }
    for field, expected in expected_contract_state.items():
        if contract.get(field) != expected:
            failures.append(
                f"Local v1 inherited state is invalid: {field}={contract.get(field)!r}"
            )

    makefile_path = root / "Makefile"
    if not makefile_path.is_file():
        failures.append("Makefile is unavailable")
        makefile = ""
    else:
        makefile = makefile_path.read_text(encoding="utf-8")
    inventory_body = _target_body(makefile, DESCENDANT_INVENTORY_TARGET)
    descendant_targets = tuple(
        re.findall(
            r"^\t\$\(MAKE\) ([a-z0-9][a-z0-9-]*)$",
            inventory_body,
            re.MULTILINE,
        )
    )
    expected_targets = expected_descendant_targets()
    if descendant_targets != expected_targets:
        failures.append("Enterprise E1 Local v1 descendant inventory drifted")

    return {
        "schema_version": "ithildin.enterprise-e1-inherited-local-v1.v1",
        "valid": not failures,
        "failures": failures,
        "current_commit": head,
        "source_commit": SOURCE_COMMIT,
        "source_commit_is_ancestor": source_ancestor_code == 0,
        "frozen_candidate": FROZEN_CANDIDATE,
        "frozen_candidate_tree": frozen_tree,
        "frozen_candidate_is_source_ancestor": frozen_ancestor_code == 0,
        "protected_record_count": len(PROTECTED_LOCAL_V1_RECORDS),
        "changed_protected_records": changed_protected_records,
        "candidate_evidence_complete": contract.get("candidate_evidence_complete"),
        "independent_review_evidence_complete": contract.get(
            "independent_review_evidence_complete"
        ),
        "human_uat_complete": contract.get("human_uat_complete"),
        "release_accepted": contract.get("release_accepted"),
        "tool_count": contract.get("tool_count"),
        "descendant_inventory_target_count": len(descendant_targets),
        "historical_exact_only_target_reexecuted": (
            LOCAL_V1_EXACT_ONLY_TARGET in descendant_targets
        ),
    }


def main() -> int:
    report = build_report(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

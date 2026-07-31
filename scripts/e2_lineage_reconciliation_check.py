"""Validate the exact post-PIS E2 lineage reconciliation candidate."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import product_line_acceptance_checkpoint as product_checkpoint
from scripts import production_identity_storage_pis_005a_check as pis005a_check

ROOT = Path(__file__).resolve().parents[1]
RECORD_REL = Path("docs/codex/e2-lineage-reconciliation-checkpoint.json")
DOC_REL = Path("docs/codex/e2-lineage-reconciliation-checkpoint.md")
BRANCH = "codex/e2-control-tower-lineage-reconciliation-repair-1"
REJECTED_BRANCH = "codex/e2-control-tower-lineage-reconciliation"

MAIN_COMMIT = "cc4de49be0ac7915b33c412fc9b06128fa690a26"
MAIN_TREE = "139d2036f8da6f2e806f11bdbcc9d6451c34e94b"
MERGE_BASE = "9df7a04cec197fd4953de692793a32e69c107b49"
PRODUCT_COMMIT = "4a6b9e5061874a26c5f9d20a39818930866a6d55"
PRODUCT_TREE = "2914c134d29e62c031f2778fa31fd858c4ac5276"
E2_COMMIT = "e86f5a19e4e067d73141246f78304597e6cc28a0"
E2_TREE = "6dbbcf0bef3320dfdfa4142f2d30b798b01511d0"
PIS004A_COMMIT = "e8e6a75ca3d76a233243f5e890091f3c95731da9"
PIS004A_TREE = "1a5a6c818bf3fd5e17bcffedaae4cf5497e1e6f2"
PIS004A_PARENT = "ff358753c50037c2bc936b761f249cf5c9115749"
REPAIR_8_COMMIT = "88f9717198709bfa7b5d520bb4aa41c427543042"
REVIEWED_COMMIT = "a23dd3c525bf748a632d8ad3ebd9597883dc0842"
REVIEWED_TREE = "c37ff1043cdfe4511fa35a63cd7fd1675f85c797"
DISPOSITION_COMMIT = "afb81bdc023a300ba49d48d5fddcc8babbf44575"
DISPOSITION_TREE = "3afbe2381fcd490bf2e511695c00fb05dd226e9b"
F_COMMIT = "c10c6051a62a62fb5618909295828782147428f2"
F_TREE = "1b3002c64e2891ae6a3a2519e4015ac3a1f56beb"
M_COMMIT = "b06e8399674f17c188f6502c320a6d2746d24532"
M_TREE = "855dbd27cc6cc9788a955ff7a6a10e12583c3332"
REJECTED_COMMIT = "51c625a3f3538308c356747e170c9f79f83df41f"
REJECTED_TREE = "99329bbf0e0da7b40d6a1e0ba9ba7dac8557a7ad"

PROTECTED_REFS = {
    "main": MAIN_COMMIT,
    "codex/product-line-acceptance-checkpoint": PRODUCT_COMMIT,
    "codex/enterprise-e2-production-identity-prep": E2_COMMIT,
    "codex/enterprise-e2-pis004a-review-repair": PIS004A_COMMIT,
    "codex/enterprise-e2-pis005a-node-identity": (
        "fce0a3668db5150cf0aa75de1fd914b296a2e099"
    ),
    "codex/enterprise-e2-pis005a-review-repair-2": (
        "1542bd0469e18a0ae52cc48920f30b4e41518513"
    ),
    "codex/enterprise-e2-pis005a-review-repair-3": (
        "afd13f98440d4cd9c032b6a996db133bdf78055d"
    ),
    "codex/enterprise-e2-pis005a-review-repair-4": (
        "22566cae4a1bc84dca20747d7bd1531d77d7f025"
    ),
    "codex/enterprise-e2-pis005a-review-repair-5": (
        "cedcf5d0bf3baeab12f54600a247a61a4671d7f9"
    ),
    "codex/enterprise-e2-pis005a-review-repair-6": (
        "735877b2bb387a50dfbd376d6d3d8c047fd49c8f"
    ),
    "codex/enterprise-e2-pis005a-review-repair-7": (
        "3c4060ca997089228debfff7c082f6fd5c96fb04"
    ),
    "codex/enterprise-e2-pis005a-review-repair-8": REPAIR_8_COMMIT,
    "codex/enterprise-e2-pis005a-review-repair-9": DISPOSITION_COMMIT,
    REJECTED_BRANCH: REJECTED_COMMIT,
}

EXPECTED_FROZEN_GATE_LABELS = (
    "exact_product_checkpoint",
    "exact_pis005a_report",
    "exact_pis004a_report",
    "complete_repaired_pis_fixture_matrix",
    "exact_e2_preparation",
)
EXPECTED_LIVE_REF_EVIDENCE: dict[str, Any] = {
    "status": "verified",
    "remote": "origin",
    "protected_ref_count": len(PROTECTED_REFS),
    "local_tracking_live_match": True,
}

PRODUCT_ARTIFACTS = (
    "docs/codex/product-line-acceptance-checkpoint.json",
    "docs/codex/product-line-acceptance-checkpoint.md",
    "scripts/product_line_acceptance_checkpoint.py",
    "tests/test_product_line_acceptance_checkpoint.py",
)
FROZEN_PIS_REVIEW_DOCS = (
    "docs/codex/production-identity-storage-pis-005a-entry-and-implementation-contract.json",
    "docs/codex/production-identity-storage-pis-005a-independent-review.md",
    "docs/codex/production-identity-storage-pis-005a-node-workload-identity-foundation.md",
)
E2_FROZEN_ARTIFACTS = (
    "docs/codex/enterprise-e2-preparation-contract.json",
    "docs/codex/enterprise-e2-production-identity-preparation.md",
)
M_FIRST_PARENT_PATHS = {
    "Makefile": "M",
    "README.md": "M",
    "docs/codex/product-line-acceptance-checkpoint.json": "A",
    "docs/codex/product-line-acceptance-checkpoint.md": "A",
    "docs/codex/review-docs-index.md": "M",
    "scripts/build_docs_site.py": "M",
    "scripts/product_line_acceptance_checkpoint.py": "A",
    "scripts/review_docs.py": "M",
    "tests/test_product_line_acceptance_checkpoint.py": "A",
}
R_PATHS = {
    "Makefile": "M",
    "README.md": "M",
    "docs/codex/e2-lineage-reconciliation-checkpoint.json": "A",
    "docs/codex/e2-lineage-reconciliation-checkpoint.md": "A",
    "docs/codex/review-docs-index.md": "M",
    "scripts/build_docs_site.py": "M",
    "scripts/e2_lineage_reconciliation_check.py": "A",
    "scripts/review_docs.py": "M",
    "tests/test_e2_lineage_reconciliation_check.py": "A",
}
REPAIR_PATHS = {
    "docs/codex/e2-lineage-reconciliation-checkpoint.json": "M",
    "docs/codex/e2-lineage-reconciliation-checkpoint.md": "M",
    "scripts/e2_lineage_reconciliation_check.py": "M",
    "tests/test_e2_lineage_reconciliation_check.py": "M",
}

EXPECTED_RECORD: dict[str, Any] = {
    "schema_version": "1",
    "record_type": "ithildin_e2_lineage_reconciliation_checkpoint",
    "record_status": "candidate_independent_review_pending",
    "recorded_on": "2026-07-31",
    "sources": {
        "main": {"branch": "main", "commit": MAIN_COMMIT, "tree": MAIN_TREE},
        "product_acceptance": {
            "branch": "codex/product-line-acceptance-checkpoint",
            "commit": PRODUCT_COMMIT,
            "tree": PRODUCT_TREE,
            "sole_parent": MERGE_BASE,
            "historical_pis_snapshot_is_current_status": False,
        },
        "e2_preparation": {
            "branch": "codex/enterprise-e2-production-identity-prep",
            "commit": E2_COMMIT,
            "tree": E2_TREE,
            "sole_parent": MERGE_BASE,
        },
        "pis004a_disposition": {
            "branch": "codex/enterprise-e2-pis004a-review-repair",
            "commit": PIS004A_COMMIT,
            "tree": PIS004A_TREE,
            "sole_parent": PIS004A_PARENT,
        },
        "pis005a_reviewed_candidate": {
            "commit": REVIEWED_COMMIT,
            "tree": REVIEWED_TREE,
            "sole_parent": REPAIR_8_COMMIT,
            "review_findings": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "open": 0,
            },
        },
        "pis005a_disposition": {
            "branch": "codex/enterprise-e2-pis005a-review-repair-9",
            "commit": DISPOSITION_COMMIT,
            "tree": DISPOSITION_TREE,
            "raw_parents": [REVIEWED_COMMIT],
        },
        "fixture_repair": {
            "commit": F_COMMIT,
            "tree": F_TREE,
            "sole_parent": DISPOSITION_COMMIT,
            "allowed_paths": ["tests/test_pis005a_contract.py"],
        },
        "integration_merge": {
            "commit": M_COMMIT,
            "tree": M_TREE,
            "raw_parents": [F_COMMIT, PRODUCT_COMMIT],
        },
        "rejected_reconciliation_candidate": {
            "branch": REJECTED_BRANCH,
            "commit": REJECTED_COMMIT,
            "tree": REJECTED_TREE,
            "sole_parent": M_COMMIT,
            "review_status": "rejected_after_high_finding",
            "review_findings": {
                "critical": 0,
                "high": 1,
                "medium": 0,
                "low": 0,
            },
            "finding": "H-01_production_cli_mandatory_control_bypass",
        },
        "reconciliation_candidate": {
            "branch": BRANCH,
            "commit_binding": "checked_out_local_branch_tip",
            "tree_binding": "checked_out_commit_tree",
            "sole_parent": REJECTED_COMMIT,
            "repair_status": "H-01_repaired_pending_fresh_independent_review",
        },
    },
    "protected_refs": PROTECTED_REFS,
    "product_acceptance": {
        "personal_technical_preview_continuation_accepted": True,
        "enterprise_e1_bounded_pilot_continuation_accepted": True,
        "prescribed_human_uat_executed": False,
        "prescribed_human_uat_passed": False,
    },
    "authority": {
        "governed_tool_count": 24,
        "runtime_authority": "Gateway",
        "e2_status": "preparation_complete_implementation_not_authorized",
        "e2_id_005a_selected_recommendation": (
            "command_center_local_authentication_boundary_and_credential_exit"
        ),
        "e2_id_005a_implementation_authorized": False,
        "pis_collection_action_authorized": False,
        "remote_transport_allowed": False,
        "production_identity_allowed": False,
        "runtime_postgres_allowed": False,
        "release_allowed": False,
        "production_allowed": False,
        "production_promotion_allowed": False,
        "human_uat_complete": False,
    },
    "separate_release_blocker": {
        "artifact": "PIS-002/PIS-003 enterprise-route artifact validity",
        "resolved": False,
        "repaired_or_waived_by_this_checkpoint": False,
    },
}


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_record(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    if not isinstance(value, dict):
        raise ValueError("lineage reconciliation record must be an object")
    return value


def validate_record(record: dict[str, Any]) -> list[str]:
    if record != EXPECTED_RECORD:
        return ["E2 lineage reconciliation record keys or values are not exact"]
    return []


def _git(root: Path, *arguments: str) -> str:
    return pis005a_check._git(root, *arguments)  # noqa: SLF001


def _git_or_none(root: Path, *arguments: str) -> str | None:
    return pis005a_check._git_or_none(root, *arguments)  # noqa: SLF001


def _git_blob(root: Path, revision: str, relative: str) -> bytes:
    return pis005a_check._git_blob(root, revision, relative)  # noqa: SLF001


def _identity(root: Path, commit: str) -> tuple[str | None, str | None]:
    return (
        _git_or_none(root, "rev-parse", f"{commit}^{{tree}}"),
        _git_or_none(root, "show", "-s", "--format=%P", commit),
    )


def _changed_entries(root: Path, older: str, newer: str) -> dict[str, str] | None:
    output = _git_or_none(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "--find-renames",
        "-r",
        older,
        newer,
    )
    if output is None:
        return None
    entries: dict[str, str] = {}
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 2 or fields[0] not in {"A", "M", "D"}:
            return None
        status, relative = fields
        if relative in entries:
            return None
        entries[relative] = status
    return entries


def _fixed_identity_failures(root: Path) -> list[str]:
    failures: list[str] = []
    expected = {
        MAIN_COMMIT: (MAIN_TREE, "8da9ac630b191a36a2782e5febb45d739030cd48"),
        PRODUCT_COMMIT: (PRODUCT_TREE, MERGE_BASE),
        E2_COMMIT: (E2_TREE, MERGE_BASE),
        PIS004A_COMMIT: (PIS004A_TREE, PIS004A_PARENT),
        REVIEWED_COMMIT: (REVIEWED_TREE, REPAIR_8_COMMIT),
        DISPOSITION_COMMIT: (DISPOSITION_TREE, REVIEWED_COMMIT),
        F_COMMIT: (F_TREE, DISPOSITION_COMMIT),
        M_COMMIT: (M_TREE, f"{F_COMMIT} {PRODUCT_COMMIT}"),
        REJECTED_COMMIT: (REJECTED_TREE, M_COMMIT),
    }
    for commit, identity in expected.items():
        if _identity(root, commit) != identity:
            failures.append(f"fixed commit identity or raw-parent topology changed: {commit}")
    if _git_or_none(root, "merge-base", PRODUCT_COMMIT, DISPOSITION_COMMIT) != MERGE_BASE:
        failures.append("product/PIS merge base changed")
    divergence = _git_or_none(
        root,
        "rev-list",
        "--left-right",
        "--count",
        f"{DISPOSITION_COMMIT}...{PRODUCT_COMMIT}",
    )
    if divergence != "27\t1":
        failures.append("product/PIS divergence changed")
    if _changed_entries(root, DISPOSITION_COMMIT, F_COMMIT) != {
        "tests/test_pis005a_contract.py": "M"
    }:
        failures.append("fixture repair changed paths other than the approved test file")
    if _changed_entries(root, F_COMMIT, M_COMMIT) != M_FIRST_PARENT_PATHS:
        failures.append("integration merge first-parent inventory changed")
    if _changed_entries(root, M_COMMIT, REJECTED_COMMIT) != R_PATHS:
        failures.append("rejected reconciliation candidate inventory changed")
    if _changed_entries(root, REVIEWED_COMMIT, DISPOSITION_COMMIT) != {
        relative: "M" for relative in FROZEN_PIS_REVIEW_DOCS
    }:
        failures.append("PIS-005A disposition inventory changed")
    return failures


def _protected_ref_verification(root: Path) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    local_tracking_match = True
    for branch, expected in PROTECTED_REFS.items():
        local = _git_or_none(root, "rev-parse", f"refs/heads/{branch}^{{commit}}")
        tracking = _git_or_none(
            root, "rev-parse", f"refs/remotes/origin/{branch}^{{commit}}"
        )
        if local != expected or tracking != expected:
            local_tracking_match = False
            failures.append(f"protected local or tracking ref moved: {branch}")
    arguments = tuple(f"refs/heads/{branch}" for branch in PROTECTED_REFS)
    output = _git_or_none(root, "ls-remote", "--heads", "origin", *arguments)
    if output is None:
        failures.append("live protected refs could not be verified")
        return failures, {
            "status": "failed",
            "remote": "origin",
            "protected_ref_count": len(PROTECTED_REFS),
            "local_tracking_live_match": False,
        }
    observed: dict[str, str] = {}
    for line in output.splitlines():
        commit, separator, ref = line.partition("\t")
        if not separator or not ref.startswith("refs/heads/"):
            failures.append("live protected ref output is malformed")
            return failures, {
                "status": "failed",
                "remote": "origin",
                "protected_ref_count": len(PROTECTED_REFS),
                "local_tracking_live_match": False,
            }
        observed[ref.removeprefix("refs/heads/")] = commit
    live_match = observed == PROTECTED_REFS
    if not live_match:
        failures.append("one or more live protected refs moved or disappeared")
    verified = local_tracking_match and live_match
    return failures, {
        "status": "verified" if verified else "failed",
        "remote": "origin",
        "protected_ref_count": len(PROTECTED_REFS),
        "local_tracking_live_match": verified,
    }


def validate_git_bindings(root: Path) -> dict[str, Any]:
    failures = list(
        pis005a_check._git_topology_metadata_failures(root)  # noqa: SLF001
    )
    failures.extend(_fixed_identity_failures(root))
    protected_failures, live_ref_evidence = _protected_ref_verification(root)
    failures.extend(protected_failures)
    head = _git_or_none(root, "rev-parse", "HEAD^{commit}")
    tree = _git_or_none(root, "rev-parse", "HEAD^{tree}")
    parents = _git_or_none(root, "show", "-s", "--format=%P", "HEAD")
    branch = _git_or_none(root, "symbolic-ref", "--short", "HEAD")
    local = _git_or_none(root, "rev-parse", f"refs/heads/{BRANCH}^{{commit}}")
    if not head or branch != BRANCH or local != head or parents != REJECTED_COMMIT:
        failures.append("reconciliation candidate branch, identity, or sole parent is invalid")
    if head and _changed_entries(root, REJECTED_COMMIT, head) != REPAIR_PATHS:
        failures.append("reconciliation candidate path inventory is invalid")
    status = _git_or_none(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status is None or status:
        failures.append("reconciliation candidate is dirty or cleanliness is unavailable")
    if _git_or_none(root, "rev-parse", "--is-shallow-repository") != "false":
        failures.append("reconciliation candidate is shallow or unverifiable")
    return {
        "commit": head,
        "tree": tree,
        "raw_parents": parents.split() if parents else [],
        "live_ref_verification": live_ref_evidence,
        "failures": failures,
    }


def validate_frozen_artifacts(root: Path) -> list[str]:
    failures: list[str] = []
    for relative in PRODUCT_ARTIFACTS:
        try:
            if (root / relative).read_bytes() != _git_blob(root, PRODUCT_COMMIT, relative):
                failures.append(f"product checkpoint artifact drifted: {relative}")
        except OSError:
            failures.append(f"product checkpoint artifact cannot be read: {relative}")
    for relative in FROZEN_PIS_REVIEW_DOCS:
        try:
            if (root / relative).read_bytes() != _git_blob(
                root, DISPOSITION_COMMIT, relative
            ):
                failures.append(f"frozen PIS review document drifted: {relative}")
        except OSError:
            failures.append(f"frozen PIS review document cannot be read: {relative}")
    for relative in E2_FROZEN_ARTIFACTS:
        try:
            if (root / relative).read_bytes() != _git_blob(root, E2_COMMIT, relative):
                failures.append(f"frozen E2 preparation artifact drifted: {relative}")
        except OSError:
            failures.append(f"frozen E2 preparation artifact cannot be read: {relative}")
    return failures


def _load_json(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        failures.append(f"required authority source cannot be loaded: {path.name}: {exc}")
        return {}
    if not isinstance(value, dict):
        failures.append(f"required authority source is not an object: {path.name}")
        return {}
    return value


def validate_authority_ceilings(root: Path, record: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if pis005a_check._observed_tool_count(root) != 24:  # noqa: SLF001
        failures.append("governed tool count is not exactly 24")
    product = _load_json(root / product_checkpoint.RECORD_REL, failures)
    e1 = _load_json(root / "docs/codex/enterprise-e1-completion-contract.json", failures)
    e2 = _load_json(root / "docs/codex/enterprise-e2-preparation-contract.json", failures)
    pis005a_contract = Path(
        "docs/codex/production-identity-storage-pis-005a-entry-and-implementation-contract.json"
    )
    pis005a = _load_json(root / pis005a_contract, failures)
    preserved = product.get("preserved_boundaries", {})
    if not isinstance(preserved, dict) or preserved.get("runtime_authority") != "Gateway":
        failures.append("independent product source does not preserve Gateway authority")
    if preserved.get("governed_tool_count") != 24:
        failures.append("independent product source does not preserve 24 tools")
    pis_wait = e1.get("pis_wait", {})
    if not isinstance(pis_wait, dict) or any(
        pis_wait.get(key) is not False
        for key in ("external_inputs_present", "collection_action_authority")
    ):
        failures.append("PIS external-input or collection authority ceiling changed")
    e1_authority = e1.get("authority", {})
    if not isinstance(e1_authority, dict) or any(
        e1_authority.get(key) is not False
        for key in (
            "production_identity_allowed",
            "runtime_postgres_allowed",
            "production_promotion_allowed",
            "enterprise_production_ready",
            "local_v1_release_accepted",
        )
    ):
        failures.append("E1 production, release, identity, or PostgreSQL ceiling changed")
    qualification = e1.get("qualification", {})
    if not isinstance(qualification, dict) or qualification.get("human_uat_complete") is not False:
        failures.append("E1 human UAT must remain incomplete")
    e2_authority = e2.get("authority", {})
    if (
        e2.get("status") != "preparation_complete_implementation_not_authorized"
        or not isinstance(e2_authority, dict)
        or any(value is not False for value in e2_authority.values())
    ):
        failures.append("E2 preparation or authority ceiling changed")
    pis_authority = pis005a.get("authority", {})
    if not isinstance(pis_authority, dict) or any(
        pis_authority.get(key) is not False
        for key in (
            "remote_transport_allowed",
            "runtime_postgres_allowed",
            "production_identity_allowed",
            "release_allowed",
            "production_promotion_allowed",
            "human_uat_completion_allowed",
        )
    ):
        failures.append("PIS remote, production, release, or UAT ceiling changed")
    authority = record.get("authority", {})
    if not isinstance(authority, dict) or any(
        value is not False
        for key, value in authority.items()
        if key
        not in {
            "governed_tool_count",
            "runtime_authority",
            "e2_status",
            "e2_id_005a_selected_recommendation",
        }
    ):
        failures.append("reconciliation authority record contains a true authority field")
    return failures


def validate_navigation(root: Path) -> list[str]:
    failures: list[str] = []
    routed = (DOC_REL.as_posix(), RECORD_REL.as_posix())
    sources = (
        root / "README.md",
        root / "docs/codex/review-docs-index.md",
        root / "scripts/build_docs_site.py",
        root / "scripts/review_docs.py",
    )
    for source in sources:
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            failures.append(f"navigation source cannot be read: {source.name}: {exc}")
            continue
        for relative in routed:
            occurrences = (
                text.count(relative)
                if relative in text
                else text.count(Path(relative).name)
            )
            if occurrences != 1:
                failures.append(f"{source.name} does not route {relative} exactly once")
    try:
        makefile = (root / "Makefile").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        failures.append(f"Makefile cannot be read: {exc}")
    else:
        if makefile.count("e2-lineage-reconciliation-check:") != 1:
            failures.append("Makefile does not define the reconciliation target exactly once")
    return failures


def _run_command(
    command: list[str], cwd: Path, *, environment: dict[str, str] | None = None
) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=1_800,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    summary = output.splitlines()[-1] if output else "no output"
    if result.returncode != 0:
        tail = "\n".join(output.splitlines()[-40:])
        return False, tail or f"exit code {result.returncode}"
    return True, summary


@contextmanager
def _detached_worktree(root: Path, commit: str) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="ithildin-e2-lineage-") as temporary:
        checkout = Path(temporary) / "checkout"
        _git(root, "worktree", "add", "--quiet", "--detach", str(checkout), commit)
        try:
            yield checkout
        finally:
            result = subprocess.run(
                pis005a_check._git_command(  # noqa: SLF001
                    root, "worktree", "remove", "--force", str(checkout)
                ),
                cwd=root,
                env=pis005a_check._controlled_git_environment(),  # noqa: SLF001
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"temporary worktree cleanup failed: {result.stderr}")


@contextmanager
def _isolated_named_checkout(
    root: Path,
    branch: str,
    commit: str,
) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="ithildin-e2-named-") as temporary:
        checkout = Path(temporary) / "checkout"
        result = subprocess.run(
            [
                "git",
                "-c",
                f"core.hooksPath={os.devnull}",
                "clone",
                "--quiet",
                "--no-hardlinks",
                str(root),
                str(checkout),
            ],
            cwd=temporary,
            env=pis005a_check._controlled_git_environment(),  # noqa: SLF001
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"temporary clone failed: {result.stderr}")
        _git(checkout, "checkout", "--quiet", "-B", branch, commit)
        if _git(checkout, "rev-parse", f"refs/remotes/origin/{branch}^{{commit}}") != commit:
            raise RuntimeError("temporary named checkout tracking identity changed")
        yield checkout


def run_frozen_gates(root: Path) -> tuple[list[str], dict[str, str]]:
    failures: list[str] = []
    summaries: dict[str, str] = {}

    def run(
        label: str,
        command: list[str],
        cwd: Path,
        *,
        env: dict[str, str] | None = None,
    ) -> None:
        passed, summary = _run_command(command, cwd, environment=env)
        summaries[label] = summary
        if not passed:
            failures.append(f"{label} failed:\n{summary}")

    try:
        with _detached_worktree(root, PRODUCT_COMMIT) as product_root:
            run(
                "exact_product_checkpoint",
                [sys.executable, "scripts/product_line_acceptance_checkpoint.py"],
                product_root,
            )
    except RuntimeError as exc:
        label = "exact_product_checkpoint"
        summaries[label] = f"not executed: {exc}"
        failures.append(f"{label} failed:\n{exc}")

    disposition_labels = (
        "exact_pis005a_report",
        "exact_pis004a_report",
        "complete_repaired_pis_fixture_matrix",
    )
    try:
        with _detached_worktree(root, DISPOSITION_COMMIT) as disposition_root:
            run(
                "exact_pis005a_report",
                [sys.executable, "scripts/production_identity_storage_pis_005a_check.py"],
                disposition_root,
            )
            run(
                "exact_pis004a_report",
                [sys.executable, "scripts/production_identity_storage_pis_004a_check.py"],
                disposition_root,
            )
            with tempfile.TemporaryDirectory(
                prefix="ithildin-repaired-pis-tests-"
            ) as test_dir:
                test_path = Path(test_dir) / "test_pis005a_contract.py"
                test_path.write_bytes(
                    _git_blob(root, F_COMMIT, "tests/test_pis005a_contract.py")
                )
                environment = os.environ.copy()
                environment["PYTHONPATH"] = str(disposition_root)
                run(
                    "complete_repaired_pis_fixture_matrix",
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        str(test_path),
                        "--rootdir",
                        str(disposition_root),
                        "-p",
                        "no:cacheprovider",
                        "-q",
                    ],
                    disposition_root,
                    env=environment,
                )
    except (OSError, RuntimeError) as exc:
        for label in disposition_labels:
            if label not in summaries:
                summaries[label] = f"not executed: {exc}"
                failures.append(f"{label} failed:\n{exc}")

    try:
        with _isolated_named_checkout(
            root,
            "codex/enterprise-e2-production-identity-prep",
            E2_COMMIT,
        ) as e2_root:
            run(
                "exact_e2_preparation",
                [sys.executable, "scripts/enterprise_e2_preparation_check.py"],
                e2_root,
            )
    except RuntimeError as exc:
        label = "exact_e2_preparation"
        summaries[label] = f"not executed: {exc}"
        failures.append(f"{label} failed:\n{exc}")
    return failures, summaries


def _frozen_evidence_failures(summaries: dict[str, str]) -> list[str]:
    if set(summaries) != set(EXPECTED_FROZEN_GATE_LABELS):
        return ["frozen gate summary inventory is missing, partial, or extra"]
    if any(not isinstance(summary, str) or not summary.strip() for summary in summaries.values()):
        return ["frozen gate summary inventory contains an empty or invalid result"]
    return []


def _live_ref_evidence_failures(evidence: dict[str, Any]) -> list[str]:
    if evidence != EXPECTED_LIVE_REF_EVIDENCE:
        return ["live protected-ref verification evidence is missing or invalid"]
    return []


def build_authoritative_report(root: Path = ROOT) -> dict[str, Any]:
    failures: list[str] = []
    try:
        record = load_record(root / RECORD_REL)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        record = {}
        failures.append(f"lineage reconciliation record cannot be loaded: {exc}")
    failures.extend(validate_record(record))
    git_report = validate_git_bindings(root)
    failures.extend(git_report["failures"])
    failures.extend(validate_frozen_artifacts(root))
    failures.extend(validate_authority_ceilings(root, record))
    failures.extend(validate_navigation(root))
    try:
        frozen_failures, frozen_summaries = run_frozen_gates(root)
        failures.extend(frozen_failures)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        frozen_summaries = {}
        failures.append(f"mandatory frozen gates could not be executed: {exc}")
    failures.extend(_frozen_evidence_failures(frozen_summaries))
    live_ref_evidence = git_report["live_ref_verification"]
    failures.extend(_live_ref_evidence_failures(live_ref_evidence))
    authority = record.get("authority", {})
    if not isinstance(authority, dict):
        authority = {}
    return {
        "authoritative": True,
        "valid": not failures,
        "record_status": record.get("record_status"),
        "candidate_branch": BRANCH,
        "candidate_commit": git_report["commit"],
        "candidate_tree": git_report["tree"],
        "raw_parents": git_report["raw_parents"],
        "governed_tool_count": (
            authority.get("governed_tool_count")
        ),
        "runtime_authority": authority.get("runtime_authority"),
        "human_uat_complete": authority.get("human_uat_complete"),
        "release_allowed": authority.get("release_allowed"),
        "e2_id_005a_implementation_authorized": authority.get(
            "e2_id_005a_implementation_authorized"
        ),
        "live_ref_verification": live_ref_evidence,
        "frozen_gate_summaries": frozen_summaries,
        "failures": failures,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin E2 lineage reconciliation checkpoint",
        f"authoritative: {str(report['authoritative']).lower()}",
        f"valid: {str(report['valid']).lower()}",
        f"record_status: {report['record_status']}",
        f"candidate_branch: {report['candidate_branch']}",
        f"candidate_commit: {report['candidate_commit']}",
        f"candidate_tree: {report['candidate_tree']}",
        f"raw_parents: {' '.join(report['raw_parents'])}",
        f"governed_tool_count: {report['governed_tool_count']}",
        f"runtime_authority: {report['runtime_authority']}",
        f"human_uat_complete: {str(report['human_uat_complete']).lower()}",
        f"release_allowed: {str(report['release_allowed']).lower()}",
        (
            "e2_id_005a_implementation_authorized: "
            f"{str(report['e2_id_005a_implementation_authorized']).lower()}"
        ),
        (
            "live_ref_verification: "
            f"{report['live_ref_verification']['status']} "
            f"({report['live_ref_verification']['protected_ref_count']} protected refs)"
        ),
    ]
    summaries = report["frozen_gate_summaries"]
    if summaries:
        lines.append("frozen_gate_summaries:")
        lines.extend(f"- {label}: {summary}" for label, summary in summaries.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_authoritative_report(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

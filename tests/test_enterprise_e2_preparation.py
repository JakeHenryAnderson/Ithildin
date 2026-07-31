from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts import enterprise_e2_preparation_check


def _live_contract() -> dict[str, Any]:
    failures: list[str] = []
    contract = enterprise_e2_preparation_check.load_contract(
        enterprise_e2_preparation_check.ROOT
        / enterprise_e2_preparation_check.CONTRACT_REL,
        failures,
    )
    assert failures == []
    return contract


def test_live_enterprise_e2_preparation_is_valid_and_non_authorizing() -> None:
    report = enterprise_e2_preparation_check.build_report(
        enterprise_e2_preparation_check.ROOT
    )

    assert report["valid"] is True, report["failures"]
    assert report["track_id"] == "E2-PREP"
    assert report["tool_count"] == 24
    assert report["work_package_ids"] == list(
        enterprise_e2_preparation_check.WORK_PACKAGE_IDS
    )
    assert report["runtime_behavior_changes_allowed"] is False
    assert report["production_identity_allowed"] is False
    assert report["runtime_postgres_allowed"] is False
    assert report["e1_human_uat_complete"] is False
    assert report["pis_next_action"] == enterprise_e2_preparation_check.PIS_WAIT_ACTION
    assert report["next_action"] == enterprise_e2_preparation_check.NEXT_ACTION


def test_e2_contract_rejects_runtime_authority_or_pis_route_drift() -> None:
    contract = copy.deepcopy(_live_contract())
    authority = contract["authority"]
    standing = contract["standing_authority"]
    assert isinstance(authority, dict)
    assert isinstance(standing, dict)
    authority["production_identity_allowed"] = True
    standing["pis_next_action"] = "connect_to_postgres"

    failures = enterprise_e2_preparation_check.validate_contract(contract)

    assert "E2 preparation grants forbidden implementation authority" in failures
    assert "E2 preparation does not preserve current PIS authority" in failures


def test_e2_contract_rejects_scale_overclaim_or_work_package_reordering() -> None:
    contract = copy.deepcopy(_live_contract())
    scale = contract["scale_fixture"]
    identity = contract["identity_reconciliation"]
    assert isinstance(scale, dict)
    assert isinstance(identity, dict)
    scale["supported_scale_claim_allowed"] = True
    packages = identity["work_packages"]
    assert isinstance(packages, list)
    packages.reverse()

    failures = enterprise_e2_preparation_check.validate_contract(contract)

    assert "E2 scale fixture contract is not exact and bounded" in failures
    assert "E2 identity work packages are not exact and ordered" in failures


@pytest.mark.parametrize("checkout_mode", ["named", "detached", "linked"])
def test_e2_full_report_accepts_clean_exact_pending_repair9_checkout(
    tmp_path: Path,
    checkout_mode: str,
) -> None:
    repository = _initialize_e2_candidate_repository(tmp_path)
    checkout = repository
    if checkout_mode == "detached":
        _git(repository, "checkout", "-q", "--detach", "HEAD")
    elif checkout_mode == "linked":
        checkout = tmp_path / "linked-review"
        _git(repository, "worktree", "add", "-q", "--detach", str(checkout), "HEAD")

    report = enterprise_e2_preparation_check.build_report(checkout)

    assert report["valid"] is True, report["failures"]
    assert report["status"] == "preparation_complete_implementation_not_authorized"
    assert report["production_identity_allowed"] is False


def test_e2_full_report_rejects_extra_descendant_hidden_by_replace(
    tmp_path: Path,
) -> None:
    repository = _initialize_e2_candidate_repository(tmp_path)
    candidate = _git(repository, "rev-parse", "HEAD")
    _git(repository, "commit", "--allow-empty", "-q", "-m", "hidden descendant")
    extra = _git(repository, "rev-parse", "HEAD")
    _git(
        repository,
        "update-ref",
        (
            "refs/remotes/origin/"
            f"{enterprise_e2_preparation_check.PIS005A_BRANCH}"
        ),
        extra,
    )
    _git(repository, "replace", extra, candidate)

    failures = _failures(enterprise_e2_preparation_check.build_report(repository))

    assert "E2 preparation replacement-ref topology metadata is present" in failures
    assert "E2 preparation PIS-005A candidate identity or topology changed" in failures


def test_e2_full_report_rejects_unrelated_replace_ref(tmp_path: Path) -> None:
    repository = _initialize_e2_candidate_repository(tmp_path)
    first = _git(repository, "hash-object", "-w", "--stdin", stdin="first\n")
    second = _git(repository, "hash-object", "-w", "--stdin", stdin="second\n")
    _git(repository, "replace", first, second)

    failures = _failures(enterprise_e2_preparation_check.build_report(repository))

    assert "E2 preparation replacement-ref topology metadata is present" in failures


@pytest.mark.parametrize("namespaced", [False, True])
def test_e2_full_report_rejects_packed_replacement_namespaces(
    tmp_path: Path,
    namespaced: bool,
) -> None:
    repository = _initialize_e2_candidate_repository(tmp_path)
    first = _git(repository, "hash-object", "-w", "--stdin", stdin="first\n")
    second = _git(repository, "hash-object", "-w", "--stdin", stdin="second\n")
    replacement_ref = f"refs/replace/{first}"
    if namespaced:
        replacement_ref = f"refs/namespaces/hidden/{replacement_ref}"
    _git(repository, "update-ref", replacement_ref, second)
    _git(repository, "pack-refs", "--all", "--prune")

    failures = _failures(enterprise_e2_preparation_check.build_report(repository))

    assert "E2 preparation replacement-ref topology metadata is present" in failures


def test_e2_full_report_rejects_redirected_replacement_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _initialize_e2_candidate_repository(tmp_path)
    candidate = _git(repository, "rev-parse", "HEAD")
    _git(repository, "commit", "--allow-empty", "-q", "-m", "redirected descendant")
    extra = _git(repository, "rev-parse", "HEAD")
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{enterprise_e2_preparation_check.PIS005A_BRANCH}",
        extra,
    )
    replacement_base = "refs/redirected-replacements"
    _git(repository, "update-ref", f"{replacement_base}/{extra}", candidate)
    monkeypatch.setenv("GIT_REPLACE_REF_BASE", replacement_base)

    failures = _failures(enterprise_e2_preparation_check.build_report(repository))

    assert any(
        failure.startswith(
            "E2 preparation inherited Git object or topology environment is unsafe:"
        )
        for failure in failures
    )
    assert "E2 preparation PIS-005A candidate identity or topology changed" in failures


def test_e2_full_report_rejects_common_directory_graft(
    tmp_path: Path,
) -> None:
    repository = _initialize_e2_candidate_repository(tmp_path)
    checkout = tmp_path / "linked-graft-review"
    _git(repository, "worktree", "add", "-q", "--detach", str(checkout), "HEAD")
    common = Path(
        _git(
            checkout,
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        )
    )
    graft = common / "info/grafts"
    graft.parent.mkdir(parents=True, exist_ok=True)
    graft.write_text(
        f"{_git(checkout, 'rev-parse', 'HEAD')} "
        f"{enterprise_e2_preparation_check.PIS005A_REPAIR_BASE_COMMIT}\n",
        encoding="utf-8",
    )

    failures = _failures(enterprise_e2_preparation_check.build_report(checkout))

    assert "E2 preparation legacy graft topology metadata is present" in failures


@pytest.mark.parametrize(
    "environment_name",
    [
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CONFIG",
        "GIT_CONFIG_COUNT",
        "GIT_INDEX_FILE",
        "GIT_NAMESPACE",
        "GIT_SHALLOW_FILE",
    ],
)
def test_e2_full_report_rejects_and_sanitizes_inherited_git_redirects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
) -> None:
    repository = _initialize_e2_candidate_repository(tmp_path)
    expected_head = _git(repository, "rev-parse", "HEAD")
    monkeypatch.setenv(environment_name, str(tmp_path / "redirected"))

    report = enterprise_e2_preparation_check.build_report(repository)
    failures = _failures(report)

    assert (
        enterprise_e2_preparation_check._git_one(  # noqa: SLF001
            repository,
            "rev-parse",
            "HEAD",
        )
        == expected_head
    )
    assert any(
        failure.startswith(
            "E2 preparation inherited Git object or topology environment is unsafe:"
        )
        for failure in failures
    )


def test_e2_full_report_rejects_shallow_metadata(tmp_path: Path) -> None:
    repository = _initialize_e2_candidate_repository(tmp_path)
    shallow = Path(
        _git(
            repository,
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "shallow",
        )
    )
    shallow.write_text(_git(repository, "rev-parse", "HEAD") + "\n", encoding="utf-8")

    failures = _failures(enterprise_e2_preparation_check.build_report(repository))

    assert "E2 preparation shallow topology metadata is present" in failures
    assert "E2 preparation PIS-005A checkout is shallow or unverifiable" in failures


@pytest.mark.parametrize("mutation", ["branch", "tree", "ancestry"])
def test_e2_full_report_rejects_branch_tree_or_ancestry_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    repository = _initialize_e2_candidate_repository(tmp_path)
    if mutation == "branch":
        _git(repository, "checkout", "-q", "-b", "unapproved-e2-branch")
    elif mutation == "tree":
        monkeypatch.setattr(
            enterprise_e2_preparation_check,
            "PIS005A_REPAIR_BASE_TREE",
            "0" * 40,
        )
    else:
        _git(repository, "checkout", "-q", "--orphan", "unrelated-history")
        unrelated = repository / "unrelated.txt"
        unrelated.write_text("unrelated\n", encoding="utf-8")
        _git(repository, "add", unrelated.name)
        _git(repository, "commit", "-q", "-m", "unrelated source")
        unrelated_commit = _git(repository, "rev-parse", "HEAD")
        unrelated_tree = _git(repository, "rev-parse", "HEAD^{tree}")
        _git(
            repository,
            "checkout",
            "-q",
            enterprise_e2_preparation_check.PIS005A_BRANCH,
        )
        monkeypatch.setattr(
            enterprise_e2_preparation_check,
            "PIS005A_SOURCE_COMMIT",
            unrelated_commit,
        )
        monkeypatch.setattr(
            enterprise_e2_preparation_check,
            "PIS005A_SOURCE_TREE",
            unrelated_tree,
        )

    failures = _failures(enterprise_e2_preparation_check.build_report(repository))

    if mutation == "branch":
        assert "E2 preparation is not on its isolated branch" in failures
    elif mutation == "tree":
        assert "E2 preparation PIS-005A candidate identity or topology changed" in failures
    else:
        assert (
            "E2 preparation PIS-005A descendant does not preserve its exact source"
            in failures
        )


def test_e2_completed_review_does_not_become_entry_authority(
    tmp_path: Path,
) -> None:
    repository = _initialize_e2_candidate_repository(tmp_path)
    contract_path = repository / enterprise_e2_preparation_check.PIS005A_CONTRACT_REL
    contract = enterprise_e2_preparation_check._load_json(  # noqa: SLF001
        contract_path,
        [],
    )
    contract["status"] = "candidate_independent_review_complete"
    contract_path.write_text(
        json.dumps(contract, indent=2) + "\n",
        encoding="utf-8",
    )
    _git(repository, "add", contract_path.relative_to(repository).as_posix())
    _git(repository, "commit", "-q", "-m", "completed review is not E2 entry")
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{enterprise_e2_preparation_check.PIS005A_BRANCH}",
        "HEAD",
    )

    report = enterprise_e2_preparation_check.build_report(repository)

    assert report["valid"] is False
    assert (
        "E2 preparation PIS-005A checkout is not the exact pending repair-9 lifecycle"
        in _failures(report)
    )
    assert report["status"] == "preparation_complete_implementation_not_authorized"
    assert report["production_identity_allowed"] is False


def _failures(report: dict[str, Any]) -> list[str]:
    failures = report["failures"]
    assert isinstance(failures, list)
    assert all(isinstance(failure, str) for failure in failures)
    return failures


def _initialize_e2_candidate_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "e2-full-report-repository"
    git_executable = shutil.which("git", path=os.defpath)
    assert git_executable is not None
    subprocess.run(
        [
            git_executable,
            "clone",
            "--quiet",
            str(enterprise_e2_preparation_check.ROOT),
            str(repository),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    _git(repository, "config", "user.name", "E2 full report fixture")
    _git(repository, "config", "user.email", "e2-full-report@example.invalid")
    _git(
        repository,
        "checkout",
        "-q",
        "-B",
        enterprise_e2_preparation_check.PIS005A_BRANCH,
        enterprise_e2_preparation_check.PIS005A_REPAIR_BASE_COMMIT,
    )

    candidate_paths: set[str] = set()
    for arguments in (
        (
            "diff",
            "--name-only",
            f"{enterprise_e2_preparation_check.PIS005A_REPAIR_BASE_COMMIT}..HEAD",
        ),
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        candidate_paths.update(
            line
            for line in _git(
                enterprise_e2_preparation_check.ROOT,
                *arguments,
            ).splitlines()
            if line
        )
    for relative in sorted(candidate_paths):
        source = enterprise_e2_preparation_check.ROOT / relative
        destination = repository / relative
        if source.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        elif destination.exists():
            destination.unlink()

    _git(repository, "add", "-A")
    _git(repository, "commit", "-q", "-m", "PIS-005A repair-9 E2 fixture")
    candidate = _git(repository, "rev-parse", "HEAD")
    _git(
        repository,
        "update-ref",
        (
            "refs/heads/"
            f"{enterprise_e2_preparation_check.PIS005A_REPAIR_BASE_BRANCH}"
        ),
        enterprise_e2_preparation_check.PIS005A_REPAIR_BASE_COMMIT,
    )
    _git(
        repository,
        "update-ref",
        (
            "refs/remotes/origin/"
            f"{enterprise_e2_preparation_check.PIS005A_REPAIR_BASE_BRANCH}"
        ),
        enterprise_e2_preparation_check.PIS005A_REPAIR_BASE_COMMIT,
    )
    _git(
        repository,
        "update-ref",
        f"refs/remotes/origin/{enterprise_e2_preparation_check.PIS005A_BRANCH}",
        candidate,
    )
    return repository


def _git(
    root: Path,
    *arguments: str,
    stdin: str | None = None,
) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        input=stdin,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()

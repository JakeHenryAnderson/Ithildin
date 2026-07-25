from __future__ import annotations

import subprocess
from pathlib import Path

from scripts import mission_command_runner_bridge_authorization_check as authorization_check


def test_runner_bridge_authorization_is_exact_reviewed_code_only() -> None:
    report = authorization_check.build_report(Path("."))

    assert report["valid"] is True, report["failures"]
    assert report["tool_count"] == 24
    assert report["reviewed_candidate_commit"] == authorization_check.REVIEWED_COMMIT
    assert report["code_implementation_authorized"] is True
    assert report["authorized_runtime_matches_reviewed_candidate"] is True
    assert report["live_hermes_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False
    assert report["new_governed_tool"] is False
    assert report["release_allowed"] is False
    assert report["uat_complete"] is False


def test_authorization_contract_binds_exact_review_lineage_and_inventory() -> None:
    text = Path(authorization_check.AUTHORIZATION).read_text(encoding="utf-8")
    authorization = authorization_check._contract(text)  # noqa: SLF001

    assert authorization["reviewed_candidate_parent"] == authorization_check.REVIEWED_PARENT
    assert authorization["reviewed_candidate_tree"] == authorization_check.REVIEWED_TREE
    assert authorization["review_document"] == authorization_check.REVIEW_DOCUMENT
    assert authorization["review_lineage"] == authorization_check.REVIEW_LINEAGE
    assert (
        authorization["previous_reviewed_candidate_commit"]
        == authorization_check.PREVIOUS_REVIEWED_COMMIT
    )
    assert (
        authorization["previous_review_document"]
        == authorization_check.PREVIOUS_REVIEW_DOCUMENT
    )
    assert (
        authorization["previous_review_document_sha256"]
        == authorization_check.PREVIOUS_REVIEW_DOCUMENT_DIGEST
    )
    assert (
        authorization["reviewed_path_inventory"]
        == authorization_check.REVIEWED_PATH_INVENTORY
    )
    assert len(authorization["reviewed_path_inventory"]) == 11
    assert authorization["review_lineage"][-1] == {
        "stage": "producer_exact_review",
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "disposition": "GO",
    }
    assert (
        "scripts/local_v1_lv1_003_o4_producer.py"
        in authorization["allowed_runtime_paths"]
    )
    assert authorization["runtime_adapter_code_authorized"] is True
    assert authorization["runner_bridge_code_authorized"] is True
    assert authorization["exact_implementation_review_complete"] is True


def test_authorization_rejects_live_authority() -> None:
    text = Path(authorization_check.AUTHORIZATION).read_text(encoding="utf-8")
    decision = Path(authorization_check.decision_check.DECISION).read_text(
        encoding="utf-8"
    )
    authorization = authorization_check._contract(  # noqa: SLF001
        text.replace(
            '"live_hermes_execution_authorized": false',
            '"live_hermes_execution_authorized": true',
            1,
        )
    )
    failures: list[str] = []

    authorization_check._validate_contract(  # noqa: SLF001
        authorization, decision, failures
    )

    assert "runner-bridge authorization live_hermes_execution_authorized must remain false" in (
        failures
    )


def test_authorization_rejects_path_expansion() -> None:
    text = Path(authorization_check.AUTHORIZATION).read_text(encoding="utf-8")
    decision = Path(authorization_check.decision_check.DECISION).read_text(
        encoding="utf-8"
    )
    authorization = authorization_check._contract(  # noqa: SLF001
        text.replace(
            '"apps/node/src/ithildin_node/client.py"',
            '"pyproject.toml",\n    "apps/node/src/ithildin_node/client.py"',
            1,
        )
    )
    failures: list[str] = []

    authorization_check._validate_contract(  # noqa: SLF001
        authorization, decision, failures
    )

    assert any("allowed_runtime_paths" in failure for failure in failures)


def test_authorization_rejects_reviewed_inventory_substitution() -> None:
    text = Path(authorization_check.AUTHORIZATION).read_text(encoding="utf-8")
    decision = Path(authorization_check.decision_check.DECISION).read_text(
        encoding="utf-8"
    )
    authorization = authorization_check._contract(text)  # noqa: SLF001
    authorization["reviewed_path_inventory"].append("pyproject.toml")
    failures: list[str] = []

    authorization_check._validate_contract(  # noqa: SLF001
        authorization, decision, failures
    )

    assert any("reviewed_path_inventory" in failure for failure in failures)


def test_authorized_runtime_state_rejects_modified_tracked_file(
    tmp_path: Path,
) -> None:
    repo, reviewed_commit, tracked = _runtime_state_repository(tmp_path)
    tracked.write_text("modified\n", encoding="utf-8")
    failures: list[str] = []

    valid = authorization_check._validate_authorized_runtime_state(  # noqa: SLF001
        repo,
        failures,
        reviewed_commit=reviewed_commit,
    )

    assert valid is False
    assert any("worktree differs" in failure for failure in failures)


def test_authorized_runtime_state_rejects_untracked_runtime_prefix_file(
    tmp_path: Path,
) -> None:
    repo, reviewed_commit, _ = _runtime_state_repository(tmp_path)
    untracked = repo / "deploy/hermes-node-bridge/unreviewed.txt"
    untracked.parent.mkdir(parents=True, exist_ok=True)
    untracked.write_text("not reviewed\n", encoding="utf-8")
    failures: list[str] = []

    valid = authorization_check._validate_authorized_runtime_state(  # noqa: SLF001
        repo,
        failures,
        reviewed_commit=reviewed_commit,
    )

    assert valid is False
    assert any("contain untracked files" in failure for failure in failures)


def test_authorized_runtime_state_rejects_staged_runtime_change(
    tmp_path: Path,
) -> None:
    repo, reviewed_commit, tracked = _runtime_state_repository(tmp_path)
    tracked.write_text("staged modification\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "add", tracked.relative_to(repo).as_posix()],
        check=True,
        capture_output=True,
        text=True,
    )
    failures: list[str] = []

    valid = authorization_check._validate_authorized_runtime_state(  # noqa: SLF001
        repo,
        failures,
        reviewed_commit=reviewed_commit,
    )

    assert valid is False
    assert any("index differs" in failure for failure in failures)


def test_authorization_rejects_decision_substitution() -> None:
    text = Path(authorization_check.AUTHORIZATION).read_text(encoding="utf-8")
    decision = (
        Path(authorization_check.decision_check.DECISION).read_text(encoding="utf-8")
        + "\nsubstituted\n"
    )
    authorization = authorization_check._contract(text)  # noqa: SLF001
    failures: list[str] = []

    authorization_check._validate_contract(  # noqa: SLF001
        authorization, decision, failures
    )

    assert any("current runner-bridge decision" in failure for failure in failures)


def test_authorization_rejects_coupled_current_decision_and_digest_substitution() -> None:
    text = Path(authorization_check.AUTHORIZATION).read_text(encoding="utf-8")
    decision = (
        Path(authorization_check.decision_check.DECISION).read_text(encoding="utf-8")
        + "\nsubstituted\n"
    )
    substituted_digest = authorization_check._digest(decision)  # noqa: SLF001
    authorization = authorization_check._contract(text)  # noqa: SLF001
    authorization["current_decision_sha256"] = substituted_digest
    failures: list[str] = []

    authorization_check._validate_contract(  # noqa: SLF001
        authorization, decision, failures
    )

    assert any("current runner-bridge decision" in failure for failure in failures)
    assert any("current_decision_sha256" in failure for failure in failures)


def test_authorization_requires_own_make_target_definition(tmp_path: Path) -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    mutated = makefile.replace(
        "mission-command-runner-bridge-authorization-check:\n"
        "\tuv run python scripts/mission_command_runner_bridge_authorization_check.py\n",
        "renamed-runner-bridge-authorization-check:\n"
        "\tuv run python scripts/mission_command_runner_bridge_authorization_check.py\n",
        1,
    )
    root = tmp_path
    for relative in (
        "README.md",
        "scripts/build_docs_site.py",
        "scripts/review_docs.py",
        "docs/codex/review-docs-index.md",
    ):
        source = Path(relative)
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (root / "Makefile").write_text(mutated, encoding="utf-8")
    failures: list[str] = []

    authorization_check._validate_wiring(root, failures)  # noqa: SLF001

    assert any("exactly one Make target definition" in failure for failure in failures)


def _runtime_state_repository(tmp_path: Path) -> tuple[Path, str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "-C", str(repo), "init", "-q"],
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = repo / authorization_check.ALLOWED_RUNTIME_PATHS[0]
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("reviewed\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "add", tracked.relative_to(repo).as_posix()],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Ithildin Test",
            "-c",
            "user.email=ithildin-test@example.invalid",
            "commit",
            "-q",
            "-m",
            "reviewed runtime fixture",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    reviewed_commit = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return repo, reviewed_commit, tracked

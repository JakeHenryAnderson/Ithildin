from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import local_v1_lv1_003_o4_execution_authorization_check as gate

ROOT = Path(".")


def _contract() -> dict[str, object]:
    document = json.loads(gate.CONTRACT.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _run_git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_blob_digest(repo: Path, commit: str, path: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"],
        check=True,
        capture_output=True,
    )
    return "sha256:" + hashlib.sha256(result.stdout).hexdigest()


def _attempt_010_control_child_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "candidate"
    subprocess.run(
        ["git", "clone", "-q", str(Path.cwd()), str(repo)],
        check=True,
    )
    _run_git(repo, "checkout", "--detach", gate.ATTEMPT_010_CANDIDATE_COMMIT)
    for relative in gate.ATTEMPT_010_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_010_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 010 closure child",
    )
    return (
        repo,
        _run_git(repo, "rev-parse", "HEAD"),
        _run_git(repo, "show", "-s", "--format=%T", "HEAD"),
    )


def _attempt_011_closure_child_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-011-closure"
    subprocess.run(
        ["git", "clone", "-q", str(Path.cwd()), str(repo)],
        check=True,
    )
    _run_git(repo, "checkout", "--detach", gate.ATTEMPT_011_CANDIDATE_COMMIT)
    for relative in gate.ATTEMPT_011_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_011_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 011 closure child",
    )
    return (
        repo,
        _run_git(repo, "rev-parse", "HEAD"),
        _run_git(repo, "show", "-s", "--format=%T", "HEAD"),
    )


def _attempt_012_candidate_repository(
    tmp_path: Path,
    *,
    tag_candidate: bool = True,
) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-012-candidate"
    subprocess.run(
        ["git", "clone", "-q", str(Path.cwd()), str(repo)],
        check=True,
    )
    _run_git(repo, "checkout", "--detach", gate.ATTEMPT_012_CANDIDATE_COMMIT)
    for relative in gate.ATTEMPT_012_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_012_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 012 closure child",
    )
    commit = _run_git(repo, "rev-parse", "HEAD")
    tree = _run_git(repo, "show", "-s", "--format=%T", "HEAD")
    if not tag_candidate:
        _run_git(repo, "tag", "-d", gate.ATTEMPT_012_REVIEW_TAG)
    return repo, commit, tree


def _attempt_013_candidate_repository(
    tmp_path: Path,
    *,
    tag_candidate: bool = True,
) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-013-candidate"
    subprocess.run(
        ["git", "clone", "-q", str(Path.cwd()), str(repo)],
        check=True,
    )
    _run_git(repo, "checkout", "--detach", gate.ATTEMPT_013_PARENT_COMMIT)
    for relative in gate.ATTEMPT_013_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_013_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 013 authorization candidate",
    )
    commit = _run_git(repo, "rev-parse", "HEAD")
    tree = _run_git(repo, "show", "-s", "--format=%T", "HEAD")
    inherited_tag = _run_git(repo, "tag", "--list", gate.ATTEMPT_013_REVIEW_TAG)
    if inherited_tag:
        _run_git(repo, "tag", "-d", gate.ATTEMPT_013_REVIEW_TAG)
    if tag_candidate:
        _run_git(
            repo,
            "-c",
            "user.name=Ithildin Test",
            "-c",
            "user.email=ithildin-test@example.invalid",
            "tag",
            "-a",
            gate.ATTEMPT_013_REVIEW_TAG,
            "-m",
            "test: exact reviewed Attempt 013 candidate",
            commit,
        )
    return repo, commit, tree


def _attempt_013_closure_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-013-closure"
    subprocess.run(
        ["git", "clone", "-q", str(Path.cwd()), str(repo)],
        check=True,
    )
    _run_git(repo, "checkout", "--detach", gate.ATTEMPT_013_CANDIDATE_COMMIT)
    for relative in gate.ATTEMPT_013_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_013_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 013 closure child",
    )
    return (
        repo,
        _run_git(repo, "rev-parse", "HEAD"),
        _run_git(repo, "show", "-s", "--format=%T", "HEAD"),
    )


def _attempt_014_candidate_repository(
    tmp_path: Path,
    *,
    tag_candidate: bool,
) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-014-candidate"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(
        repo,
        "checkout",
        "--detach",
        gate.TERMINAL_HEALTH_PHASE_PROJECTION_REVIEW_RECORD_COMMIT,
    )
    for relative in gate.ATTEMPT_014_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_014_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 014 authorization candidate",
    )
    commit = _run_git(repo, "rev-parse", "HEAD")
    tree = _run_git(repo, "show", "-s", "--format=%T", "HEAD")
    inherited_tag = _run_git(repo, "tag", "--list", gate.ATTEMPT_014_REVIEW_TAG)
    if inherited_tag:
        _run_git(repo, "tag", "-d", gate.ATTEMPT_014_REVIEW_TAG)
    if tag_candidate:
        _run_git(
            repo,
            "-c",
            "user.name=Ithildin Test",
            "-c",
            "user.email=ithildin-test@example.invalid",
            "tag",
            "-a",
            gate.ATTEMPT_014_REVIEW_TAG,
            "-m",
            "test: exact reviewed Attempt 014 candidate",
            commit,
        )
    return repo, commit, tree


def _attempt_014_closure_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-014-closure"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(repo, "checkout", "--detach", gate.ATTEMPT_014_CANDIDATE_COMMIT)
    for relative in gate.ATTEMPT_014_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_014_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 014 closure child",
    )
    return (
        repo,
        _run_git(repo, "rev-parse", "HEAD"),
        _run_git(repo, "show", "-s", "--format=%T", "HEAD"),
    )


def _attempt_015_candidate_repository(
    tmp_path: Path,
    *,
    tag_candidate: bool,
) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-015-candidate"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(
        repo,
        "checkout",
        "--detach",
        gate.SOCKET_PARENT_MODE_REVIEW_RECORD_COMMIT,
    )
    for relative in gate.ATTEMPT_015_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_015_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 015 authorization candidate",
    )
    commit = _run_git(repo, "rev-parse", "HEAD")
    tree = _run_git(repo, "show", "-s", "--format=%T", "HEAD")
    inherited_tag = _run_git(repo, "tag", "--list", gate.ATTEMPT_015_REVIEW_TAG)
    if inherited_tag:
        _run_git(repo, "tag", "-d", gate.ATTEMPT_015_REVIEW_TAG)
    if tag_candidate:
        _run_git(
            repo,
            "-c",
            "user.name=Ithildin Test",
            "-c",
            "user.email=ithildin-test@example.invalid",
            "tag",
            "-a",
            gate.ATTEMPT_015_REVIEW_TAG,
            "-m",
            "test: exact reviewed Attempt 015 candidate",
            commit,
        )
    return repo, commit, tree


def _attempt_015_closure_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-015-closure"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(repo, "checkout", "--detach", gate.ATTEMPT_015_CANDIDATE_COMMIT)
    for relative in gate.ATTEMPT_015_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_015_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 015 consumed closure",
    )
    return (
        repo,
        _run_git(repo, "rev-parse", "HEAD"),
        _run_git(repo, "show", "-s", "--format=%T", "HEAD"),
    )


def _attempt_016_closure_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-016-closure"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(repo, "checkout", "--detach", gate.ATTEMPT_016_CANDIDATE_COMMIT)
    for relative in gate.ATTEMPT_016_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_016_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 016 consumed closure",
    )
    return (
        repo,
        _run_git(repo, "rev-parse", "HEAD"),
        _run_git(repo, "show", "-s", "--format=%T", "HEAD"),
    )


def _attempt_017_candidate_repository(
    tmp_path: Path,
    *,
    tag_candidate: bool,
) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-017-candidate"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(
        repo,
        "checkout",
        "--detach",
        gate.MISSION_CONVERGENCE_REVIEW_RECORD_COMMIT,
    )
    for relative in gate.ATTEMPT_017_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_017_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 017 authorization candidate",
    )
    commit = _run_git(repo, "rev-parse", "HEAD")
    tree = _run_git(repo, "show", "-s", "--format=%T", "HEAD")
    inherited_tag = _run_git(repo, "tag", "--list", gate.ATTEMPT_017_REVIEW_TAG)
    if inherited_tag:
        _run_git(repo, "tag", "-d", gate.ATTEMPT_017_REVIEW_TAG)
    if tag_candidate:
        _run_git(
            repo,
            "-c",
            "user.name=Ithildin Test",
            "-c",
            "user.email=ithildin-test@example.invalid",
            "tag",
            "-a",
            gate.ATTEMPT_017_REVIEW_TAG,
            "-m",
            "test: exact reviewed Attempt 017 candidate",
            commit,
        )
    return repo, commit, tree


def _attempt_017_closure_repair_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-017-closure-repair"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(repo, "checkout", "--detach", gate.ATTEMPT_017_CLOSURE_COMMIT)
    for relative in gate.ATTEMPT_017_CLOSURE_REPAIR_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(
        repo,
        "add",
        "--",
        *gate.ATTEMPT_017_CLOSURE_REPAIR_CONTROL_PATH_ALLOWLIST,
    )
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 017 closure repair",
    )
    return (
        repo,
        _run_git(repo, "rev-parse", "HEAD"),
        _run_git(repo, "show", "-s", "--format=%T", "HEAD"),
    )


def _attempt_018_candidate_repository(
    tmp_path: Path,
    *,
    tag_candidate: bool,
) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-018-candidate"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(
        repo,
        "checkout",
        "--detach",
        gate.MISSION_LIVENESS_TERMINAL_REASON_REVIEW_RECORD_COMMIT,
    )
    for relative in gate.ATTEMPT_018_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_018_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 018 authorization candidate",
    )
    commit = _run_git(repo, "rev-parse", "HEAD")
    tree = _run_git(repo, "show", "-s", "--format=%T", "HEAD")
    inherited_tag = _run_git(repo, "tag", "--list", gate.ATTEMPT_018_REVIEW_TAG)
    if inherited_tag:
        _run_git(repo, "tag", "-d", gate.ATTEMPT_018_REVIEW_TAG)
    if tag_candidate:
        _run_git(
            repo,
            "-c",
            "user.name=Ithildin Test",
            "-c",
            "user.email=ithildin-test@example.invalid",
            "tag",
            "-a",
            gate.ATTEMPT_018_REVIEW_TAG,
            "-m",
            "test: exact reviewed Attempt 018 candidate",
            commit,
        )
    return repo, commit, tree


def _attempt_018_closure_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-018-closure"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(repo, "checkout", "--detach", gate.ATTEMPT_018_CANDIDATE_COMMIT)
    for relative in gate.ATTEMPT_018_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_018_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 018 consumed closure",
    )
    return (
        repo,
        _run_git(repo, "rev-parse", "HEAD"),
        _run_git(repo, "show", "-s", "--format=%T", "HEAD"),
    )


def _attempt_019_candidate_repository(
    tmp_path: Path,
    *,
    tag_candidate: bool,
) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-019-candidate"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(repo, "checkout", "--detach", gate.CANDIDATE_PARENT_COMMIT)
    for relative in gate.ATTEMPT_019_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_019_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 019 authorization candidate",
    )
    commit = _run_git(repo, "rev-parse", "HEAD")
    tree = _run_git(repo, "show", "-s", "--format=%T", "HEAD")
    inherited_tag = _run_git(repo, "tag", "--list", gate.ATTEMPT_019_REVIEW_TAG)
    if inherited_tag:
        _run_git(repo, "tag", "-d", gate.ATTEMPT_019_REVIEW_TAG)
    if tag_candidate:
        _run_git(
            repo,
            "-c",
            "user.name=Ithildin Test",
            "-c",
            "user.email=ithildin-test@example.invalid",
            "tag",
            "-a",
            gate.ATTEMPT_019_REVIEW_TAG,
            "-m",
            "test: exact reviewed Attempt 019 candidate",
            commit,
        )
    return repo, commit, tree


def _attempt_019_closure_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-019-closure"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(repo, "checkout", "--detach", gate.ATTEMPT_019_CANDIDATE_COMMIT)
    for relative in gate.ATTEMPT_019_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_019_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 019 consumed closure",
    )
    return (
        repo,
        _run_git(repo, "rev-parse", "HEAD"),
        _run_git(repo, "show", "-s", "--format=%T", "HEAD"),
    )


def _attempt_020_candidate_repository(
    tmp_path: Path,
    *,
    tag_candidate: bool,
) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-020-candidate"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(repo, "checkout", "--detach", gate.CANDIDATE_PARENT_COMMIT)
    for relative in gate.ATTEMPT_020_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_020_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 020 authorization candidate",
    )
    commit = _run_git(repo, "rev-parse", "HEAD")
    tree = _run_git(repo, "show", "-s", "--format=%T", "HEAD")
    inherited_tag = _run_git(repo, "tag", "--list", gate.ATTEMPT_020_REVIEW_TAG)
    if inherited_tag:
        _run_git(repo, "tag", "-d", gate.ATTEMPT_020_REVIEW_TAG)
    if tag_candidate:
        _run_git(
            repo,
            "-c",
            "user.name=Ithildin Test",
            "-c",
            "user.email=ithildin-test@example.invalid",
            "tag",
            "-a",
            gate.ATTEMPT_020_REVIEW_TAG,
            "-m",
            "test: exact reviewed Attempt 020 candidate",
            commit,
        )
    return repo, commit, tree


def _attempt_020_closure_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-020-closure"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(repo, "checkout", "--detach", gate.ATTEMPT_020_CANDIDATE_COMMIT)
    for relative in gate.ATTEMPT_020_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_020_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 020 consumed closure",
    )
    return (
        repo,
        _run_git(repo, "rev-parse", "HEAD"),
        _run_git(repo, "show", "-s", "--format=%T", "HEAD"),
    )


def _attempt_021_closure_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "attempt-021-closure"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(repo, "checkout", "--detach", gate.CANDIDATE_PARENT_COMMIT)
    for relative in gate.ATTEMPT_021_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_021_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 021 consumed-success closure",
    )
    commit = _run_git(repo, "rev-parse", "HEAD")
    tree = _run_git(repo, "show", "-s", "--format=%T", "HEAD")
    return repo, commit, tree


def _skip_private_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "_validate_attempt_010_receipts", lambda *_: None)
    monkeypatch.setattr(gate, "_validate_attempt_011_receipts", lambda *_: None)
    monkeypatch.setattr(gate, "_validate_attempt_012_receipts", lambda *_: None)
    monkeypatch.setattr(gate, "_validate_attempt_013_receipts", lambda *_: None)
    monkeypatch.setattr(gate, "_validate_attempt_014_receipts", lambda *_: None)
    monkeypatch.setattr(gate, "_validate_attempt_015_receipts", lambda *_: None)
    monkeypatch.setattr(gate, "_validate_attempt_016_receipts", lambda *_: None)
    monkeypatch.setattr(gate, "_validate_attempt_017_receipts", lambda *_: None)
    monkeypatch.setattr(gate, "_validate_attempt_018_receipts", lambda *_: None)
    monkeypatch.setattr(gate, "_validate_attempt_019_receipts", lambda *_: None)
    monkeypatch.setattr(gate, "_validate_attempt_020_receipts", lambda *_: None)
    monkeypatch.setattr(gate, "_validate_attempt_021_receipts", lambda *_: None)
    monkeypatch.setattr(gate, "_validate_retained_attempt_evidence", lambda *_: None)


def _attempt_010_child_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo, commit, tree = _attempt_010_control_child_repository(tmp_path)
    shutil.copytree(
        Path.cwd() / gate.ATTEMPT_002_RECEIPT_BASE,
        repo / gate.ATTEMPT_002_RECEIPT_BASE,
        copy_function=shutil.copy2,
    )
    runtime_base = repo / gate.ATTEMPT_002_RUNTIME_BASE
    runtime_base.mkdir(parents=True, mode=0o700)
    runtime_base.chmod(0o700)
    (runtime_base / gate.ATTEMPT_008_RUN_ID).mkdir(mode=0o700)
    shutil.copy2(
        Path.cwd() / gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT,
        repo / gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT,
    )
    return (
        repo,
        commit,
        tree,
    )


_attempt_009_closure_child_repository = _attempt_010_child_repository


def _synthetic_attempt_010_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path, Path]:
    receipt_base = Path("receipts")
    receipt_root = receipt_base / "attempt-010"
    runtime_base = Path("runtime")
    runtime_root = runtime_base / "attempt-010"
    report_root = Path("reports") / "attempt-010"
    diagnostic_bytes = b"x" * gate.ATTEMPT_010_DIAGNOSTIC_SIZE
    absolute_receipt_root = tmp_path / receipt_root
    absolute_receipt_root.mkdir(parents=True)
    (tmp_path / receipt_base).chmod(0o700)
    absolute_receipt_root.chmod(0o700)
    (tmp_path / runtime_base).mkdir(mode=0o700)
    candidate = absolute_receipt_root / "candidate"
    candidate.mkdir(mode=0o500)
    manifest = absolute_receipt_root / "candidate-manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    manifest.chmod(0o600)
    diagnostic = absolute_receipt_root / "diagnostic.json"
    disposition = absolute_receipt_root / "disposition.json"
    diagnostic.write_bytes(diagnostic_bytes)
    disposition.write_bytes(gate.ATTEMPT_010_DISPOSITION_BYTES)
    diagnostic.chmod(0o600)
    disposition.chmod(0o600)
    monkeypatch.setattr(gate, "ATTEMPT_002_RECEIPT_BASE", receipt_base)
    monkeypatch.setattr(gate, "ATTEMPT_010_RECEIPT_ROOT", receipt_root)
    monkeypatch.setattr(gate, "ATTEMPT_002_RUNTIME_BASE", runtime_base)
    monkeypatch.setattr(gate, "ATTEMPT_010_RUNTIME_ROOT", runtime_root)
    monkeypatch.setattr(gate, "ATTEMPT_010_REPORT_ROOT", report_root)
    monkeypatch.setattr(
        gate,
        "ATTEMPT_010_DIAGNOSTIC_RECEIPT_DIGEST",
        "sha256:" + hashlib.sha256(diagnostic_bytes).hexdigest(),
    )
    return tmp_path, diagnostic, disposition, absolute_receipt_root


def _synthetic_attempt_011_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path, Path]:
    receipt_base = Path("receipts")
    receipt_root = receipt_base / "attempt-011"
    runtime_base = Path("runtime")
    runtime_root = runtime_base / "attempt-011"
    report_base = Path("reports")
    report_root = report_base / "attempt-011"
    diagnostic_bytes = b"x" * gate.ATTEMPT_011_DIAGNOSTIC_SIZE
    absolute_receipt_root = tmp_path / receipt_root
    absolute_receipt_root.mkdir(parents=True)
    (tmp_path / receipt_base).chmod(0o700)
    absolute_receipt_root.chmod(0o700)
    (tmp_path / runtime_base).mkdir(mode=0o700)
    candidate = absolute_receipt_root / "candidate"
    candidate.mkdir(mode=0o500)
    manifest = absolute_receipt_root / "candidate-manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    manifest.chmod(0o600)
    diagnostic = absolute_receipt_root / "diagnostic.json"
    disposition = absolute_receipt_root / "disposition.json"
    diagnostic.write_bytes(diagnostic_bytes)
    disposition.write_bytes(gate.ATTEMPT_011_DISPOSITION_BYTES)
    diagnostic.chmod(0o600)
    disposition.chmod(0o600)
    monkeypatch.setattr(gate, "ATTEMPT_002_RECEIPT_BASE", receipt_base)
    monkeypatch.setattr(gate, "ATTEMPT_011_RECEIPT_ROOT", receipt_root)
    monkeypatch.setattr(gate, "ATTEMPT_002_RUNTIME_BASE", runtime_base)
    monkeypatch.setattr(gate, "ATTEMPT_011_RUNTIME_ROOT", runtime_root)
    monkeypatch.setattr(gate, "ATTEMPT_002_REPORT_BASE", report_base)
    monkeypatch.setattr(gate, "ATTEMPT_011_REPORT_ROOT", report_root)
    monkeypatch.setattr(
        gate,
        "ATTEMPT_011_DIAGNOSTIC_RECEIPT_DIGEST",
        "sha256:" + hashlib.sha256(diagnostic_bytes).hexdigest(),
    )
    return tmp_path, diagnostic, disposition, absolute_receipt_root


def _synthetic_attempt_012_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path, Path, str, str]:
    receipt_base = Path("receipts")
    runtime_base = Path("runtime")
    report_base = Path("reports")
    run_name = "20260726T120000Z-012abcde"
    project_name = "ithildin-local-v1-o4-012abcde"
    receipt_root = tmp_path / receipt_base / run_name
    receipt_root.mkdir(parents=True)
    (tmp_path / receipt_base).chmod(0o700)
    receipt_root.chmod(0o700)
    (tmp_path / runtime_base).mkdir(mode=0o700)
    candidate = receipt_root / "candidate"
    candidate.mkdir(mode=0o500)
    manifest = receipt_root / "candidate-manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    manifest.chmod(0o600)
    diagnostic_document = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_producer_failure_diagnostic",
        "outward_failure_code": "fixed_node_start_failed",
        "primary_failure_code": "fixed_node_start_failed",
        "cleanup_failure_codes": [],
        "recovery_required": False,
        "highest_completed_stage": 11,
        "base_build_completed": True,
        "bridge_build_completed": True,
        "bound_inspected_image_identities": [
            {
                "reference": f"private-reference-{index}",
                "image_id": f"private-image-{index}",
                "project": project_name,
                "service": f"private-service-{index}",
                "compose_version": "private-version",
                "platform": "private-platform",
                "ordered_layer_digests": [f"private-layer-{index}"],
            }
            for index in range(4)
        ],
        "fixed_node_start_diagnostic": {
            "collection_status": "complete",
            "collection_reason_code": "fixed_node_start_state_collected",
            "classification": "fixed_node_exited_observation_noncanonical",
            "container_presence": "present",
            "container_lifecycle_state": "exited",
            "container_running_state": "not_running",
            "container_exit_class": "nonzero",
            "container_health_state": "unhealthy",
            "container_failure_signal": "none",
            "observation_semantics": "sequential_container_then_mission",
            "mission_lifecycle_state": "claimed",
            "delivery_state": "claim_delivered",
            "evidence_state": "complete",
        },
    }
    diagnostic_bytes = (
        json.dumps(diagnostic_document, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    diagnostic = receipt_root / "diagnostic.json"
    diagnostic.write_bytes(diagnostic_bytes)
    diagnostic.chmod(0o600)
    disposition = receipt_root / "disposition.json"
    disposition.write_bytes(gate.ATTEMPT_012_DISPOSITION_BYTES)
    disposition.chmod(0o600)
    monkeypatch.setattr(gate, "ATTEMPT_002_RECEIPT_BASE", receipt_base)
    monkeypatch.setattr(gate, "ATTEMPT_002_RUNTIME_BASE", runtime_base)
    monkeypatch.setattr(gate, "ATTEMPT_002_REPORT_BASE", report_base)
    monkeypatch.setattr(
        gate,
        "ATTEMPT_012_RUN_IDENTITY_DIGEST",
        gate._domain_identity_digest(  # noqa: SLF001
            gate.ATTEMPT_012_RUN_DIGEST_PREFIX,
            run_name,
        ),
    )
    monkeypatch.setattr(
        gate,
        "ATTEMPT_012_PROJECT_IDENTITY_DIGEST",
        gate._domain_identity_digest(  # noqa: SLF001
            gate.ATTEMPT_012_PROJECT_DIGEST_PREFIX,
            project_name,
        ),
    )
    monkeypatch.setattr(gate, "ATTEMPT_012_DIAGNOSTIC_SIZE", len(diagnostic_bytes))
    monkeypatch.setattr(
        gate,
        "ATTEMPT_012_DIAGNOSTIC_RECEIPT_DIGEST",
        "sha256:" + hashlib.sha256(diagnostic_bytes).hexdigest(),
    )
    return tmp_path, diagnostic, disposition, receipt_root, run_name, project_name


def _synthetic_attempt_013_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path, Path, str, str]:
    receipt_base = Path("receipts")
    runtime_base = Path("runtime")
    report_base = Path("reports")
    run_name = "20260726T130000Z-013abcde"
    project_name = "ithildin-local-v1-o4-013abcde"
    receipt_root = tmp_path / receipt_base / run_name
    receipt_root.mkdir(parents=True)
    (tmp_path / receipt_base).chmod(0o700)
    receipt_root.chmod(0o700)
    (tmp_path / runtime_base).mkdir(mode=0o700)
    candidate = receipt_root / "candidate"
    candidate.mkdir(mode=0o500)
    manifest = receipt_root / "candidate-manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    manifest.chmod(0o600)
    diagnostic_document = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_producer_failure_diagnostic",
        "outward_failure_code": "fixed_node_start_failed",
        "primary_failure_code": "fixed_node_start_failed",
        "cleanup_failure_codes": [],
        "recovery_required": False,
        "highest_completed_stage": 11,
        "base_build_completed": True,
        "bridge_build_completed": True,
        "bound_inspected_image_identities": [
            {
                "reference": f"private-reference-{index}",
                "image_id": f"private-image-{index}",
                "project": project_name,
                "service": f"private-service-{index}",
                "compose_version": "private-version",
                "platform": "private-platform",
                "ordered_layer_digests": [f"private-layer-{index}"],
            }
            for index in range(4)
        ],
        "fixed_node_start_diagnostic": {
            "collection_status": "complete",
            "collection_reason_code": "fixed_node_start_state_collected",
            "classification": "fixed_node_exited_observation_noncanonical",
            "container_presence": "present",
            "container_lifecycle_state": "exited",
            "container_running_state": "not_running",
            "container_exit_class": "nonzero",
            "container_health_state": "unhealthy",
            "container_failure_signal": "none",
            "observation_semantics": "sequential_container_then_mission",
            "mission_lifecycle_state": "claimed",
            "delivery_state": "claim_delivered",
            "evidence_state": "complete",
            "fixed_bridge_last_entered_phase": "not_reported",
        },
    }
    diagnostic_bytes = (
        json.dumps(diagnostic_document, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    diagnostic = receipt_root / "diagnostic.json"
    diagnostic.write_bytes(diagnostic_bytes)
    diagnostic.chmod(0o600)
    disposition = receipt_root / "disposition.json"
    disposition.write_bytes(gate.ATTEMPT_013_DISPOSITION_BYTES)
    disposition.chmod(0o600)
    monkeypatch.setattr(gate, "ATTEMPT_002_RECEIPT_BASE", receipt_base)
    monkeypatch.setattr(gate, "ATTEMPT_002_RUNTIME_BASE", runtime_base)
    monkeypatch.setattr(gate, "ATTEMPT_002_REPORT_BASE", report_base)
    monkeypatch.setattr(
        gate,
        "ATTEMPT_013_RUN_IDENTITY_DIGEST",
        gate._domain_identity_digest(  # noqa: SLF001
            gate.ATTEMPT_013_RUN_DIGEST_PREFIX,
            run_name,
        ),
    )
    monkeypatch.setattr(
        gate,
        "ATTEMPT_013_PROJECT_IDENTITY_DIGEST",
        gate._domain_identity_digest(  # noqa: SLF001
            gate.ATTEMPT_013_PROJECT_DIGEST_PREFIX,
            project_name,
        ),
    )
    monkeypatch.setattr(gate, "ATTEMPT_013_DIAGNOSTIC_SIZE", len(diagnostic_bytes))
    monkeypatch.setattr(
        gate,
        "ATTEMPT_013_DIAGNOSTIC_RECEIPT_DIGEST",
        "sha256:" + hashlib.sha256(diagnostic_bytes).hexdigest(),
    )
    return tmp_path, diagnostic, disposition, receipt_root, run_name, project_name


def _synthetic_attempt_017_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, str, str]:
    receipt_base = Path("receipts")
    runtime_base = Path("runtime")
    report_base = Path("reports")
    run_name = "20260726T170000Z-017abcde"
    project_name = "ithildin-local-v1-o4-017abcde"
    receipt_root = tmp_path / receipt_base / run_name
    receipt_root.mkdir(parents=True)
    (tmp_path / receipt_base).chmod(0o700)
    receipt_root.chmod(0o700)
    (tmp_path / runtime_base).mkdir(mode=0o700)
    candidate = receipt_root / "candidate"
    candidate.mkdir(mode=0o700)
    fixture_bytes = b"fixture-only-candidate\n"
    fixture = candidate / "fixture.txt"
    fixture.write_bytes(fixture_bytes)
    fixture.chmod(0o400)
    candidate.chmod(0o500)
    fixture_digest = "sha256:" + hashlib.sha256(fixture_bytes).hexdigest()
    manifest_document = {
        "candidate_commit": gate.ATTEMPT_017_CANDIDATE_COMMIT,
        "candidate_tree": gate.ATTEMPT_017_CANDIDATE_TREE,
        "files": {
            "fixture.txt": {
                "mode": 0o400,
                "sha256": fixture_digest,
            }
        },
    }
    manifest_bytes = (
        json.dumps(manifest_document, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    manifest = receipt_root / "candidate-manifest.json"
    manifest.write_bytes(manifest_bytes)
    manifest.chmod(0o600)
    diagnostic_document = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_producer_failure_diagnostic",
        "outward_failure_code": "gateway_mission_projection_invalid",
        "primary_failure_code": "gateway_mission_projection_invalid",
        "cleanup_failure_codes": [],
        "recovery_required": False,
        "highest_completed_stage": 13,
        "base_build_completed": True,
        "bridge_build_completed": True,
        "bound_inspected_image_identities": [
            {
                "reference": f"private-reference-{index}",
                "image_id": f"private-image-{index}",
                "project": project_name,
                "service": f"private-service-{index}",
                "compose_version": "private-version",
                "platform": "private-platform",
                "ordered_layer_digests": [f"private-layer-{index}"],
            }
            for index in range(4)
        ],
        "gateway_mission_projection_diagnostic": {
            "collection_status": "complete",
            "collection_reason_code": "gateway_mission_projection_state_collected",
            "mission_identity_binding": "matched",
            "mission_lifecycle_state": "runner_reported_running",
            "target_node_identity_binding": "matched",
            "delivery_projection_state": "present_object",
            "governed_agent_runs_projection_state": "present_object",
        },
        "node_receipt_projection_diagnostic": {
            "collection_status": "complete",
            "collection_reason_code": "node_receipt_projection_state_collected",
            "receipt_shape_state": "exact",
            "mission_identity_binding": "matched",
            "claim_identity_state": "valid_format",
            "envelope_identity_state": "valid_digest",
            "handoff_nonce_digest_state": "valid_digest",
            "next_operation_state": "completion_pending",
            "last_closed_status": "failed_closed",
        },
    }
    diagnostic_bytes = (
        json.dumps(diagnostic_document, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    diagnostic = receipt_root / "diagnostic.json"
    diagnostic.write_bytes(diagnostic_bytes)
    diagnostic.chmod(0o600)
    disposition = receipt_root / "disposition.json"
    disposition.write_bytes(gate.ATTEMPT_017_DISPOSITION_BYTES)
    disposition.chmod(0o600)
    monkeypatch.setattr(gate, "ATTEMPT_002_RECEIPT_BASE", receipt_base)
    monkeypatch.setattr(gate, "ATTEMPT_002_RUNTIME_BASE", runtime_base)
    monkeypatch.setattr(gate, "ATTEMPT_002_REPORT_BASE", report_base)
    monkeypatch.setattr(
        gate,
        "ATTEMPT_017_RUN_IDENTITY_DIGEST",
        gate._domain_identity_digest(gate.ATTEMPT_017_RUN_DIGEST_PREFIX, run_name),  # noqa: SLF001
    )
    monkeypatch.setattr(
        gate,
        "ATTEMPT_017_PROJECT_IDENTITY_DIGEST",
        gate._domain_identity_digest(  # noqa: SLF001
            gate.ATTEMPT_017_PROJECT_DIGEST_PREFIX,
            project_name,
        ),
    )
    monkeypatch.setattr(gate, "ATTEMPT_017_MANIFEST_SIZE", len(manifest_bytes))
    monkeypatch.setattr(
        gate,
        "ATTEMPT_017_MANIFEST_RECEIPT_DIGEST",
        "sha256:" + hashlib.sha256(manifest_bytes).hexdigest(),
    )
    monkeypatch.setattr(gate, "ATTEMPT_017_DIAGNOSTIC_SIZE", len(diagnostic_bytes))
    monkeypatch.setattr(
        gate,
        "ATTEMPT_017_DIAGNOSTIC_RECEIPT_DIGEST",
        "sha256:" + hashlib.sha256(diagnostic_bytes).hexdigest(),
    )
    monkeypatch.setattr(gate, "ATTEMPT_017_SNAPSHOT_FILE_COUNT", 1)
    monkeypatch.setattr(
        gate,
        "_candidate_snapshot_from_git",
        lambda *_args, **_kwargs: {
            "fixture.txt": (0o400, fixture_digest, fixture_bytes)
        },
    )
    return tmp_path, diagnostic, run_name, project_name


def test_attempt_010_exact_closure_child_is_clean_parent_bound_and_runtime_equal(
    tmp_path: Path,
) -> None:
    repo, commit, tree = _attempt_010_control_child_repository(tmp_path)
    failures: list[str] = []

    result = gate._validate_execution_checkout(  # noqa: SLF001
        repo,
        failures,
        candidate_parent_commit=gate.ATTEMPT_010_CANDIDATE_COMMIT,
        candidate_parent_tree=gate.ATTEMPT_010_CANDIDATE_TREE,
        reviewed_commit=gate.ATTEMPT_010_CANDIDATE_COMMIT,
        control_paths=gate.ATTEMPT_010_CLOSURE_CONTROL_PATH_ALLOWLIST,
    )

    assert failures == []
    assert result == (commit, tree)


def test_attempt_013_disposition_remains_exact_closed_history() -> None:
    disposition = json.loads(
        gate.ATTEMPT_013_DISPOSITION_JSON.read_text(encoding="utf-8")
    )
    document = gate.ATTEMPT_013_DISPOSITION_DOCUMENT.read_text(encoding="utf-8")
    failures: list[str] = []

    assert isinstance(disposition, dict)
    gate._validate_attempt_013_disposition(  # noqa: SLF001
        disposition,
        document,
        failures,
    )

    assert failures == []
    assert disposition["attempt_contract"] == {
        "execution_attempt_budget": 0,
        "attempt_consumed": True,
        "retry_authorized": False,
        "automatic_retry_authorized": False,
        "recovery_authorized": False,
        "cleanup_authorized": False,
        "successor_attempt_authorized": False,
    }
    assert disposition["authority"] == gate.CLOSED_AUTHORITY


def test_attempt_013_pretag_candidate_fails_closed_before_live_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, commit, tree = _attempt_013_candidate_repository(
        tmp_path,
        tag_candidate=False,
    )
    del monkeypatch
    failures: list[str] = []

    gate._validate_attempt_013_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=commit,
        candidate_tree=tree,
        failures=failures,
    )

    assert failures == ["O4 Attempt 013 review tag is missing or not annotated"]


def test_attempt_013_closure_checkout_binds_exact_eight_paths_and_runtime(
    tmp_path: Path,
) -> None:
    repo, commit, tree = _attempt_013_closure_repository(tmp_path)
    failures: list[str] = []

    result = gate._validate_execution_checkout(  # noqa: SLF001
        repo,
        failures,
        candidate_parent_commit=gate.ATTEMPT_013_CANDIDATE_COMMIT,
        candidate_parent_tree=gate.ATTEMPT_013_CANDIDATE_TREE,
        reviewed_commit=gate.ATTEMPT_013_CANDIDATE_COMMIT,
        runtime_paths=gate.ATTEMPT_013_RUNTIME_PATHS,
        control_paths=gate.ATTEMPT_013_CLOSURE_CONTROL_PATH_ALLOWLIST,
    )

    assert len(gate.ATTEMPT_013_CONTROL_PATH_ALLOWLIST) == 6
    assert len(gate.ATTEMPT_013_CLOSURE_CONTROL_PATH_ALLOWLIST) == 8
    assert len(gate.ATTEMPT_013_RUNTIME_PATHS) == 6
    assert failures == []
    assert result == (commit, tree)


def test_attempt_012_closure_checkout_binds_exact_eight_paths_parent_and_runtime(
    tmp_path: Path,
) -> None:
    repo, commit, tree = _attempt_012_candidate_repository(tmp_path)
    failures: list[str] = []

    result = gate._validate_execution_checkout(  # noqa: SLF001
        repo,
        failures,
        candidate_parent_commit=gate.ATTEMPT_012_CANDIDATE_COMMIT,
        candidate_parent_tree=gate.ATTEMPT_012_CANDIDATE_TREE,
        reviewed_commit=gate.ATTEMPT_012_CANDIDATE_COMMIT,
        control_paths=gate.ATTEMPT_012_CLOSURE_CONTROL_PATH_ALLOWLIST,
    )

    assert len(gate.ATTEMPT_012_CLOSURE_CONTROL_PATH_ALLOWLIST) == 8
    assert failures == []
    assert result == (commit, tree)


def test_attempt_012_descendant_with_runtime_drift_is_not_a_closure_candidate(
    tmp_path: Path,
) -> None:
    repo, _, _ = _attempt_012_candidate_repository(tmp_path)
    producer = repo / "scripts/local_v1_lv1_003_o4_producer.py"
    producer.write_text(
        producer.read_text(encoding="utf-8") + "\n# forbidden test drift\n",
        encoding="utf-8",
    )
    _run_git(repo, "add", producer.relative_to(repo).as_posix())
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: forbidden closure descendant runtime drift",
    )
    failures: list[str] = []

    result = gate._validate_execution_checkout(  # noqa: SLF001
        repo,
        failures,
        candidate_parent_commit=gate.ATTEMPT_012_CANDIDATE_COMMIT,
        candidate_parent_tree=gate.ATTEMPT_012_CANDIDATE_TREE,
        reviewed_commit=gate.ATTEMPT_012_CANDIDATE_COMMIT,
        control_paths=gate.ATTEMPT_012_CLOSURE_CONTROL_PATH_ALLOWLIST,
    )

    assert result is None
    assert (
        "O4 execution checkout is not a single immediate child of the authorized parent"
        in failures
    )
    assert "O4 execution runtime differs from the exact reviewed candidate" in failures


def test_attempt_010_descendant_resolves_immutable_first_closure_child(
    tmp_path: Path,
) -> None:
    repo, closure_commit, _ = _attempt_010_control_child_repository(tmp_path)
    readme = repo / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\n<!-- descendant test -->\n",
        encoding="utf-8",
    )
    _run_git(repo, "add", "README.md")
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: descendant after O4 Attempt 010 closure",
    )
    failures: list[str] = []

    resolved = gate._attempt_010_closure_candidate_ref(repo, failures)  # noqa: SLF001

    assert failures == []
    assert resolved == closure_commit


def test_attempt_011_descendant_resolves_immutable_first_closure_child(
    tmp_path: Path,
) -> None:
    repo, closure_commit, _ = _attempt_011_closure_child_repository(tmp_path)
    readme = repo / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\n<!-- descendant test -->\n",
        encoding="utf-8",
    )
    _run_git(repo, "add", "README.md")
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: descendant after O4 Attempt 011 closure",
    )
    failures: list[str] = []

    resolved = gate._attempt_011_closure_candidate_ref(repo, failures)  # noqa: SLF001

    assert failures == []
    assert resolved == closure_commit


def test_enrollment_repair_review_binds_three_field_derived_principal_projection() -> None:
    document = gate.ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW.read_text(encoding="utf-8")
    normalized = " ".join(document.split())

    assert (
        "exactly three string fields: `node_id`, `principal_id`, and `workspace_id`" in normalized
    )
    assert "`principal_id` must equal `agent:node.{node_id}`" in normalized
    for stale in ("`agent_id`", "`gateway`", "`registered`", "five-field"):
        assert stale not in normalized


def test_consumed_gate_021_preserves_prior_consumed_history() -> None:
    contract = _contract()

    assert contract["record_status"] == (
        "ATTEMPT_021_CONSUMED_SUCCESS_O4_LV1_003_COMPLETE_NO_LIVE_AUTHORITY"
    )
    assert contract["attempt_010_id"] == gate.ATTEMPT_010_ID
    assert contract["attempt_010_review_tag"] == gate.ATTEMPT_010_REVIEW_TAG
    assert contract["attempt_010_attempted_candidate_commit"] == gate.ATTEMPT_010_CANDIDATE_COMMIT
    assert contract["attempt_010_attempted_candidate_tree"] == gate.ATTEMPT_010_CANDIDATE_TREE
    assert contract["attempt_010_failure_code"] == "fixed_node_start_failed"
    assert contract["attempt_010_highest_completed_stage"] == 11
    assert contract["attempt_010_cleanup_failure_codes"] == []
    assert contract["attempt_010_recovery_required"] is False
    assert contract["candidate_parent_commit"] == gate.CANDIDATE_PARENT_COMMIT
    assert contract["candidate_parent_tree"] == gate.CANDIDATE_PARENT_TREE
    assert (
        contract["execution_candidate_binding_mode"]
        == "exact_consumed_success_disposition_bound_to_reviewed_attempt_candidate"
    )
    assert contract["attempt_011_id"] == gate.ATTEMPT_011_ID
    assert contract["attempt_011_review_tag"] == gate.ATTEMPT_011_REVIEW_TAG
    assert contract["attempt_011_attempted_candidate_commit"] == gate.ATTEMPT_011_CANDIDATE_COMMIT
    assert contract["attempt_011_attempted_candidate_tree"] == gate.ATTEMPT_011_CANDIDATE_TREE
    assert contract["attempt_011_diagnostic_classification"] == (
        "fixed_node_runtime_state_inconsistent"
    )
    assert contract["attempt_011_root_cause_proven"] is False
    assert contract["attempt_012_id"] == gate.ATTEMPT_012_ID
    assert contract["attempt_012_review_tag"] == gate.ATTEMPT_012_REVIEW_TAG
    assert contract["attempt_012_candidate_parent_commit"] == gate.ATTEMPT_012_PARENT_COMMIT
    assert contract["attempt_012_candidate_parent_tree"] == gate.ATTEMPT_012_PARENT_TREE
    assert contract["attempt_012_execution_authorized"] is False
    assert contract["attempt_012_automatic_retry_authorized"] is False
    assert contract["attempt_012_fixed_node_start_failure_projection_only"] is True
    assert contract["attempt_012_success_not_predicted"] is True
    assert contract["fixed_node_state_projection_commit"] == (
        gate.FIXED_NODE_STATE_PROJECTION_COMMIT
    )
    assert contract["fixed_node_state_projection_tree"] == (
        gate.FIXED_NODE_STATE_PROJECTION_TREE
    )
    assert contract["attempt_012_attempted_candidate_commit"] == (
        gate.ATTEMPT_012_CANDIDATE_COMMIT
    )
    assert contract["attempt_012_attempted_candidate_tree"] == (
        gate.ATTEMPT_012_CANDIDATE_TREE
    )
    assert contract["attempt_012_run_identity_sha256"] == (
        gate.ATTEMPT_012_RUN_IDENTITY_DIGEST
    )
    assert contract["attempt_012_compose_project_identity_sha256"] == (
        gate.ATTEMPT_012_PROJECT_IDENTITY_DIGEST
    )
    assert contract["attempt_012_attempt_consumed"] is True
    assert contract["attempt_012_execution_attempt_budget"] == 0
    assert contract["attempt_012_retry_authorized"] is False
    assert contract["attempt_012_authority"] == gate.CLOSED_AUTHORITY
    assert all(value is False for value in contract["attempt_012_authority"].values())  # type: ignore[union-attr]
    assert contract["attempt_012_diagnostic_projection"] == {
        "collection_status": "complete",
        "collection_reason_code": "fixed_node_start_state_collected",
        "classification": "fixed_node_exited_observation_noncanonical",
        "container_presence": "present",
        "container_lifecycle_state": "exited",
        "container_running_state": "not_running",
        "container_exit_class": "nonzero",
        "container_health_state": "unhealthy",
        "container_failure_signal": "none",
        "observation_semantics": "sequential_container_then_mission",
        "mission_lifecycle_state": "claimed",
        "delivery_state": "claim_delivered",
        "evidence_state": "complete",
    }
    assert contract["fixed_bridge_phase_diagnostic_commit"] == (
        gate.ATTEMPT_013_REVIEWED_IMPLEMENTATION_COMMIT
    )
    assert contract["fixed_bridge_phase_diagnostic_tree"] == (
        gate.ATTEMPT_013_REVIEWED_IMPLEMENTATION_TREE
    )
    assert contract["fixed_bridge_phase_diagnostic_rejected_commit"] == (
        gate.FIXED_BRIDGE_PHASE_DIAGNOSTIC_REJECTED_COMMIT
    )
    projection = contract["fixed_node_state_projection_contract"]
    assert isinstance(projection, dict)
    assert projection["retained_keys"] == gate.FIXED_NODE_STATE_PROJECTION_KEYS
    assert len(projection["retained_keys"]) == 14  # type: ignore[arg-type]
    assert projection["fixed_bridge_last_entered_phase_values"] == (
        gate.FIXED_BRIDGE_PHASE_VALUES
    )
    assert len(projection["fixed_bridge_last_entered_phase_values"]) == 12  # type: ignore[arg-type]
    assert projection["raw_exit_identity_or_output_retained"] is False
    assert projection["sequential_nonatomic_noncausal"] is True
    assert projection["phase_grants_authority"] is False
    assert projection["phase_predicts_success"] is False
    assert contract["attempt_013_id"] == gate.ATTEMPT_013_ID
    assert contract["attempt_013_review_tag"] == gate.ATTEMPT_013_REVIEW_TAG
    assert contract["attempt_013_candidate_parent_commit"] == gate.ATTEMPT_013_PARENT_COMMIT
    assert contract["attempt_013_candidate_parent_tree"] == gate.ATTEMPT_013_PARENT_TREE
    assert contract["attempt_013_execution_authorized"] is True
    assert contract["attempt_013_automatic_retry_authorized"] is False
    assert contract["attempt_013_concurrent_invocation_authorized"] is False
    assert contract["attempt_013_post_attempt_retry_authorized"] is False
    assert contract["attempt_013_immediate_consumed_disposition_required"] is True
    assert contract["attempt_013_authority_derived_from_history_or_recovery"] is False
    assert contract["attempt_013_attempted_candidate_commit"] == (
        gate.ATTEMPT_013_CANDIDATE_COMMIT
    )
    assert contract["attempt_013_attempted_candidate_tree"] == (
        gate.ATTEMPT_013_CANDIDATE_TREE
    )
    assert contract["attempt_013_run_identity_sha256"] == (
        gate.ATTEMPT_013_RUN_IDENTITY_DIGEST
    )
    assert contract["attempt_013_compose_project_identity_sha256"] == (
        gate.ATTEMPT_013_PROJECT_IDENTITY_DIGEST
    )
    assert contract["attempt_013_diagnostic_projection"][
        "fixed_bridge_last_entered_phase"
    ] == "not_reported"  # type: ignore[index]
    assert contract["attempt_013_projection_behavior_source_explained"] is True
    assert contract["attempt_013_underlying_fixed_node_root_cause_explained"] is False
    assert contract["terminal_health_phase_projection_commit"] == (
        gate.TERMINAL_HEALTH_PHASE_PROJECTION_COMMIT
    )
    assert contract["terminal_health_phase_projection_tree"] == (
        gate.TERMINAL_HEALTH_PHASE_PROJECTION_TREE
    )
    assert contract["terminal_health_phase_projection_review_record_commit"] == (
        gate.TERMINAL_HEALTH_PHASE_PROJECTION_REVIEW_RECORD_COMMIT
    )
    assert contract["terminal_health_phase_projection_review_findings"] == {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    assert contract["attempt_014_id"] == gate.ATTEMPT_014_ID
    assert contract["attempt_014_candidate_parent_commit"] == (
        gate.TERMINAL_HEALTH_PHASE_PROJECTION_REVIEW_RECORD_COMMIT
    )
    assert contract["attempt_014_review_tag"] == gate.ATTEMPT_014_REVIEW_TAG
    assert contract["attempt_014_execution_authorized"] is True
    assert contract["attempt_014_automatic_retry_authorized"] is False
    assert contract["attempt_014_concurrent_invocation_authorized"] is False
    assert contract["attempt_014_post_attempt_retry_authorized"] is False
    assert contract["attempt_014_immediate_consumed_disposition_required"] is True
    assert contract["attempt_014_attempted_candidate_commit"] == (
        gate.ATTEMPT_014_CANDIDATE_COMMIT
    )
    assert contract["attempt_014_attempted_candidate_tree"] == gate.ATTEMPT_014_CANDIDATE_TREE
    assert contract["attempt_014_diagnostic_projection"][
        "fixed_bridge_last_entered_phase"
    ] == "socket_parent_validation_entered"  # type: ignore[index]
    assert contract["attempt_014_run_identity_sha256"] == (
        gate.ATTEMPT_014_RUN_IDENTITY_DIGEST
    )
    assert contract["attempt_014_compose_project_identity_sha256"] == (
        gate.ATTEMPT_014_PROJECT_IDENTITY_DIGEST
    )
    assert contract["socket_parent_mode_commit"] == gate.SOCKET_PARENT_MODE_COMMIT
    assert contract["socket_parent_mode_tree"] == gate.SOCKET_PARENT_MODE_TREE
    assert contract["socket_parent_mode_review_record_commit"] == (
        gate.SOCKET_PARENT_MODE_REVIEW_RECORD_COMMIT
    )
    assert contract["socket_parent_mode_review_findings"] == {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    assert contract["attempt_015_id"] == gate.ATTEMPT_015_ID
    assert contract["attempt_015_review_tag"] == gate.ATTEMPT_015_REVIEW_TAG
    assert contract["attempt_015_execution_authorized"] is False
    assert contract["attempt_015_automatic_retry_authorized"] is False
    assert contract["attempt_015_concurrent_invocation_authorized"] is False
    assert contract["attempt_015_post_attempt_retry_authorized"] is False
    assert contract["attempt_015_deterministic_source_contradiction_repaired"] is True
    assert contract["attempt_015_success_not_predicted"] is True
    assert contract["attempt_015_attempted_candidate_commit"] == gate.ATTEMPT_015_CANDIDATE_COMMIT
    assert contract["attempt_015_attempted_candidate_tree"] == gate.ATTEMPT_015_CANDIDATE_TREE
    assert contract["attempt_015_failure_code"] == "gateway_mission_projection_invalid"
    assert contract["attempt_015_primary_failure_code"] == "gateway_mission_projection_invalid"
    assert contract["attempt_015_highest_completed_stage"] == 13
    assert contract["attempt_015_run_identity_sha256"] == gate.ATTEMPT_015_RUN_IDENTITY_DIGEST
    assert contract["attempt_015_compose_project_identity_sha256"] == (
        gate.ATTEMPT_015_PROJECT_IDENTITY_DIGEST
    )
    assert contract["attempt_017_id"] == gate.ATTEMPT_017_ID
    assert contract["attempt_017_execution_authorized"] is False
    assert contract["attempt_017_automatic_retry_authorized"] is False
    assert contract["attempt_017_concurrent_invocation_authorized"] is False
    assert contract["attempt_017_post_attempt_retry_authorized"] is False
    assert contract["attempt_017_failure_code"] == "gateway_mission_projection_invalid"
    assert contract["attempt_017_highest_completed_stage"] == 13
    assert contract["attempt_017_cleanup_failure_codes"] == []
    assert contract["attempt_017_recovery_required"] is False
    assert contract["attempt_017_root_cause_proven"] is False
    assert contract["attempt_018_id"] == gate.ATTEMPT_018_ID
    assert contract["attempt_018_execution_authorized"] is False
    assert contract["attempt_018_automatic_retry_authorized"] is False
    assert contract["attempt_018_concurrent_invocation_authorized"] is False
    assert contract["attempt_018_post_attempt_retry_authorized"] is False
    assert contract["attempt_018_review_tag"] == gate.ATTEMPT_018_REVIEW_TAG
    assert contract["attempt_019_id"] == gate.ATTEMPT_019_ID
    assert contract["attempt_019_execution_authorized"] is False
    assert contract["attempt_019_automatic_retry_authorized"] is False
    assert contract["attempt_019_concurrent_invocation_authorized"] is False
    assert contract["attempt_019_post_attempt_retry_authorized"] is False
    assert contract["attempt_019_review_tag"] == gate.ATTEMPT_019_REVIEW_TAG
    assert contract["attempt_020_id"] == gate.ATTEMPT_020_ID
    assert contract["attempt_020_execution_authorized"] is False
    assert contract["attempt_020_review_tag"] == gate.ATTEMPT_020_REVIEW_TAG
    assert contract["attempt_021_id"] == gate.ATTEMPT_021_ID
    assert contract["attempt_021_execution_authorized"] is False
    assert contract["attempt_021_review_tag"] == gate.ATTEMPT_021_REVIEW_TAG
    assert contract["execution_attempt_budget"] == 0
    assert contract["attempt_consumed"] is True
    assert contract["retry_authorized"] is False
    assert contract["attempt_011_automatic_retry_authorized"] is False
    assert contract["attempt_010_automatic_retry_authorized"] is False
    assert contract["persistent_cross_process_budget_consumption_claimed"] is False
    assert contract["immediate_post_attempt_disposition_recorded"] is True
    assert contract["mcc_review_disposition"] == "GO_CODE_ONLY"
    assert contract["mcc_review_findings"] == {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    authority = contract["authority"]
    assert isinstance(authority, dict)
    assert authority == gate.EXPECTED_AUTHORITY
    assert {key for key, enabled in authority.items() if enabled} == (
        gate.TRUE_AUTHORITY_FIELDS
    )
    assert len(authority) == 19
    recovery = contract["attempt008_recovery_closure_binding"]
    assert isinstance(recovery, dict)
    assert recovery["recovery_closed"] is True
    assert recovery["successor_authority_derived_from_recovery"] is False
    assert recovery["cleanup_or_full_project_removal_claimed"] is False
    assert recovery["general_absence_claimed"] is False


def test_attempt_014_exact_eight_path_closure_and_annotated_tag_binding(
    tmp_path: Path,
) -> None:
    repo, commit, tree = _attempt_014_closure_repository(tmp_path)
    failures: list[str] = []

    checkout = gate._validate_execution_checkout(  # noqa: SLF001
        repo,
        failures,
        candidate_parent_commit=gate.ATTEMPT_014_CANDIDATE_COMMIT,
        candidate_parent_tree=gate.ATTEMPT_014_CANDIDATE_TREE,
        reviewed_commit=gate.ATTEMPT_014_CANDIDATE_COMMIT,
        runtime_paths=gate.ATTEMPT_014_RUNTIME_PATHS,
        control_paths=gate.ATTEMPT_014_CLOSURE_CONTROL_PATH_ALLOWLIST,
    )
    gate._validate_attempt_014_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=gate.ATTEMPT_014_CANDIDATE_COMMIT,
        candidate_tree=gate.ATTEMPT_014_CANDIDATE_TREE,
        failures=failures,
    )

    assert failures == []
    assert checkout == (commit, tree)
    assert len(gate.ATTEMPT_014_CLOSURE_CONTROL_PATH_ALLOWLIST) == 8


def test_attempt_014_repair_and_review_bindings_are_exact() -> None:
    document = gate.TERMINAL_HEALTH_PHASE_PROJECTION_REVIEW.read_text(encoding="utf-8")
    failures: list[str] = []

    gate._validate_terminal_health_phase_projection_review(  # noqa: SLF001
        ROOT,
        document,
        failures,
    )

    assert failures == []


def test_attempt_014_tracked_disposition_is_closed_and_exact() -> None:
    disposition = json.loads(
        gate.ATTEMPT_014_DISPOSITION_JSON.read_text(encoding="utf-8")
    )
    failures: list[str] = []

    gate._validate_attempt_014_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_014_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []
    assert disposition["authority"] == gate.CLOSED_AUTHORITY
    assert disposition["normalized_fixed_node_start_diagnostic"][
        "fixed_bridge_last_entered_phase"
    ] == "socket_parent_validation_entered"


def test_attempt_015_consumed_disposition_is_exact() -> None:
    disposition = json.loads(
        gate.ATTEMPT_015_DISPOSITION_JSON.read_text(encoding="utf-8")
    )
    failures: list[str] = []

    gate._validate_attempt_015_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_015_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []
    assert disposition["attempt_contract"]["execution_attempt_budget"] == 0
    assert disposition["attempt_contract"]["attempt_consumed"] is True
    assert disposition["authority"] == gate.CLOSED_AUTHORITY


def test_attempt_015_consumed_exact_eight_path_closure(
    tmp_path: Path,
) -> None:
    repo, commit, tree = _attempt_015_closure_repository(tmp_path)
    failures: list[str] = []

    checkout = gate._validate_execution_checkout(  # noqa: SLF001
        repo,
        failures,
        candidate_parent_commit=gate.ATTEMPT_015_CANDIDATE_COMMIT,
        candidate_parent_tree=gate.ATTEMPT_015_CANDIDATE_TREE,
        reviewed_commit=gate.ATTEMPT_015_CANDIDATE_COMMIT,
        runtime_paths=gate.ATTEMPT_015_RUNTIME_PATHS,
        control_paths=gate.ATTEMPT_015_CLOSURE_CONTROL_PATH_ALLOWLIST,
    )
    gate._validate_attempt_015_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=gate.ATTEMPT_015_CANDIDATE_COMMIT,
        candidate_tree=gate.ATTEMPT_015_CANDIDATE_TREE,
        failures=failures,
    )

    assert failures == []
    assert checkout == (commit, tree)
    assert len(gate.ATTEMPT_015_CLOSURE_CONTROL_PATH_ALLOWLIST) == 8


def test_attempt_016_consumed_disposition_projection_is_exact() -> None:
    disposition = json.loads(
        gate.ATTEMPT_016_DISPOSITION_JSON.read_text(encoding="utf-8")
    )
    failures: list[str] = []

    gate._validate_attempt_016_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_016_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []
    projection = disposition["identity_free_gateway_mission_projection"]
    assert projection["mission_lifecycle_state"] == "runner_reported_running"
    assert disposition["diagnostic_claims"]["attempt_017_authorized"] is False
    assert disposition["attempt_contract"]["execution_attempt_budget"] == 0
    assert disposition["authority"] == gate.CLOSED_AUTHORITY


def test_attempt_016_consumed_exact_eight_path_closure_cannot_authorize_attempt_017(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, _ = _attempt_016_closure_repository(tmp_path)
    _skip_private_evidence(monkeypatch)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert len(gate.ATTEMPT_016_CLOSURE_CONTROL_PATH_ALLOWLIST) == 8


def test_attempt_016_consumed_contract_is_preserved_under_attempt_021_gate() -> None:
    contract = _contract()
    failures: list[str] = []

    gate._validate_contract(contract, failures)  # noqa: SLF001

    assert failures == []
    assert contract["attempt_016_execution_authorized"] is False
    assert contract["attempt_017_execution_authorized"] is False
    assert contract["attempt_018_execution_authorized"] is False
    assert contract["attempt_019_execution_authorized"] is False
    assert contract["attempt_020_execution_authorized"] is False
    assert contract["attempt_021_execution_authorized"] is False
    assert contract["execution_attempt_budget"] == 0
    assert contract["attempt_consumed"] is True
    assert contract["attempt_016_identity_free_gateway_mission_projection"][
        "mission_lifecycle_state"
    ] == "runner_reported_running"  # type: ignore[index]
    authority = contract["authority"]
    assert isinstance(authority, dict)
    assert len(authority) == 19
    assert {key for key, enabled in authority.items() if enabled} == gate.TRUE_AUTHORITY_FIELDS


def test_attempt_017_consumed_closure_cannot_authorize_attempt_019(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, _ = _attempt_017_closure_repair_repository(tmp_path)
    _skip_private_evidence(monkeypatch)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert report["execution_checkout_commit"] is None
    assert report["execution_checkout_tree"] is None
    assert report["execution_attempt_budget"] == 0
    assert report["attempt_consumed"] is True
    assert report["live_execution_authorized"] is False
    assert len(gate.ATTEMPT_017_CLOSURE_CONTROL_PATH_ALLOWLIST) == 8
    assert len(gate.ATTEMPT_017_CLOSURE_REPAIR_CONTROL_PATH_ALLOWLIST) == 2


def test_attempt_017_consumed_disposition_has_both_exact_projections(
) -> None:
    disposition = json.loads(
        gate.ATTEMPT_017_DISPOSITION_JSON.read_text(encoding="utf-8")
    )
    failures: list[str] = []

    gate._validate_attempt_017_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_017_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []
    assert disposition["identity_free_gateway_mission_projection"][
        "mission_lifecycle_state"
    ] == "runner_reported_running"
    assert disposition["identity_free_node_receipt_projection"]["next_operation"] == (
        "completion_pending"
    )
    assert disposition["identity_free_node_receipt_projection"][
        "last_closed_status"
    ] == "failed_closed"
    serialized = json.dumps(disposition, sort_keys=True)
    assert "ithildin-local-v1-o4-" not in serialized
    assert not re.search(r"20[0-9]{6}T[0-9]{6}Z-[0-9a-f]{8}", serialized)


def test_attempt_017_private_receipt_fixture_is_exact_and_identity_silent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, run_name, project_name = _synthetic_attempt_017_receipts(
        tmp_path,
        monkeypatch,
    )
    failures: list[str] = []

    gate._validate_attempt_017_receipts(repo, failures)  # noqa: SLF001

    assert failures == []
    failure_text = "\n".join(failures)
    assert run_name not in failure_text
    assert project_name not in failure_text


def test_attempt_017_private_receipt_fixture_rejects_node_projection_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, diagnostic, run_name, project_name = _synthetic_attempt_017_receipts(
        tmp_path,
        monkeypatch,
    )
    document = json.loads(diagnostic.read_text(encoding="utf-8"))
    document["node_receipt_projection_diagnostic"]["next_operation_state"] = (
        "completion_recorded"
    )
    diagnostic_bytes = (
        json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    diagnostic.write_bytes(diagnostic_bytes)
    diagnostic.chmod(0o600)
    monkeypatch.setattr(gate, "ATTEMPT_017_DIAGNOSTIC_SIZE", len(diagnostic_bytes))
    monkeypatch.setattr(
        gate,
        "ATTEMPT_017_DIAGNOSTIC_RECEIPT_DIGEST",
        "sha256:" + hashlib.sha256(diagnostic_bytes).hexdigest(),
    )
    failures: list[str] = []

    gate._validate_attempt_017_receipts(repo, failures)  # noqa: SLF001

    assert "O4 Attempt 017 Node receipt projection is not exact" in failures
    failure_text = "\n".join(failures)
    assert run_name not in failure_text
    assert project_name not in failure_text


def test_attempt_017_lightweight_tag_fails_closed(
    tmp_path: Path,
) -> None:
    repo, commit, tree = _attempt_017_candidate_repository(
        tmp_path,
        tag_candidate=False,
    )
    _run_git(repo, "tag", gate.ATTEMPT_017_REVIEW_TAG, commit)
    failures: list[str] = []

    gate._validate_attempt_017_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=commit,
        candidate_tree=tree,
        failures=failures,
    )

    assert failures == ["O4 Attempt 017 review tag is missing or not annotated"]


def test_attempt_018_consumed_contract_is_preserved_under_attempt_021_gate() -> None:
    contract = _contract()
    failures: list[str] = []

    gate._validate_contract(contract, failures)  # noqa: SLF001
    gate._validate_mission_convergence_review(  # noqa: SLF001
        ROOT,
        gate.MISSION_CONVERGENCE_REVIEW.read_text(encoding="utf-8"),
        failures,
    )
    gate._validate_mission_liveness_terminal_reason_review(  # noqa: SLF001
        ROOT,
        gate.MISSION_LIVENESS_TERMINAL_REASON_REVIEW.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []
    assert contract["execution_attempt_budget"] == 0
    assert contract["attempt_consumed"] is True
    assert contract["attempt_017_execution_authorized"] is False
    assert contract["attempt_018_execution_authorized"] is False
    assert contract["attempt_019_execution_authorized"] is False
    assert contract["attempt_020_execution_authorized"] is False
    assert contract["attempt_021_execution_authorized"] is False
    authority = contract["authority"]
    assert isinstance(authority, dict)
    assert len(authority) == 19
    assert {key for key, enabled in authority.items() if enabled} == gate.TRUE_AUTHORITY_FIELDS


def test_attempt_018_consumed_disposition_has_terminal_reason() -> None:
    disposition = json.loads(
        gate.ATTEMPT_018_DISPOSITION_JSON.read_text(encoding="utf-8")
    )
    failures: list[str] = []

    gate._validate_attempt_018_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_018_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []
    assert disposition["identity_free_gateway_mission_projection"][
        "mission_lifecycle_state"
    ] == "runner_reported_running"
    node_projection = disposition["identity_free_node_receipt_projection"]
    assert node_projection["next_operation"] == "completion_pending"
    assert node_projection["last_closed_status"] == "failed_closed"
    assert node_projection["last_closed_reason_code"] == "bridge_disconnected"
    assert disposition["attempt_contract"]["execution_attempt_budget"] == 0
    assert disposition["attempt_contract"]["attempt_consumed"] is True
    assert disposition["authority"] == gate.CLOSED_AUTHORITY


def test_attempt_018_real_private_receipts_are_exact() -> None:
    failures: list[str] = []

    gate._validate_attempt_018_receipts(ROOT, failures)  # noqa: SLF001

    assert failures == []


def test_attempt_018_consumed_closure_cannot_authorize_attempt_021(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, _ = _attempt_018_closure_repository(tmp_path)
    _skip_private_evidence(monkeypatch)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert report["attempt_id"] == gate.ATTEMPT_021_ID
    assert report["execution_checkout_commit"] is None
    assert report["execution_checkout_tree"] is None
    assert report["execution_attempt_budget"] == 0
    assert report["attempt_consumed"] is True
    assert report["attempt_018_consumed"] is True
    assert report["attempt_021_consumed"] is True
    assert report["live_execution_authorized"] is False
    assert len(gate.ATTEMPT_018_CLOSURE_CONTROL_PATH_ALLOWLIST) == 8


def test_attempt_019_consumed_closure_cannot_authorize_attempt_021(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, _ = _attempt_019_closure_repository(tmp_path)
    _skip_private_evidence(monkeypatch)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert report["attempt_id"] == gate.ATTEMPT_021_ID
    assert report["execution_checkout_commit"] is None
    assert report["execution_checkout_tree"] is None
    assert report["execution_attempt_budget"] == 0
    assert report["attempt_consumed"] is True
    assert report["attempt_019_consumed"] is True
    assert report["attempt_021_consumed"] is True
    assert report["live_execution_authorized"] is False
    assert report["next_action"] == (
        "pause_after_o4_lv1_003_complete_do_not_start_lv1_004_or_o5"
    )
    assert report["release_allowed"] is False
    assert report["uat_complete"] is False
    assert len(gate.ATTEMPT_019_CLOSURE_CONTROL_PATH_ALLOWLIST) == 8


def test_attempt_019_real_private_receipts_are_exact() -> None:
    failures: list[str] = []

    gate._validate_attempt_019_receipts(ROOT, failures)  # noqa: SLF001

    assert failures == []


def test_attempt_019_consumed_contract_is_preserved_under_attempt_021_gate() -> None:
    contract = _contract()
    failures: list[str] = []

    gate._validate_contract(contract, failures)  # noqa: SLF001
    gate._validate_two_operation_terminal_repair_review(  # noqa: SLF001
        ROOT,
        gate.TWO_OPERATION_TERMINAL_REPAIR_REVIEW.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []
    assert contract["execution_attempt_budget"] == 0
    assert contract["attempt_consumed"] is True
    assert contract["attempt_018_execution_authorized"] is False
    assert contract["attempt_019_execution_authorized"] is False
    assert contract["attempt_020_execution_authorized"] is False
    assert contract["attempt_021_execution_authorized"] is False
    assert contract["attempt_019_failure_code"] == "gateway_run_detail_invalid"
    assert contract["attempt_019_identity_free_node_receipt_projection"][
        "last_closed_status"
    ] == "runner_reported_succeeded"  # type: ignore[index]
    disposition = json.loads(
        gate.ATTEMPT_019_DISPOSITION_JSON.read_text(encoding="utf-8")
    )
    gate._validate_attempt_019_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_019_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )
    assert failures == []
    authority = contract["authority"]
    assert isinstance(authority, dict)
    assert len(authority) == 19
    assert {key for key, enabled in authority.items() if enabled} == gate.TRUE_AUTHORITY_FIELDS


def test_attempt_020_consumed_closure_cannot_authorize_attempt_021(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, _ = _attempt_020_closure_repository(tmp_path)
    _skip_private_evidence(monkeypatch)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert report["attempt_id"] == gate.ATTEMPT_021_ID
    assert report["execution_checkout_commit"] is None
    assert report["execution_checkout_tree"] is None
    assert report["execution_attempt_budget"] == 0
    assert report["attempt_consumed"] is True
    assert report["attempt_020_consumed"] is True
    assert report["attempt_021_consumed"] is True
    assert report["live_execution_authorized"] is False
    assert report["producer_code_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False
    assert report["next_action"] == (
        "pause_after_o4_lv1_003_complete_do_not_start_lv1_004_or_o5"
    )
    assert report["release_allowed"] is False
    assert report["uat_complete"] is False
    assert len(gate.ATTEMPT_020_CLOSURE_CONTROL_PATH_ALLOWLIST) == 8


def test_attempt_020_real_private_receipts_are_exact() -> None:
    failures: list[str] = []

    gate._validate_attempt_020_receipts(ROOT, failures)  # noqa: SLF001

    assert failures == []


def test_attempt_020_consumed_contract_and_disposition_are_exact() -> None:
    contract = _contract()
    failures: list[str] = []

    gate._validate_contract(contract, failures)  # noqa: SLF001
    assert contract["attempt_020_execution_authorized"] is False
    assert contract["attempt_020_automatic_retry_authorized"] is False
    assert contract["attempt_020_concurrent_invocation_authorized"] is False
    assert contract["attempt_020_post_attempt_retry_authorized"] is False
    assert contract["attempt_020_recovery_authorized"] is False
    assert contract["attempt_020_cleanup_authorized"] is False
    assert contract["attempt_020_failure_code"] == "gateway_run_detail_invalid"
    assert contract["attempt_020_identity_free_node_receipt_projection"][
        "last_closed_status"
    ] == "runner_reported_succeeded"  # type: ignore[index]
    assert contract["attempt_020_immediate_consumed_disposition_required"] is True
    disposition = json.loads(
        gate.ATTEMPT_020_DISPOSITION_JSON.read_text(encoding="utf-8")
    )
    gate._validate_attempt_020_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_020_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )
    assert failures == []


def test_attempt_021_contract_preserves_consumed_history_and_bounded_authority() -> None:
    contract = _contract()
    failures: list[str] = []

    gate._validate_contract(contract, failures)  # noqa: SLF001

    assert failures == []
    assert contract["record_status"] == (
        "ATTEMPT_021_CONSUMED_SUCCESS_O4_LV1_003_COMPLETE_NO_LIVE_AUTHORITY"
    )
    assert contract["attempt_020_execution_authorized"] is False
    assert contract["attempt_020_failure_code"] == "gateway_run_detail_invalid"
    assert contract["attempt_021_id"] == gate.ATTEMPT_021_ID
    assert contract["attempt_021_execution_authorized"] is False
    assert contract["attempt_021_automatic_retry_authorized"] is False
    assert contract["attempt_021_concurrent_invocation_authorized"] is False
    assert contract["attempt_021_post_attempt_retry_authorized"] is False
    assert contract["attempt_021_recovery_authorized"] is False
    assert contract["attempt_021_cleanup_authorized"] is False
    assert contract["attempt_021_review_tag"] == gate.ATTEMPT_021_REVIEW_TAG
    assert contract["execution_attempt_budget"] == 0
    assert contract["attempt_consumed"] is True
    authority = contract["authority"]
    assert isinstance(authority, dict)
    assert len(authority) == 19
    assert {key for key, enabled in authority.items() if enabled} == (
        set()
    )


def test_gateway_session_binding_review_contract_is_exact() -> None:
    failures: list[str] = []
    document = gate.GATEWAY_SESSION_BINDING_REPAIR_REVIEW.read_text(encoding="utf-8")

    gate._validate_gateway_session_binding_repair_review(  # noqa: SLF001
        ROOT,
        document,
        failures,
    )

    assert failures == []
    assert len(gate.GATEWAY_SESSION_BINDING_REPAIR_PATH_DIGESTS) == 5
    assert gate.ATTEMPT_021_RUNTIME_PATHS == list(
        gate.GATEWAY_SESSION_BINDING_REPAIR_PATH_DIGESTS
    )


def test_attempt_021_exact_consumed_success_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, commit, tree = _attempt_021_closure_repository(tmp_path)
    _skip_private_evidence(monkeypatch)

    report = gate.build_report(repo)

    assert report["valid"] is True, report["failures"]
    assert report["execution_checkout_commit"] == commit
    assert report["execution_checkout_tree"] == tree
    assert report["execution_attempt_budget"] == 0
    assert report["attempt_consumed"] is True
    assert report["retry_authorized"] is False
    assert report["live_execution_authorized"] is False
    assert report["producer_code_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False
    assert report["new_governed_tool"] is False
    assert report["release_allowed"] is False
    assert report["uat_complete"] is False
    assert report["next_action"] == (
        "pause_after_o4_lv1_003_complete_do_not_start_lv1_004_or_o5"
    )
    assert len(gate.ATTEMPT_021_CLOSURE_CONTROL_PATH_ALLOWLIST) == 16


def test_attempt_021_disposition_is_digest_bound_and_closes_only_o4() -> None:
    disposition = json.loads(gate.ATTEMPT_021_DISPOSITION_JSON.read_text(encoding="utf-8"))
    failures: list[str] = []
    gate._validate_attempt_021_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_021_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )
    assert failures == []
    assert disposition["closure"]["o4_complete"] is True
    assert disposition["closure"]["lv1_003_complete"] is True
    assert disposition["closure"]["o5_authorized"] is False


def test_attempt_015_exact_six_path_candidate_and_annotated_tag_binding(
    tmp_path: Path,
) -> None:
    repo, commit, tree = _attempt_015_candidate_repository(
        tmp_path,
        tag_candidate=True,
    )
    failures: list[str] = []

    checkout = gate._validate_execution_checkout(  # noqa: SLF001
        repo,
        failures,
        candidate_parent_commit=gate.SOCKET_PARENT_MODE_REVIEW_RECORD_COMMIT,
        candidate_parent_tree=gate.SOCKET_PARENT_MODE_REVIEW_RECORD_TREE,
        reviewed_commit=gate.SOCKET_PARENT_MODE_COMMIT,
        runtime_paths=gate.ATTEMPT_015_RUNTIME_PATHS,
        control_paths=gate.ATTEMPT_015_CONTROL_PATH_ALLOWLIST,
    )
    gate._validate_attempt_015_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=commit,
        candidate_tree=tree,
        failures=failures,
    )

    assert failures == []
    assert checkout == (commit, tree)
    assert len(gate.ATTEMPT_015_CONTROL_PATH_ALLOWLIST) == 6


def test_attempt_015_pretag_candidate_fails_closed(
    tmp_path: Path,
) -> None:
    repo, commit, tree = _attempt_015_candidate_repository(
        tmp_path,
        tag_candidate=False,
    )
    failures: list[str] = []

    gate._validate_attempt_015_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=commit,
        candidate_tree=tree,
        failures=failures,
    )

    assert failures == ["O4 Attempt 015 review tag is missing or not annotated"]


def test_attempt_015_socket_parent_mode_review_binding_is_exact() -> None:
    document = gate.SOCKET_PARENT_MODE_REVIEW.read_text(encoding="utf-8")
    failures: list[str] = []

    gate._validate_socket_parent_mode_review(ROOT, document, failures)  # noqa: SLF001

    assert failures == []


@pytest.mark.parametrize(
    "mapped_description",
    [
        (
            "`M1`: a successful fixed-Node start return bypassed the existing forbidden-output "
            "validation before Hermes could run"
        ),
        (
            "`L1`: a post-bind or pre-discard anchor-validation failure could leave the "
            "diagnostic container identity transiently bound"
        ),
    ],
)
def test_fixed_node_diagnostic_review_rejects_mapped_finding_description_drift(
    mapped_description: str,
) -> None:
    document = gate.FIXED_NODE_START_DIAGNOSTIC_REVIEW.read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    assert mapped_description in normalized
    drifted = normalized.replace(mapped_description, "mapped finding transposed", 1)
    failures: list[str] = []

    gate._validate_fixed_node_start_diagnostic_review(  # noqa: SLF001
        ROOT,
        drifted,
        failures,
    )

    assert any(mapped_description in failure for failure in failures)


def test_fixed_node_state_projection_review_and_runtime_bindings_are_exact() -> None:
    document = gate.FIXED_NODE_STATE_PROJECTION_REVIEW.read_text(encoding="utf-8")
    failures: list[str] = []

    gate._validate_fixed_node_state_projection_review(  # noqa: SLF001
        ROOT,
        document,
        failures,
    )

    assert failures == []
    assert gate._file_digest(  # noqa: SLF001
        gate.FIXED_NODE_STATE_PROJECTION_REVIEW,
        [],
    ) == gate.FIXED_NODE_STATE_PROJECTION_REVIEW_DIGEST
    assert _git_blob_digest(
        ROOT,
        gate.FIXED_NODE_STATE_PROJECTION_COMMIT,
        "scripts/local_v1_lv1_003_o4_producer.py",
    ) == gate.FIXED_NODE_STATE_PROJECTION_PRODUCER_DIGEST
    assert _git_blob_digest(
        ROOT,
        gate.FIXED_NODE_STATE_PROJECTION_COMMIT,
        "tests/test_local_v1_lv1_003_o4_producer.py",
    ) == gate.FIXED_NODE_STATE_PROJECTION_TEST_DIGEST


def test_fixed_node_state_projection_review_rejects_content_drift() -> None:
    document = gate.FIXED_NODE_STATE_PROJECTION_REVIEW.read_text(encoding="utf-8")
    failures: list[str] = []

    gate._validate_fixed_node_state_projection_review(  # noqa: SLF001
        ROOT,
        document.replace("67,200-case classifier audit", "smaller audit", 1),
        failures,
    )

    assert any("state projection review is missing phrase" in item for item in failures)
    assert "O4 fixed-Node state projection review digest is invalid" in failures


def test_fixed_bridge_phase_review_and_six_runtime_hashes_are_exact() -> None:
    document = gate.FIXED_BRIDGE_PHASE_DIAGNOSTIC_REVIEW.read_text(encoding="utf-8")
    failures: list[str] = []

    gate._validate_fixed_bridge_phase_diagnostic_review(  # noqa: SLF001
        ROOT,
        document,
        failures,
    )

    assert failures == []
    assert gate._digest(document) == gate.FIXED_BRIDGE_PHASE_DIAGNOSTIC_REVIEW_DIGEST  # noqa: SLF001
    assert set(gate.FIXED_BRIDGE_PHASE_DIAGNOSTIC_PATH_DIGESTS) == set(
        gate.ATTEMPT_013_RUNTIME_PATHS
    )


def test_fixed_bridge_phase_review_rejects_content_drift() -> None:
    document = gate.FIXED_BRIDGE_PHASE_DIAGNOSTIC_REVIEW.read_text(encoding="utf-8")
    failures: list[str] = []

    gate._validate_fixed_bridge_phase_diagnostic_review(  # noqa: SLF001
        ROOT,
        document.replace(
            "nine closed, non-authoritative last-entered phase markers",
            "unbounded phase markers",
            1,
        ),
        failures,
    )

    assert any("fixed-bridge phase review is missing phrase" in item for item in failures)
    assert "O4 fixed-bridge phase review digest is invalid" in failures


def test_attempt_012_review_tag_rejects_missing_lightweight_wrong_and_moved(
    tmp_path: Path,
) -> None:
    repo, commit, _ = _attempt_012_candidate_repository(tmp_path)

    failures: list[str] = []
    gate._validate_attempt_012_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=gate.ATTEMPT_012_CANDIDATE_COMMIT,
        candidate_tree=gate.ATTEMPT_012_CANDIDATE_TREE,
        failures=failures,
    )
    assert failures == []

    _run_git(repo, "tag", "-d", gate.ATTEMPT_012_REVIEW_TAG)
    failures = []
    gate._validate_attempt_012_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=gate.ATTEMPT_012_CANDIDATE_COMMIT,
        candidate_tree=gate.ATTEMPT_012_CANDIDATE_TREE,
        failures=failures,
    )
    assert "O4 Attempt 012 review tag is missing or not annotated" in failures

    _run_git(repo, "tag", gate.ATTEMPT_012_REVIEW_TAG, commit)
    failures = []
    gate._validate_attempt_012_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=gate.ATTEMPT_012_CANDIDATE_COMMIT,
        candidate_tree=gate.ATTEMPT_012_CANDIDATE_TREE,
        failures=failures,
    )
    assert "O4 Attempt 012 review tag is missing or not annotated" in failures

    _run_git(repo, "tag", "-d", gate.ATTEMPT_012_REVIEW_TAG)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "tag",
        "-a",
        gate.ATTEMPT_012_REVIEW_TAG,
        "-m",
        "test: wrong reviewed target",
        commit,
    )
    failures = []
    gate._validate_attempt_012_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=gate.ATTEMPT_012_CANDIDATE_COMMIT,
        candidate_tree=gate.ATTEMPT_012_CANDIDATE_TREE,
        failures=failures,
    )
    assert (
        "O4 Attempt 012 annotated review tag does not peel to the exact candidate"
        in failures
    )

    _run_git(repo, "tag", "-d", gate.ATTEMPT_012_REVIEW_TAG)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "tag",
        "-a",
        gate.ATTEMPT_012_REVIEW_TAG,
        "-m",
        "test: restored exact reviewed target",
        gate.ATTEMPT_012_CANDIDATE_COMMIT,
    )
    failures = []
    gate._validate_attempt_012_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=gate.ATTEMPT_012_CANDIDATE_COMMIT,
        candidate_tree=gate.ATTEMPT_012_CANDIDATE_TREE,
        failures=failures,
    )
    assert failures == []


def test_attempt_013_review_tag_rejects_missing_lightweight_wrong_and_moved(
    tmp_path: Path,
) -> None:
    repo, commit, tree = _attempt_013_candidate_repository(tmp_path)

    failures: list[str] = []
    gate._validate_attempt_013_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=commit,
        candidate_tree=tree,
        failures=failures,
    )
    assert failures == []

    _run_git(repo, "tag", "-d", gate.ATTEMPT_013_REVIEW_TAG)
    failures = []
    gate._validate_attempt_013_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=commit,
        candidate_tree=tree,
        failures=failures,
    )
    assert "O4 Attempt 013 review tag is missing or not annotated" in failures

    _run_git(repo, "tag", gate.ATTEMPT_013_REVIEW_TAG, commit)
    failures = []
    gate._validate_attempt_013_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=commit,
        candidate_tree=tree,
        failures=failures,
    )
    assert "O4 Attempt 013 review tag is missing or not annotated" in failures

    _run_git(repo, "tag", "-d", gate.ATTEMPT_013_REVIEW_TAG)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "tag",
        "-a",
        gate.ATTEMPT_013_REVIEW_TAG,
        "-m",
        "test: wrong reviewed target",
        gate.ATTEMPT_013_PARENT_COMMIT,
    )
    failures = []
    gate._validate_attempt_013_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=commit,
        candidate_tree=tree,
        failures=failures,
    )
    assert (
        "O4 Attempt 013 annotated review tag does not peel to the exact candidate"
        in failures
    )

    _run_git(repo, "tag", "-d", gate.ATTEMPT_013_REVIEW_TAG)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "tag",
        "-a",
        gate.ATTEMPT_013_REVIEW_TAG,
        "-m",
        "test: restored exact reviewed target",
        commit,
    )
    failures = []
    gate._validate_attempt_013_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=commit,
        candidate_tree=tree,
        failures=failures,
    )
    assert failures == []


def test_attempt_010_tracked_disposition_is_closed_and_exact() -> None:
    disposition = json.loads(gate.ATTEMPT_010_DISPOSITION_JSON.read_text(encoding="utf-8"))
    failures: list[str] = []

    gate._validate_attempt_010_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_010_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []
    assert disposition["attempt_contract"]["execution_attempt_budget"] == 0
    assert disposition["attempt_contract"]["attempt_consumed"] is True
    assert disposition["authority"] == gate.CLOSED_AUTHORITY


def test_attempt_011_tracked_disposition_is_closed_and_exact() -> None:
    disposition = json.loads(gate.ATTEMPT_011_DISPOSITION_JSON.read_text(encoding="utf-8"))
    failures: list[str] = []

    gate._validate_attempt_011_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_011_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []
    assert disposition["normalized_fixed_node_start_diagnostic"] == {
        "collection_status": "complete",
        "classification": "fixed_node_runtime_state_inconsistent",
        "reason_code": "fixed_node_start_state_collected",
        "mission_lifecycle_state": "claimed",
        "delivery_state": "claim_delivered",
        "evidence_state": "complete",
        "root_cause_proven": False,
        "raw_container_id_recorded": False,
        "raw_output_recorded": False,
    }
    assert disposition["attempt_contract"]["execution_attempt_budget"] == 0
    assert disposition["attempt_contract"]["attempt_consumed"] is True
    assert disposition["authority"] == gate.CLOSED_AUTHORITY


def test_attempt_012_tracked_disposition_is_closed_private_and_exact() -> None:
    disposition = json.loads(gate.ATTEMPT_012_DISPOSITION_JSON.read_text(encoding="utf-8"))
    failures: list[str] = []

    gate._validate_attempt_012_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_012_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []
    assert disposition["attempt_contract"] == {
        "execution_attempt_budget": 0,
        "attempt_consumed": True,
        "retry_authorized": False,
        "automatic_retry_authorized": False,
        "recovery_authorized": False,
        "cleanup_authorized": False,
        "successor_attempt_authorized": False,
    }
    assert disposition["authority"] == gate.CLOSED_AUTHORITY
    invocation = disposition["invocation"]
    assert isinstance(invocation, dict)
    assert set(invocation) == {
        "make_exit_code",
        "producer_exit_code",
        "run_identity_sha256",
        "compose_project_identity_sha256",
        "raw_run_or_project_identity_recorded",
    }


def test_attempt_013_tracked_disposition_is_closed_private_and_exact() -> None:
    disposition = json.loads(gate.ATTEMPT_013_DISPOSITION_JSON.read_text(encoding="utf-8"))
    failures: list[str] = []

    gate._validate_attempt_013_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_013_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []
    assert disposition["attempt_contract"]["execution_attempt_budget"] == 0
    assert disposition["attempt_contract"]["attempt_consumed"] is True
    assert disposition["authority"] == gate.CLOSED_AUTHORITY
    assert disposition["normalized_fixed_node_start_diagnostic"][
        "fixed_bridge_last_entered_phase"
    ] == "not_reported"
    assert disposition["diagnostic_claims"]["root_cause_proven"] is False
    invocation = disposition["invocation"]
    assert isinstance(invocation, dict)
    assert invocation["raw_run_project_or_output_recorded"] is False


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "execution_attempt_budget",
            1,
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "producer_code_authorized",
            True,
        ),
        lambda value: value["diagnostic_claims"].__setitem__(  # type: ignore[union-attr]
            "root_cause_proven",
            True,
        ),
        lambda value: value["normalized_fixed_node_start_diagnostic"].__setitem__(  # type: ignore[union-attr]
            "fixed_bridge_last_entered_phase",
            "listener_accept_entered",
        ),
        lambda value: value["invocation"].__setitem__(  # type: ignore[union-attr]
            "raw_run_project_or_output_recorded",
            True,
        ),
        lambda value: value["retained_receipt_binding"]["entries"][1].__setitem__(  # type: ignore[index,union-attr]
            "sha256",
            "sha256:" + "0" * 64,
        ),
    ],
)
def test_attempt_013_disposition_rejects_authority_projection_or_receipt_drift(
    mutate: object,
) -> None:
    disposition = json.loads(gate.ATTEMPT_013_DISPOSITION_JSON.read_text(encoding="utf-8"))
    assert callable(mutate)
    mutate(disposition)
    failures: list[str] = []

    gate._validate_attempt_013_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_013_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures


@pytest.mark.parametrize("attempt", ["008", "010"])
def test_execution_authorization_document_rejects_present_tense_consumed_authority(
    attempt: str,
) -> None:
    document = gate.DOCUMENT.read_text(encoding="utf-8")
    historical = (
        f"At that Attempt {attempt} authorization point, exactly five bounded live authority "
        "fields were true"
    )
    stale = "Exactly five bounded live authority fields are true"
    assert historical in " ".join(document.split())
    pattern = r"\s+".join(re.escape(word) for word in historical.split())
    document, replacements = re.subn(pattern, stale, document, count=1)
    assert replacements == 1
    failures: list[str] = []

    gate._validate_document(document, failures)  # noqa: SLF001

    assert any(historical in failure for failure in failures)


def test_attempt_010_synthetic_receipts_are_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, _, _ = _synthetic_attempt_010_receipts(tmp_path, monkeypatch)
    failures: list[str] = []

    gate._validate_attempt_010_receipts(repo, failures)  # noqa: SLF001

    assert failures == []


@pytest.mark.parametrize(
    "mutation",
    [
        "root_mode",
        "diagnostic_mode",
        "diagnostic_size",
        "diagnostic_digest",
        "diagnostic_symlink",
        "disposition_mode",
        "disposition_size",
        "disposition_digest",
        "disposition_symlink",
        "extra_entry",
    ],
)
def test_attempt_010_synthetic_receipts_reject_metadata_or_content_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    repo, diagnostic, disposition, receipt_root = _synthetic_attempt_010_receipts(
        tmp_path,
        monkeypatch,
    )
    if mutation == "root_mode":
        receipt_root.chmod(0o755)
    elif mutation == "diagnostic_mode":
        diagnostic.chmod(0o644)
    elif mutation == "diagnostic_size":
        diagnostic.write_bytes(b"short")
        diagnostic.chmod(0o600)
    elif mutation == "diagnostic_digest":
        diagnostic.write_bytes(b"y" * gate.ATTEMPT_010_DIAGNOSTIC_SIZE)
        diagnostic.chmod(0o600)
    elif mutation == "diagnostic_symlink":
        diagnostic.unlink()
        diagnostic.symlink_to("disposition.json")
    elif mutation == "disposition_mode":
        disposition.chmod(0o644)
    elif mutation == "disposition_size":
        disposition.write_bytes(b"{}")
        disposition.chmod(0o600)
    elif mutation == "disposition_digest":
        disposition.write_bytes(b"x" * gate.ATTEMPT_010_DISPOSITION_SIZE)
        disposition.chmod(0o600)
    elif mutation == "disposition_symlink":
        disposition.unlink()
        disposition.symlink_to("diagnostic.json")
    else:
        extra = receipt_root / "unexpected.json"
        extra.write_text("{}\n", encoding="utf-8")
        extra.chmod(0o600)
    failures: list[str] = []

    gate._validate_attempt_010_receipts(repo, failures)  # noqa: SLF001

    assert failures


@pytest.mark.parametrize("present_root", ["runtime", "report"])
def test_attempt_010_synthetic_receipts_reject_exact_root_presence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    present_root: str,
) -> None:
    repo, _, _, _ = _synthetic_attempt_010_receipts(tmp_path, monkeypatch)
    relative = (
        gate.ATTEMPT_010_RUNTIME_ROOT
        if present_root == "runtime"
        else gate.ATTEMPT_010_REPORT_ROOT
    )
    (repo / relative).mkdir(parents=True)
    failures: list[str] = []

    gate._validate_attempt_010_receipts(repo, failures)  # noqa: SLF001

    label = "runtime" if present_root == "runtime" else "public report"
    assert any(f"O4 exact Attempt 010 {label} root is present" in item for item in failures)


def test_attempt_011_synthetic_receipts_are_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, _, _ = _synthetic_attempt_011_receipts(tmp_path, monkeypatch)
    failures: list[str] = []

    gate._validate_attempt_011_receipts(repo, failures)  # noqa: SLF001

    assert failures == []


@pytest.mark.parametrize(
    "mutation",
    [
        "root_mode",
        "diagnostic_digest",
        "disposition_digest",
        "disposition_symlink",
        "extra_entry",
    ],
)
def test_attempt_011_synthetic_receipts_reject_metadata_or_content_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    repo, diagnostic, disposition, receipt_root = _synthetic_attempt_011_receipts(
        tmp_path,
        monkeypatch,
    )
    if mutation == "root_mode":
        receipt_root.chmod(0o755)
    elif mutation == "diagnostic_digest":
        diagnostic.write_bytes(b"y" * gate.ATTEMPT_011_DIAGNOSTIC_SIZE)
        diagnostic.chmod(0o600)
    elif mutation == "disposition_digest":
        disposition.write_bytes(b"x" * gate.ATTEMPT_011_DISPOSITION_SIZE)
        disposition.chmod(0o600)
    elif mutation == "disposition_symlink":
        disposition.unlink()
        disposition.symlink_to("diagnostic.json")
    else:
        extra = receipt_root / "unexpected.json"
        extra.write_text("{}\n", encoding="utf-8")
        extra.chmod(0o600)
    failures: list[str] = []

    gate._validate_attempt_011_receipts(repo, failures)  # noqa: SLF001

    assert failures


@pytest.mark.parametrize("present_root", ["runtime", "report"])
def test_attempt_011_synthetic_receipts_reject_exact_run_root_presence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    present_root: str,
) -> None:
    repo, _, _, _ = _synthetic_attempt_011_receipts(tmp_path, monkeypatch)
    relative = {
        "runtime": gate.ATTEMPT_011_RUNTIME_ROOT,
        "report": gate.ATTEMPT_011_REPORT_ROOT,
    }[present_root]
    (repo / relative).mkdir(parents=True)
    failures: list[str] = []

    gate._validate_attempt_011_receipts(repo, failures)  # noqa: SLF001

    expected_label = {
        "runtime": "O4 exact Attempt 011 runtime root is present",
        "report": "O4 exact Attempt 011 public report root is present",
    }[present_root]
    assert any(expected_label in item for item in failures)


def test_attempt_012_private_digest_selects_exact_receipt_without_emitting_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, _, _, run_name, project_name = _synthetic_attempt_012_receipts(
        tmp_path,
        monkeypatch,
    )
    failures: list[str] = []

    gate._validate_attempt_012_receipts(repo, failures)  # noqa: SLF001

    assert failures == []
    rendered = gate.render_report(
        {
            "valid": False,
            "record_status": "closed",
            "attempt_id": gate.ATTEMPT_012_ID,
            "attempt_consumed": True,
            "retry_authorized": False,
            "execution_attempt_budget": 0,
            "next_action": "closed",
            "live_execution_authorized": False,
            "docker_lifecycle_authorized": False,
            "provider_access_authorized": False,
            "o4_evidence_execution_authorized": False,
            "new_governed_tool": False,
            "release_allowed": False,
            "uat_complete": False,
            "failures": ["O4 Attempt 012 private receipt selection failed"],
        }
    )
    assert run_name not in rendered
    assert project_name not in rendered


@pytest.mark.parametrize(
    "mutation",
    [
        "root_mode",
        "diagnostic_digest",
        "diagnostic_symlink",
        "disposition_digest",
        "extra_entry",
        "no_matching_digest",
    ],
)
def test_attempt_012_private_receipt_binding_fails_closed_without_identity_leak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    repo, diagnostic, disposition, receipt_root, run_name, project_name = (
        _synthetic_attempt_012_receipts(tmp_path, monkeypatch)
    )
    if mutation == "root_mode":
        receipt_root.chmod(0o755)
    elif mutation == "diagnostic_digest":
        diagnostic.write_bytes(b"changed")
        diagnostic.chmod(0o600)
    elif mutation == "diagnostic_symlink":
        diagnostic.unlink()
        diagnostic.symlink_to("disposition.json")
    elif mutation == "disposition_digest":
        disposition.write_bytes(b"x" * gate.ATTEMPT_012_DISPOSITION_SIZE)
        disposition.chmod(0o600)
    elif mutation == "extra_entry":
        extra = receipt_root / "unexpected.json"
        extra.write_text("{}\n", encoding="utf-8")
        extra.chmod(0o600)
    else:
        monkeypatch.setattr(
            gate,
            "ATTEMPT_012_RUN_IDENTITY_DIGEST",
            "sha256:" + "0" * 64,
        )
    failures: list[str] = []

    gate._validate_attempt_012_receipts(repo, failures)  # noqa: SLF001

    assert failures
    failure_text = "\n".join(failures)
    assert run_name not in failure_text
    assert project_name not in failure_text


def test_attempt_012_private_receipt_selection_rejects_multiple_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, _, _, run_name, project_name = _synthetic_attempt_012_receipts(
        tmp_path,
        monkeypatch,
    )
    second_name = "20260726T120001Z-012abcdf"
    second_root = repo / gate.ATTEMPT_002_RECEIPT_BASE / second_name
    second_root.mkdir(mode=0o700)
    original_digest = gate._domain_identity_digest  # noqa: SLF001

    def collide_for_test(prefix: str, value: str) -> str:
        if prefix == gate.ATTEMPT_012_RUN_DIGEST_PREFIX:
            return gate.ATTEMPT_012_RUN_IDENTITY_DIGEST
        return original_digest(prefix, value)

    monkeypatch.setattr(gate, "_domain_identity_digest", collide_for_test)
    failures: list[str] = []

    gate._validate_attempt_012_receipts(repo, failures)  # noqa: SLF001

    assert (
        "O4 Attempt 012 private receipt selection did not resolve exactly one root"
        in failures
    )
    failure_text = "\n".join(failures)
    assert run_name not in failure_text
    assert second_name not in failure_text
    assert project_name not in failure_text


def test_attempt_013_private_digest_selects_exact_receipt_without_emitting_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, _, _, run_name, project_name = _synthetic_attempt_013_receipts(
        tmp_path,
        monkeypatch,
    )
    failures: list[str] = []

    gate._validate_attempt_013_receipts(repo, failures)  # noqa: SLF001

    assert failures == []
    assert run_name not in "\n".join(failures)
    assert project_name not in "\n".join(failures)


def test_attempt_013_private_receipt_rejects_phase_projection_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, diagnostic, _, _, run_name, project_name = _synthetic_attempt_013_receipts(
        tmp_path,
        monkeypatch,
    )
    document = json.loads(diagnostic.read_text(encoding="utf-8"))
    document["fixed_node_start_diagnostic"]["fixed_bridge_last_entered_phase"] = (
        "listener_accept_entered"
    )
    diagnostic_bytes = (
        json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    diagnostic.write_bytes(diagnostic_bytes)
    diagnostic.chmod(0o600)
    monkeypatch.setattr(gate, "ATTEMPT_013_DIAGNOSTIC_SIZE", len(diagnostic_bytes))
    monkeypatch.setattr(
        gate,
        "ATTEMPT_013_DIAGNOSTIC_RECEIPT_DIGEST",
        "sha256:" + hashlib.sha256(diagnostic_bytes).hexdigest(),
    )
    failures: list[str] = []

    gate._validate_attempt_013_receipts(repo, failures)  # noqa: SLF001

    assert "O4 Attempt 013 fixed-Node diagnostic projection is not exact" in failures
    failure_text = "\n".join(failures)
    assert run_name not in failure_text
    assert project_name not in failure_text


def test_attempt_010_assert_live_always_refuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gate,
        "build_report",
        lambda _repo: {
            "valid": True,
            "live_execution_authorized": False,
            "execution_attempt_budget": 0,
            "execution_checkout_commit": "a" * 40,
            "execution_checkout_tree": "b" * 40,
        },
    )

    with pytest.raises(
        gate.O4ExecutionAuthorizationError,
        match="o4_live_execution_not_authorized",
    ):
        gate.assert_live_execution_authorized(
            ROOT,
            candidate_commit="a" * 40,
            candidate_tree="b" * 40,
        )


def test_mcc_reconciliation_review_and_attempt008_recovery_bindings_are_exact() -> None:
    failures: list[str] = []

    gate._validate_mcc_reconciliation_review(  # noqa: SLF001
        ROOT,
        gate.MCC_AUTHORIZATION_INDEX_RECONCILIATION_REVIEW.read_text(encoding="utf-8"),
        failures,
    )
    gate._validate_attempt008_recovery_closure_binding(ROOT, failures)  # noqa: SLF001

    assert failures == []


def test_tampered_mcc_reconciliation_review_is_rejected() -> None:
    failures: list[str] = []
    document = gate.MCC_AUTHORIZATION_INDEX_RECONCILIATION_REVIEW.read_text(encoding="utf-8")

    gate._validate_mcc_reconciliation_review(  # noqa: SLF001
        ROOT,
        document.replace("GO_CODE_ONLY", "NO_GO", 1),
        failures,
    )

    assert "O4 MCC reconciliation review digest is invalid" in failures


def test_attempt_010_review_tag_is_required_and_exact(tmp_path: Path) -> None:
    repo, closure_commit, _ = _attempt_010_control_child_repository(tmp_path)
    failures: list[str] = []

    gate._validate_attempt_010_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=gate.ATTEMPT_010_CANDIDATE_COMMIT,
        candidate_tree=gate.ATTEMPT_010_CANDIDATE_TREE,
        failures=failures,
    )
    assert failures == []

    _run_git(repo, "tag", "-f", gate.ATTEMPT_010_REVIEW_TAG, closure_commit)
    failures = []
    gate._validate_attempt_010_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=gate.ATTEMPT_010_CANDIDATE_COMMIT,
        candidate_tree=gate.ATTEMPT_010_CANDIDATE_TREE,
        failures=failures,
    )
    assert "O4 Attempt 010 independent review tag is not exact" in failures

    _run_git(
        repo,
        "tag",
        "-f",
        gate.ATTEMPT_010_REVIEW_TAG,
        gate.ATTEMPT_010_CANDIDATE_COMMIT,
    )
    failures = []
    gate._validate_attempt_010_review_binding(  # noqa: SLF001
        repo,
        candidate_commit=gate.ATTEMPT_010_CANDIDATE_COMMIT,
        candidate_tree=gate.ATTEMPT_010_CANDIDATE_TREE,
        failures=failures,
    )
    assert failures == []


def test_attempt_009_rejects_node_cli_repair_path_drift(tmp_path: Path) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    node_cli = repo / "apps/node/src/ithildin_node/__main__.py"
    node_cli.write_text(
        node_cli.read_text(encoding="utf-8") + "\n# forbidden repair drift\n",
        encoding="utf-8",
    )

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert any(
        "O4 enrollment-output projection repair differs for "
        "apps/node/src/ithildin_node/__main__.py" in failure
        for failure in report["failures"]
    )
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False


def test_real_retained_attempt_evidence_through_attempt_017_is_exact() -> None:
    failures: list[str] = []

    gate._validate_retained_attempt_evidence(ROOT, failures)  # noqa: SLF001

    assert failures == []


def test_real_attempt_016_private_receipts_are_exact() -> None:
    failures: list[str] = []

    gate._validate_attempt_016_receipts(ROOT, failures)  # noqa: SLF001

    assert failures == []


def test_attempt_016_closure_repair_checkout_is_exact() -> None:
    failures: list[str] = []

    checkout = gate._validate_execution_checkout(  # noqa: SLF001
        ROOT,
        failures,
        candidate_parent_commit=gate.ATTEMPT_016_CLOSURE_COMMIT,
        candidate_parent_tree=gate.ATTEMPT_016_CLOSURE_TREE,
        reviewed_commit=gate.ATTEMPT_016_CANDIDATE_COMMIT,
        runtime_paths=gate.ATTEMPT_016_RUNTIME_PATHS,
        control_paths=gate.ATTEMPT_016_CLOSURE_REPAIR_CONTROL_PATH_ALLOWLIST,
        candidate_ref=gate.ATTEMPT_016_CLOSURE_REPAIR_COMMIT,
        require_clean_worktree=False,
    )

    assert failures == []
    assert checkout == (
        gate.ATTEMPT_016_CLOSURE_REPAIR_COMMIT,
        gate.ATTEMPT_016_CLOSURE_REPAIR_TREE,
    )


def test_attempt_017_closure_checkout_is_exact() -> None:
    failures: list[str] = []

    checkout = gate._validate_execution_checkout(  # noqa: SLF001
        ROOT,
        failures,
        candidate_parent_commit=gate.ATTEMPT_017_CANDIDATE_COMMIT,
        candidate_parent_tree=gate.ATTEMPT_017_CANDIDATE_TREE,
        reviewed_commit=gate.ATTEMPT_017_CANDIDATE_COMMIT,
        runtime_paths=gate.ATTEMPT_017_RUNTIME_PATHS,
        control_paths=gate.ATTEMPT_017_CLOSURE_CONTROL_PATH_ALLOWLIST,
        candidate_ref=gate.ATTEMPT_017_CLOSURE_COMMIT,
        require_clean_worktree=False,
    )

    assert failures == []
    assert checkout == (
        gate.ATTEMPT_017_CLOSURE_COMMIT,
        gate.ATTEMPT_017_CLOSURE_TREE,
    )


def test_attempt_009_disposition_is_closed_and_exact() -> None:
    disposition = json.loads(gate.ATTEMPT_009_DISPOSITION_JSON.read_text(encoding="utf-8"))
    failures: list[str] = []

    gate._validate_attempt_009_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_009_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []
    assert disposition["attempt_contract"]["execution_attempt_budget"] == 0
    assert disposition["attempt_contract"]["attempt_consumed"] is True
    assert disposition["authority"] == gate.CLOSED_AUTHORITY


def test_attempt_009_retained_diagnostic_rejects_drift(tmp_path: Path) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    diagnostic = repo / gate.ATTEMPT_009_RECEIPT_ROOT / "diagnostic.json"
    diagnostic.write_bytes(b"x" * gate.ATTEMPT_009_DIAGNOSTIC_SIZE)
    diagnostic.chmod(0o600)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert any("O4 Attempt 009 failure diagnostic" in failure for failure in report["failures"])
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False


def test_attempt_009_exact_runtime_root_presence_is_rejected(tmp_path: Path) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    (repo / gate.ATTEMPT_009_RUNTIME_ROOT).mkdir(mode=0o700)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert any(
        "O4 exact Attempt 009 runtime root is present" in failure
        for failure in report["failures"]
    )
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False


def test_additional_retained_attempt_run_refuses_attempt_004(
    tmp_path: Path,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    receipt_base = repo / gate.ATTEMPT_002_RECEIPT_BASE
    (receipt_base / "unknown-attempt").mkdir(mode=0o700)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert any("receipt base entries are not exact" in failure for failure in report["failures"])
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False


@pytest.mark.parametrize(
    "mutation",
    ["tampered", "symlink", "special", "extra_child"],
)
def test_attempt_003_retained_receipt_rejects_tamper_symlink_or_special(
    tmp_path: Path,
    mutation: str,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    receipt_root = repo / gate.ATTEMPT_003_RECEIPT_ROOT
    disposition = receipt_root / "disposition.json"
    if mutation == "tampered":
        disposition.write_bytes(b"x" * len(gate.ATTEMPT_003_DISPOSITION_BYTES))
        disposition.chmod(0o600)
    elif mutation == "symlink":
        disposition.unlink()
        external = tmp_path / "external-disposition.json"
        external.write_bytes(gate.ATTEMPT_003_DISPOSITION_BYTES)
        disposition.symlink_to(external)
    elif mutation == "special":
        disposition.unlink()
        os.mkfifo(disposition, 0o600)
    else:
        extra = receipt_root / "unknown.json"
        extra.write_text("{}\n", encoding="utf-8")
        extra.chmod(0o600)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False


@pytest.mark.parametrize(
    "mutation",
    ["missing", "tampered", "symlink", "special", "extra_child"],
)
def test_attempt_004_diagnostic_rejects_any_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    receipt_root = repo / gate.ATTEMPT_004_RECEIPT_ROOT
    diagnostic = receipt_root / "diagnostic.json"
    if mutation == "missing":
        diagnostic.unlink()
    elif mutation == "tampered":
        diagnostic.write_bytes(b"x" * gate.ATTEMPT_004_DIAGNOSTIC_SIZE)
        diagnostic.chmod(0o600)
    elif mutation == "symlink":
        diagnostic.unlink()
        external = tmp_path / "external-diagnostic.json"
        external.write_bytes(b"x" * gate.ATTEMPT_004_DIAGNOSTIC_SIZE)
        diagnostic.symlink_to(external)
    elif mutation == "special":
        diagnostic.unlink()
        os.mkfifo(diagnostic, 0o600)
    else:
        extra = receipt_root / "unknown.json"
        extra.write_text("{}\n", encoding="utf-8")
        extra.chmod(0o600)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False


def test_attempt_007_retained_receipt_rejects_missing_marker_drift(
    tmp_path: Path,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    diagnostic = repo / gate.ATTEMPT_007_RECEIPT_ROOT / "diagnostic.json"
    contents = diagnostic.read_bytes()
    assert b"application_startup_stage_missing" in contents
    diagnostic.write_bytes(
        contents.replace(
            b"application_startup_stage_missing",
            b"application_startup_stage_present",
            1,
        )
    )
    diagnostic.chmod(0o600)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert any("O4 Attempt 007 failure diagnostic" in failure for failure in report["failures"])
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False


@pytest.mark.parametrize(
    "mutation",
    ["missing", "tampered", "chmod", "symlink", "special", "extra"],
)
def test_recovery_consumption_receipt_rejects_any_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    receipt = repo / gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT
    runtime_base = receipt.parent
    if mutation == "missing":
        receipt.unlink()
    elif mutation == "tampered":
        receipt.write_bytes(b"x" * len(gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES))
        receipt.chmod(0o600)
    elif mutation == "chmod":
        receipt.chmod(0o644)
    elif mutation == "symlink":
        receipt.unlink()
        external = tmp_path / "external-recovery-receipt.json"
        external.write_bytes(gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES)
        receipt.symlink_to(external)
    elif mutation == "special":
        receipt.unlink()
        os.mkfifo(receipt, 0o600)
    else:
        (runtime_base / "unknown").write_text("x\n", encoding="utf-8")

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False


@pytest.mark.parametrize(
    "posture",
    ["empty_base", "unknown_file", "unknown_directory", "symlinked_base"],
)
def test_unbound_report_base_posture_refuses_consumed_success_closure(
    tmp_path: Path,
    posture: str,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    report_base = repo / gate.ATTEMPT_002_REPORT_BASE
    if posture == "symlinked_base":
        external = tmp_path / "external-report-base"
        external.mkdir()
        report_base.symlink_to(external, target_is_directory=True)
    else:
        report_base.mkdir(parents=True)
        if posture == "unknown_file":
            (report_base / "unknown-report.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
        elif posture == "unknown_directory":
            (report_base / "unknown-run").mkdir()

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert any(
        "O4 Attempt 021 report" in failure for failure in report["failures"]
    )
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False


def test_invalid_retained_evidence_never_reopens_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_retained_evidence(_: Path, failures: list[str]) -> None:
        failures.append("retained evidence rejected for test")

    monkeypatch.setattr(
        gate,
        "_validate_retained_attempt_evidence",
        reject_retained_evidence,
    )

    report = gate.build_report(ROOT)

    assert report["valid"] is False
    assert "retained evidence rejected for test" in report["failures"]
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False
    assert report["release_allowed"] is False
    assert report["uat_complete"] is False


def test_live_gate_refuses_consumed_attempt_002() -> None:
    with pytest.raises(
        gate.O4ExecutionAuthorizationError,
        match="o4_live_execution_not_authorized",
    ):
        gate.assert_live_execution_authorized(
            ROOT,
            candidate_commit=gate.ATTEMPT_002_CANDIDATE_COMMIT,
            candidate_tree=gate.ATTEMPT_002_CANDIDATE_TREE,
        )


@pytest.mark.parametrize(
    ("mutate", "failure_fragment"),
    [
        (
            lambda value: value.__setitem__("execution_candidate_commit", "a" * 40),
            "fields are not closed",
        ),
        (
            lambda value: value.__setitem__("execution_attempt_budget", 2),
            "execution_attempt_budget",
        ),
        (
            lambda value: value.__setitem__("execution_attempt_budget", True),
            "execution_attempt_budget",
        ),
        (
            lambda value: value.__setitem__("record_status", "AUTHORIZED_EXACT_CANDIDATE"),
            "record_status",
        ),
        (
            lambda value: value.__setitem__("candidate_parent_commit", "a" * 40),
            "candidate_parent_commit",
        ),
        (
            lambda value: value.__setitem__(
                "historical_post_review_candidate_parent_commit", "a" * 40
            ),
            "historical_post_review_candidate_parent_commit",
        ),
        (
            lambda value: value.__setitem__("attempt_001_attempted_candidate_commit", "a" * 40),
            "attempt_001_attempted_candidate_commit",
        ),
        (
            lambda value: value["attempt_001_invocation"].__setitem__(  # type: ignore[union-attr]
                "command", "python scripts/local_v1_lv1_003_o4_producer.py"
            ),
            "attempt_001_invocation",
        ),
        (
            lambda value: value["attempt_001_invocation"].__setitem__(  # type: ignore[union-attr]
                "classification", "SUCCESS"
            ),
            "attempt_001_invocation",
        ),
        (
            lambda value: value["attempt_001_root_absence"]["absent_roots"].pop(),  # type: ignore[index,union-attr]
            "attempt_001_root_absence",
        ),
        (
            lambda value: value.__setitem__("attempt_consumed", False),
            "attempt_consumed",
        ),
        (
            lambda value: value.__setitem__(
                "fixed_node_state_projection_review_sha256",
                "sha256:" + "0" * 64,
            ),
            "fixed_node_state_projection_review_sha256",
        ),
        (
            lambda value: value["fixed_node_state_projection_path_digests"].__setitem__(  # type: ignore[union-attr]
                "scripts/local_v1_lv1_003_o4_producer.py",
                "sha256:" + "0" * 64,
            ),
            "fixed_node_state_projection_path_digests",
        ),
        (
            lambda value: value.__setitem__("attempt_012_execution_authorized", True),
            "attempt_012_execution_authorized",
        ),
        (
            lambda value: value.__setitem__("attempt_012_automatic_retry_authorized", True),
            "attempt_012_automatic_retry_authorized",
        ),
        (
            lambda value: value.__setitem__("attempt_012_review_tag", "moved-tag"),
            "attempt_012_review_tag",
        ),
        (
            lambda value: value.__setitem__("attempt_012_attempt_consumed", False),
            "attempt_012_attempt_consumed",
        ),
        (
            lambda value: value.__setitem__("attempt_012_execution_attempt_budget", 1),
            "attempt_012_execution_attempt_budget",
        ),
        (
            lambda value: value["attempt_012_authority"].__setitem__(  # type: ignore[union-attr]
                "producer_code_authorized",
                True,
            ),
            "attempt_012_authority",
        ),
        (
            lambda value: value.__setitem__(
                "fixed_bridge_phase_diagnostic_review_sha256",
                "sha256:" + "0" * 64,
            ),
            "fixed_bridge_phase_diagnostic_review_sha256",
        ),
        (
            lambda value: value["fixed_bridge_phase_diagnostic_path_digests"].__setitem__(  # type: ignore[union-attr]
                "apps/node/src/ithildin_node/fixed_runner_bridge.py",
                "sha256:" + "0" * 64,
            ),
            "fixed_bridge_phase_diagnostic_path_digests",
        ),
        (
            lambda value: value["fixed_node_state_projection_contract"]["retained_keys"].pop(),  # type: ignore[index,union-attr]
            "fixed_node_state_projection_contract",
        ),
        (
            lambda value: value["fixed_node_state_projection_contract"][  # type: ignore[index]
                "fixed_bridge_last_entered_phase_values"
            ].append("raw_exit_88"),  # type: ignore[union-attr]
            "fixed_node_state_projection_contract",
        ),
        (
            lambda value: value["fixed_node_state_projection_contract"].__setitem__(  # type: ignore[union-attr]
                "raw_exit_identity_or_output_retained",
                True,
            ),
            "fixed_node_state_projection_contract",
        ),
        (
            lambda value: value.__setitem__("attempt_013_execution_authorized", False),
            "attempt_013_execution_authorized",
        ),
        (
            lambda value: value.__setitem__("attempt_013_automatic_retry_authorized", True),
            "attempt_013_automatic_retry_authorized",
        ),
        (
            lambda value: value.__setitem__("attempt_013_review_tag", "moved-tag"),
            "attempt_013_review_tag",
        ),
        (
            lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
                "producer_code_authorized",
                True,
            ),
            "authority",
        ),
        (
            lambda value: value.__setitem__("attempt_004_execution_authorized", True),
            "attempt_004_execution_authorized",
        ),
        (
            lambda value: value.__setitem__(
                "image_recovery_closure_json_sha256", "sha256:" + "0" * 64
            ),
            "image_recovery_closure_json_sha256",
        ),
        (
            lambda value: value.__setitem__(
                "runtime_native_repair_review_sha256", "sha256:" + "0" * 64
            ),
            "runtime_native_repair_review_sha256",
        ),
        (
            lambda value: value.__setitem__(
                "execution_candidate_binding_mode", "none_attempt_closed"
            ),
            "execution_candidate_binding_mode",
        ),
        (
            lambda value: value.__setitem__(
                "enrollment_output_projection_repair_review_sha256",
                "sha256:" + "0" * 64,
            ),
            "enrollment_output_projection_repair_review_sha256",
        ),
        (
            lambda value: value["enrollment_output_projection_repair_path_digests"].__setitem__(  # type: ignore[union-attr]
                "tests/test_node_cli.py", "sha256:" + "0" * 64
            ),
            "enrollment_output_projection_repair_path_digests",
        ),
        (
            lambda value: value["enrollment_output_projection_contract"].__setitem__(  # type: ignore[union-attr]
                "field_names",
                ["node_id", "principal_id", "workspace_id", "registered"],
            ),
            "enrollment_output_projection_contract",
        ),
        (
            lambda value: value.__setitem__("attempt_009_execution_authorized", True),
            "attempt_009_execution_authorized",
        ),
        (
            lambda value: value.__setitem__("retry_authorized", True),
            "retry_authorized",
        ),
        (
            lambda value: value.__setitem__("attempt_002_candidate_parent_commit", "a" * 40),
            "attempt_002_candidate_parent_commit",
        ),
        (
            lambda value: value.__setitem__(
                "attempt_002_operator_command", gate.FAILED_FILE_PATH_INVOCATION
            ),
            "attempt_002_operator_command",
        ),
        (
            lambda value: value.__setitem__(
                "attempt_002_module_command", gate.FAILED_FILE_PATH_INVOCATION
            ),
            "attempt_002_module_command",
        ),
        (
            lambda value: value.__setitem__(
                "entrypoint_repair_review_sha256", "sha256:" + "0" * 64
            ),
            "entrypoint_repair_review_sha256",
        ),
        (
            lambda value: value.__setitem__(
                "attempt_002_disposition_json_sha256", "sha256:" + "0" * 64
            ),
            "attempt_002_disposition_json_sha256",
        ),
        (
            lambda value: value.__setitem__("attempt_002_execution_authorized", True),
            "attempt_002_execution_authorized",
        ),
        (
            lambda value: value["producer_entrypoint_repair"].__setitem__(  # type: ignore[union-attr]
                "module_invocation", gate.FAILED_FILE_PATH_INVOCATION
            ),
            "producer_entrypoint_repair",
        ),
        (
            lambda value: value["producer_entrypoint_repair"].__setitem__(  # type: ignore[union-attr]
                "failed_file_path_invocation_authorized", True
            ),
            "producer_entrypoint_repair",
        ),
        (
            lambda value: value["profile"].__setitem__(  # type: ignore[union-attr]
                "provider_model", "different-model"
            ),
            "profile binding",
        ),
        (
            lambda value: value["profile"].__setitem__(  # type: ignore[union-attr]
                "unexpected", False
            ),
            "profile binding",
        ),
        (
            lambda value: value["profile"]["hermes_platform_digests"].__setitem__(  # type: ignore[index,union-attr]
                "linux/ppc64le", "sha256:" + "0" * 64
            ),
            "profile binding",
        ),
        (
            lambda value: value["command_contract"]["fixed_actions"].append(  # type: ignore[index,union-attr]
                "arbitrary_exec"
            ),
            "command contract",
        ),
        (
            lambda value: value["command_contract"]["dynamic_values"].append(  # type: ignore[index,union-attr]
                "unbounded"
            ),
            "command contract",
        ),
        (
            lambda value: value["command_contract"].__setitem__(  # type: ignore[union-attr]
                "absent_image_id_probe_stdout_allowlist", [""]
            ),
            "command contract",
        ),
        (
            lambda value: value["command_contract"]["base_service_start_diagnostic"][  # type: ignore[index,union-attr]
                "compose_arguments"
            ].append("--environment"),  # type: ignore[union-attr]
            "command contract",
        ),
        (
            lambda value: value["command_contract"]["base_service_start_diagnostic"].__setitem__(  # type: ignore[index,union-attr]
                "raw_output_persisted", True
            ),
            "command contract",
        ),
        (
            lambda value: value["command_contract"].__setitem__(  # type: ignore[union-attr]
                "unexpected", False
            ),
            "command contract",
        ),
        (
            lambda value: value.__setitem__("external_preflight_requirements", []),
            "external_preflight_requirements",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "hermes_execution_attempts_maximum", 2
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "mission_count", True
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "gateway_agent_run_record_status", "completed"
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "gateway_completed_timeline_event_count", 1
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "hermes_stdout_destination", "PIPE"
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "current_assembler_usable_for_live_producer", False
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"]["bounded_image_metadata_fields"].append(
                "sbom_digest"
            ),  # type: ignore[index,union-attr]
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"][
                "current_tracked_license_inventory_inputs"
            ].append("requirements.txt"),  # type: ignore[index,union-attr]
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "transient_malicious_same_uid_mutation_during_docker_context_read_proven_absent",
                True,
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "unexpected", False
            ),
            "evidence contract",
        ),
        (
            lambda value: value["cleanup_contract"].__setitem__(  # type: ignore[union-attr]
                "runtime_plaintext_absent_required", False
            ),
            "cleanup contract",
        ),
        (
            lambda value: value["cleanup_contract"].__setitem__(  # type: ignore[union-attr]
                "chmod_only_publication_rollback_success_allowed", True
            ),
            "cleanup contract",
        ),
        (
            lambda value: value["cleanup_contract"].__setitem__(  # type: ignore[union-attr]
                "confirmed_node_revocation_required_before_destructive_cleanup",
                False,
            ),
            "cleanup contract",
        ),
        (
            lambda value: value["cleanup_contract"].__setitem__(  # type: ignore[union-attr]
                "unexpected", True
            ),
            "cleanup contract",
        ),
        (
            lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
                "docker_lifecycle_authorized", True
            ),
            "authority is not the exact bounded Attempt 021 posture",
        ),
        (
            lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
                "producer_code_authorized", True
            ),
            "authority is not the exact bounded Attempt 021 posture",
        ),
        (
            lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
                "shell_execution_authorized", True
            ),
            "authority is not the exact bounded Attempt 021 posture",
        ),
        (
            lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
                "release_allowed", 0
            ),
            "authority is not the exact bounded Attempt 021 posture",
        ),
        (
            lambda value: value.__setitem__("unexpected", False),
            "fields are not closed",
        ),
    ],
)
def test_supervised_attempt_contract_rejects_authority_or_scope_drift(
    mutate: object,
    failure_fragment: str,
) -> None:
    contract = copy.deepcopy(_contract())
    before = copy.deepcopy(contract)
    assert callable(mutate)
    mutate(contract)
    assert json.dumps(contract, sort_keys=True) != json.dumps(before, sort_keys=True)
    failures: list[str] = []

    gate._validate_contract(contract, failures)  # type: ignore[arg-type] # noqa: SLF001

    assert any(failure_fragment in failure for failure in failures)


@pytest.mark.parametrize(
    ("legacy_field", "explicit_field"),
    [
        ("attempt_disposition_json", "attempt_001_disposition_json"),
        ("attempt_disposition_json_sha256", "attempt_001_disposition_json_sha256"),
        ("attempt_disposition_document", "attempt_001_disposition_document"),
        (
            "attempt_disposition_document_sha256",
            "attempt_001_disposition_document_sha256",
        ),
        ("attempt_id", "attempt_001_id"),
        ("attempted_candidate_commit", "attempt_001_attempted_candidate_commit"),
        ("attempted_candidate_tree", "attempt_001_attempted_candidate_tree"),
        (
            "attempted_authorization_contract_sha256",
            "attempt_001_attempted_authorization_contract_sha256",
        ),
        ("attempt_invocation", "attempt_001_invocation"),
        ("attempt_root_absence", "attempt_001_root_absence"),
    ],
)
def test_contract_rejects_ambiguous_legacy_attempt_001_top_level_fields(
    legacy_field: str,
    explicit_field: str,
) -> None:
    contract = copy.deepcopy(_contract())
    contract[legacy_field] = copy.deepcopy(contract[explicit_field])
    failures: list[str] = []

    gate._validate_contract(contract, failures)  # type: ignore[arg-type] # noqa: SLF001

    assert "O4 execution authorization fields are not closed" in failures


def test_authorization_json_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version":"1","schema_version":"2"}\n', encoding="utf-8")
    failures: list[str] = []

    result = gate._read_contract(path, failures)  # noqa: SLF001

    assert result == {}
    assert failures == ["O4 execution authorization JSON is unavailable or ambiguous"]


def test_disposition_rejects_static_child_self_reference() -> None:
    disposition = json.loads(gate.DISPOSITION_JSON.read_text(encoding="utf-8"))
    disposition["execution_candidate_commit"] = "a" * 40
    failures: list[str] = []

    gate._validate_disposition(  # noqa: SLF001
        disposition,
        gate.DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 post-review disposition is not closed and exact" in failures


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "maximum_supervised_invocations", True
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "producer_code_authorized", 1
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "release_allowed", 0
        ),
    ],
)
def test_disposition_rejects_bool_int_type_substitution(mutate: object) -> None:
    disposition = json.loads(gate.DISPOSITION_JSON.read_text(encoding="utf-8"))
    assert callable(mutate)
    mutate(disposition)
    failures: list[str] = []

    gate._validate_disposition(  # noqa: SLF001
        disposition,
        gate.DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 post-review disposition is not closed and exact" in failures


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.__setitem__("attempted_candidate_commit", "a" * 40),
        lambda value: value["invocation"].__setitem__(  # type: ignore[union-attr]
            "command", "uv run python wrong.py"
        ),
        lambda value: value["invocation"].__setitem__(  # type: ignore[union-attr]
            "classification", "SUCCESS"
        ),
        lambda value: value["invocation"].__setitem__(  # type: ignore[union-attr]
            "exit_code", 0
        ),
        lambda value: value["observed_root_absence"]["roots"][0].__setitem__(  # type: ignore[index,union-attr]
            "exists", True
        ),
        lambda value: value["external_action_observation"].__setitem__(  # type: ignore[union-attr]
            "docker_action_performed", True
        ),
        lambda value: value["external_action_observation"].__setitem__(  # type: ignore[union-attr]
            "runtime_created", True
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "attempt_consumed", False
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "retry_authorized", True
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "o4_evidence_execution_authorized", True
        ),
        lambda value: value.__setitem__("closure_commit", "b" * 40),
    ],
)
def test_attempt_001_disposition_rejects_false_or_expansive_claims(
    mutate: object,
) -> None:
    disposition = json.loads(gate.ATTEMPT_001_DISPOSITION_JSON.read_text(encoding="utf-8"))
    assert callable(mutate)
    mutate(disposition)
    failures: list[str] = []

    gate._validate_attempt_001_disposition(  # noqa: SLF001
        disposition,
        gate.ATTEMPT_001_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 Attempt 001 disposition is not closed and exact" in failures


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.__setitem__("candidate_parent_commit", "a" * 40),
        lambda value: value.__setitem__("operator_command", gate.FAILED_FILE_PATH_INVOCATION),
        lambda value: value.__setitem__("module_command", gate.FAILED_FILE_PATH_INVOCATION),
        lambda value: value.__setitem__("failed_file_path_command_authorized", True),
        lambda value: value["attempt_001_history"].__setitem__(  # type: ignore[union-attr]
            "disposition_json_sha256", "sha256:" + "0" * 64
        ),
        lambda value: value["attempt_001_history"].__setitem__(  # type: ignore[union-attr]
            "consumed", False
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "maximum_supervised_invocations", 2
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "maximum_supervised_invocations", True
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "producer_code_authorized", False
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "shell_execution_authorized", True
        ),
        lambda value: value.__setitem__("execution_candidate_commit", "b" * 40),
    ],
)
def test_attempt_002_disposition_rejects_lineage_command_history_or_authority_drift(
    mutate: object,
) -> None:
    disposition = json.loads(gate.ATTEMPT_002_DISPOSITION_JSON.read_text(encoding="utf-8"))
    assert callable(mutate)
    mutate(disposition)
    failures: list[str] = []

    gate._validate_attempt_002_disposition(  # noqa: SLF001
        disposition,
        gate.ATTEMPT_002_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 Attempt 002 disposition is not closed and exact" in failures


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.__setitem__("record_status", "SUCCESS"),
        lambda value: value.__setitem__("attempted_candidate_commit", "a" * 40),
        lambda value: value.__setitem__("operator_command", gate.PRODUCER_MODULE_INVOCATION),
        lambda value: value.__setitem__("failure_code", "success"),
        lambda value: value["read_only_residue_observation"].__setitem__(  # type: ignore[union-attr]
            "cleanup_completed_claimed", True
        ),
        lambda value: value["read_only_residue_observation"].__setitem__(  # type: ignore[union-attr]
            "general_docker_absence_claimed", True
        ),
        lambda value: value["read_only_residue_observation"].__setitem__(  # type: ignore[union-attr]
            "exact_project_label_containers", 1
        ),
        lambda value: value["external_action_observation"].__setitem__(  # type: ignore[union-attr]
            "docker_mutation_performed", True
        ),
        lambda value: value["external_action_observation"].__setitem__(  # type: ignore[union-attr]
            "successful_evidence_created", True
        ),
        lambda value: value["retained_receipt"].__setitem__(  # type: ignore[union-attr]
            "candidate_manifest_sha256", "sha256:" + "0" * 64
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "attempt_consumed", False
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "retry_authorized", True
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "docker_lifecycle_authorized", True
        ),
    ],
)
def test_attempt_002_closure_rejects_false_or_expansive_claims(
    mutate: object,
) -> None:
    closure = json.loads(gate.ATTEMPT_002_CLOSURE_JSON.read_text(encoding="utf-8"))
    assert callable(mutate)
    mutate(closure)
    failures: list[str] = []

    gate._validate_attempt_002_closure(  # noqa: SLF001
        closure,
        gate.ATTEMPT_002_CLOSURE_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 Attempt 002 closure is not closed and exact" in failures


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.__setitem__("candidate_parent_commit", "a" * 40),
        lambda value: value.__setitem__("compose_repair_review_sha256", "sha256:" + "0" * 64),
        lambda value: value["repaired_source_digests"].__setitem__(  # type: ignore[union-attr]
            "overlay_compose_sha256", "sha256:" + "0" * 64
        ),
        lambda value: value["attempt_002_history"].__setitem__(  # type: ignore[union-attr]
            "consumed", False
        ),
        lambda value: value["control_path_allowlist"].pop(),  # type: ignore[union-attr]
        lambda value: value["prior_attempt_evidence_contract"].__setitem__(  # type: ignore[union-attr]
            "attempt_002_retained_evidence_required", False
        ),
        lambda value: value["prior_attempt_evidence_contract"].__setitem__(  # type: ignore[union-attr]
            "unknown_or_additional_attempt_roots_authorized", True
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "maximum_supervised_invocations", 2
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "automatic_retry_authorized", True
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "docker_lifecycle_authorized", False
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "shell_execution_authorized", True
        ),
    ],
)
def test_attempt_003_disposition_rejects_scope_history_or_authority_drift(
    mutate: object,
) -> None:
    disposition = json.loads(gate.ATTEMPT_003_DISPOSITION_JSON.read_text(encoding="utf-8"))
    assert callable(mutate)
    mutate(disposition)
    failures: list[str] = []

    gate._validate_attempt_003_disposition(  # noqa: SLF001
        disposition,
        gate.ATTEMPT_003_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 Attempt 003 disposition is not closed and exact" in failures


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["diagnosis"].__setitem__(  # type: ignore[union-attr]
            "bridge_image_build_failure_proven", True
        ),
        lambda value: value["diagnosis"].__setitem__(  # type: ignore[union-attr]
            "primary_error_presence_known", True
        ),
        lambda value: value["diagnosis"].__setitem__(  # type: ignore[union-attr]
            "primary_error_value_known", True
        ),
        lambda value: value["diagnosis"].__setitem__(  # type: ignore[union-attr]
            "final_recovery_required_may_have_replaced_primary_or_originated_in_cleanup",
            False,
        ),
        lambda value: value["read_only_residue_observation"].__setitem__(  # type: ignore[union-attr]
            "current_live_truth_claimed", True
        ),
        lambda value: value["read_only_residue_observation"].__setitem__(  # type: ignore[union-attr]
            "images_removed", True
        ),
        lambda value: value["tracked_closure_scope"].pop(),  # type: ignore[union-attr]
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "recovery_action_authorized", True
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "docker_lifecycle_authorized", True
        ),
    ],
)
def test_attempt_003_closure_rejects_diagnosis_scope_or_authority_drift(
    mutate: object,
) -> None:
    closure = json.loads(gate.ATTEMPT_003_CLOSURE_JSON.read_text(encoding="utf-8"))
    assert callable(mutate)
    mutate(closure)
    failures: list[str] = []

    gate._validate_attempt_003_closure(  # noqa: SLF001
        closure,
        gate.ATTEMPT_003_CLOSURE_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 Attempt 003 closure is not closed and exact" in failures


def test_image_recovery_history_rejects_receipt_or_authority_drift() -> None:
    authorization = json.loads(gate.IMAGE_RECOVERY_AUTHORIZATION.read_text(encoding="utf-8"))
    closure = json.loads(gate.IMAGE_RECOVERY_CLOSURE.read_text(encoding="utf-8"))
    authorization["durable_consumption_receipt"]["receipt_sha256"] = (  # type: ignore[index]
        "sha256:" + "0" * 64
    )
    closure["o4_authority"]["docker_lifecycle_authorized"] = True  # type: ignore[index]
    failures: list[str] = []

    gate._validate_image_recovery_history(  # noqa: SLF001
        authorization,
        gate.IMAGE_RECOVERY_AUTHORIZATION_DOCUMENT.read_text(encoding="utf-8"),
        closure,
        gate.IMAGE_RECOVERY_CLOSURE_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 image recovery authorization closure is not exact" in failures
    assert "O4 image recovery result closure is not exact" in failures


def test_runtime_native_repair_review_is_exact() -> None:
    failures: list[str] = []

    gate._validate_runtime_native_repair_review(  # noqa: SLF001
        gate.RUNTIME_NATIVE_REPAIR_REVIEW.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []


@pytest.mark.parametrize(
    "mutation",
    [
        "candidate",
        "primary_failure",
        "cleanup_claim",
        "image_recovery",
        "authority",
        "scope",
    ],
)
def test_attempt_004_disposition_rejects_false_or_expansive_claims(
    mutation: str,
) -> None:
    disposition = json.loads(gate.ATTEMPT_004_DISPOSITION_JSON.read_text(encoding="utf-8"))
    if mutation == "candidate":
        disposition["attempted_candidate_commit"] = "a" * 40
    elif mutation == "primary_failure":
        disposition["diagnostic_facts"]["primary_failure_code"] = "success"
    elif mutation == "cleanup_claim":
        disposition["point_in_time_post_attempt_observation"]["cleanup_completed_claimed"] = True
    elif mutation == "image_recovery":
        disposition["attempt_contract"]["image_recovery_authorized"] = True
    elif mutation == "authority":
        disposition["authority"]["docker_lifecycle_authorized"] = True
    else:
        disposition["tracked_closure_scope"].pop()
    failures: list[str] = []

    gate._validate_attempt_004_disposition(  # noqa: SLF001
        disposition,
        gate.ATTEMPT_004_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures


def _snapshot_expectation(content: bytes) -> tuple[int, str, bytes]:
    return (
        0o400,
        "sha256:" + hashlib.sha256(content).hexdigest(),
        content,
    )


def _small_snapshot(
    tmp_path: Path,
) -> tuple[
    Path,
    dict[str, tuple[int, str, bytes]],
]:
    root = tmp_path / "candidate"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "input.txt").write_bytes(b"alpha")
    (nested / "data.bin").write_bytes(b"\x00\x01")
    (root / "input.txt").chmod(0o400)
    (nested / "data.bin").chmod(0o400)
    nested.chmod(0o500)
    root.chmod(0o500)
    return root, {
        "input.txt": _snapshot_expectation(b"alpha"),
        "nested/data.bin": _snapshot_expectation(b"\x00\x01"),
    }


def _unlock_snapshot(root: Path) -> None:
    for directory, directories, files in os.walk(root, topdown=False):
        for name in files:
            path = Path(directory) / name
            if not path.is_symlink():
                path.chmod(0o600)
        for name in directories:
            path = Path(directory) / name
            if not path.is_symlink():
                path.chmod(0o700)
        Path(directory).chmod(0o700)


def test_small_snapshot_no_follow_validator_accepts_exact_tree(
    tmp_path: Path,
) -> None:
    root, expected = _small_snapshot(tmp_path)
    failures: list[str] = []
    descriptor = gate._open_owned_directory(  # noqa: SLF001
        root,
        0o500,
        "test snapshot",
        failures,
    )
    assert descriptor is not None
    try:
        observed = gate._validate_snapshot_directory(  # noqa: SLF001
            descriptor,
            expected,
            failures,
        )
    finally:
        os.close(descriptor)
        _unlock_snapshot(root)

    assert observed == set(expected)
    assert failures == []


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "tampered",
        "chmod",
        "extra",
        "extra_directory",
        "symlink",
        "special",
    ],
)
def test_small_snapshot_no_follow_validator_rejects_tree_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    root, expected = _small_snapshot(tmp_path)
    nested = root / "nested"
    if mutation == "missing":
        nested.chmod(0o700)
        (nested / "data.bin").unlink()
        nested.chmod(0o500)
    elif mutation == "tampered":
        target = root / "input.txt"
        target.chmod(0o600)
        target.write_bytes(b"omega")
        target.chmod(0o400)
    elif mutation == "chmod":
        (root / "input.txt").chmod(0o600)
    else:
        root.chmod(0o700)
        if mutation == "extra":
            (root / "extra.txt").write_text("extra\n", encoding="utf-8")
            (root / "extra.txt").chmod(0o400)
        elif mutation == "extra_directory":
            (root / "extra").mkdir(mode=0o500)
        elif mutation == "symlink":
            (root / "extra").symlink_to("input.txt")
        else:
            os.mkfifo(root / "extra", 0o400)
        root.chmod(0o500)
    failures: list[str] = []
    descriptor = gate._open_owned_directory(  # noqa: SLF001
        root,
        0o500,
        "test snapshot",
        failures,
    )
    assert descriptor is not None
    try:
        observed = gate._validate_snapshot_directory(  # noqa: SLF001
            descriptor,
            expected,
            failures,
        )
    finally:
        os.close(descriptor)
        _unlock_snapshot(root)

    assert failures or observed != set(expected)


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_runtime_entry",
        "tampered_recovery_receipt",
        "run_directory",
        "published_report",
        "runtime_chmod",
    ],
)
def test_runtime_posture_rejects_population_report_or_mode_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    runtime_base = tmp_path / gate.ATTEMPT_002_RUNTIME_BASE
    runtime_base.mkdir(parents=True, mode=0o700)
    runtime_base.chmod(0o700)
    recovery_receipt = tmp_path / gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT
    recovery_receipt.write_bytes(gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES)
    recovery_receipt.chmod(0o600)
    if mutation == "extra_runtime_entry":
        (runtime_base / "unexpected").write_text("x\n", encoding="utf-8")
    elif mutation == "tampered_recovery_receipt":
        recovery_receipt.write_bytes(b"x" * len(gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES))
        recovery_receipt.chmod(0o600)
    elif mutation == "run_directory":
        (tmp_path / gate.ATTEMPT_002_RUNTIME_ROOT).mkdir(mode=0o700)
    elif mutation == "published_report":
        (tmp_path / gate.ATTEMPT_002_REPORT_ROOT).mkdir(
            parents=True,
            mode=0o700,
        )
    else:
        runtime_base.chmod(0o755)
    failures: list[str] = []

    gate._validate_attempt_002_runtime_posture(tmp_path, failures)  # noqa: SLF001

    assert failures


def test_descriptor_traversal_rejects_symlinked_var(
    tmp_path: Path,
) -> None:
    target_var = tmp_path / "target-var"
    runtime_base = target_var / "local-v1-lv1-003-o4-runtime"
    runtime_base.mkdir(parents=True, mode=0o700)
    runtime_base.chmod(0o700)
    (tmp_path / "var").symlink_to(target_var, target_is_directory=True)
    failures: list[str] = []

    gate._validate_attempt_002_runtime_posture(tmp_path, failures)  # noqa: SLF001

    assert failures
    assert any("component var" in failure or "ancestor" in failure for failure in failures)


def test_descriptor_traversal_rejects_symlinked_receipt_base(
    tmp_path: Path,
) -> None:
    var = tmp_path / "var"
    var.mkdir()
    runtime_base = var / "local-v1-lv1-003-o4-runtime"
    runtime_base.mkdir(mode=0o700)
    external_receipts = tmp_path / "external-receipts"
    external_receipts.mkdir(mode=0o700)
    (var / "local-v1-lv1-003-o4-receipts").symlink_to(
        external_receipts,
        target_is_directory=True,
    )
    failures: list[str] = []

    gate._validate_retained_attempt_evidence(tmp_path, failures)  # noqa: SLF001

    assert failures
    assert any("local-v1-lv1-003-o4-receipts" in failure for failure in failures)


def test_evidence_ignore_patterns_and_closure_scopes_are_exact() -> None:
    failures: list[str] = []

    gate._validate_evidence_ignore_patterns(ROOT, failures)  # noqa: SLF001
    closure = json.loads(gate.ATTEMPT_002_CLOSURE_JSON.read_text(encoding="utf-8"))

    assert failures == []
    assert closure["tracked_closure_scope"] == gate.CLOSURE_CONTROL_PATH_ALLOWLIST
    assert len(gate.CLOSURE_CONTROL_PATH_ALLOWLIST) == 7
    assert gate.CLOSURE_CONTROL_PATH_ALLOWLIST[0] == ".gitignore"
    attempt_003_closure = json.loads(gate.ATTEMPT_003_CLOSURE_JSON.read_text(encoding="utf-8"))
    assert (
        attempt_003_closure["tracked_closure_scope"]
        == gate.ATTEMPT_003_CLOSURE_CONTROL_PATH_ALLOWLIST
    )
    assert len(gate.ATTEMPT_003_CLOSURE_CONTROL_PATH_ALLOWLIST) == 6
    assert gate.ATTEMPT_004_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        gate.RUNTIME_NATIVE_REPAIR_REVIEW.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_004_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_004_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_004_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_005_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_005_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_005_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_006_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.API_CONTAINER_STATE_DIAGNOSTIC_REVIEW.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_006_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_006_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_006_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_007_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.APPLICATION_STARTUP_STAGE_DIAGNOSTIC_REVIEW.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_007_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_007_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_007_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_008_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        gate.IMAGE_READABILITY_REPAIR_REVIEW.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_008_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_008_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_008_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_009_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_009_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_009_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_009_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert sorted(gate.ATTEMPT_010_CONTROL_PATH_ALLOWLIST) == sorted(
        [
            "Makefile",
            "README.md",
            gate.MCC_AUTHORIZATION_INDEX_RECONCILIATION_REVIEW.as_posix(),
            gate.CONTRACT.as_posix(),
            gate.DOCUMENT.as_posix(),
            "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
            "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
        ]
    )
    assert gate.ATTEMPT_010_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_010_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_010_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_013_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_013_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_013_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]


@pytest.mark.parametrize(
    "contents",
    [
        "\n".join(gate.EVIDENCE_IGNORE_PATTERNS[1:]) + "\n",
        "\n".join(gate.EVIDENCE_IGNORE_PATTERNS + ["var/**"]) + "\n",
        "\n".join(gate.EVIDENCE_IGNORE_PATTERNS + [gate.EVIDENCE_IGNORE_PATTERNS[0]]) + "\n",
    ],
)
def test_evidence_ignore_patterns_reject_missing_broad_or_duplicate_rules(
    tmp_path: Path,
    contents: str,
) -> None:
    (tmp_path / ".gitignore").write_text(contents, encoding="utf-8")
    failures: list[str] = []

    gate._validate_evidence_ignore_patterns(tmp_path, failures)  # noqa: SLF001

    assert failures


def test_attempt_001_history_files_remain_byte_exact() -> None:
    failures: list[str] = []

    assert (
        gate._file_digest(gate.ATTEMPT_001_DISPOSITION_JSON, failures)  # noqa: SLF001
        == gate.ATTEMPT_001_DISPOSITION_JSON_DIGEST
    )
    assert (
        gate._file_digest(gate.ATTEMPT_001_DISPOSITION_DOCUMENT, failures)  # noqa: SLF001
        == gate.ATTEMPT_001_DISPOSITION_DOCUMENT_DIGEST
    )
    assert failures == []


def test_bound_review_or_disposition_digest_drift_is_rejected(
    tmp_path: Path,
) -> None:
    for relative in (
        gate.PRODUCER_EXACT_REVIEW,
        gate.DISPOSITION_JSON,
        gate.DISPOSITION_DOCUMENT,
        gate.ATTEMPT_001_DISPOSITION_JSON,
        gate.ATTEMPT_001_DISPOSITION_DOCUMENT,
        gate.ENTRYPOINT_REPAIR_REVIEW,
        gate.ATTEMPT_002_DISPOSITION_JSON,
        gate.ATTEMPT_002_DISPOSITION_DOCUMENT,
        gate.ATTEMPT_002_CLOSURE_JSON,
        gate.ATTEMPT_002_CLOSURE_DOCUMENT,
        gate.COMPOSE_REPAIR_REVIEW,
        gate.ATTEMPT_003_DISPOSITION_JSON,
        gate.ATTEMPT_003_DISPOSITION_DOCUMENT,
        gate.ATTEMPT_003_CLOSURE_JSON,
        gate.ATTEMPT_003_CLOSURE_DOCUMENT,
        gate.IMAGE_RECOVERY_AUTHORIZATION,
        gate.IMAGE_RECOVERY_AUTHORIZATION_DOCUMENT,
        gate.IMAGE_RECOVERY_CLOSURE,
        gate.IMAGE_RECOVERY_CLOSURE_DOCUMENT,
        gate.RUNTIME_NATIVE_REPAIR_REVIEW,
        gate.ATTEMPT_004_DISPOSITION_JSON,
        gate.ATTEMPT_004_DISPOSITION_DOCUMENT,
        gate.DIAGNOSTIC_REPAIR_REVIEW,
        gate.IMAGE_READABILITY_REPAIR_REVIEW,
        gate.ATTEMPT_008_DISPOSITION_JSON,
        gate.ATTEMPT_008_DISPOSITION_DOCUMENT,
        gate.ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW,
        gate.ATTEMPT_009_DISPOSITION_JSON,
        gate.ATTEMPT_009_DISPOSITION_DOCUMENT,
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    (tmp_path / gate.ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW).write_text(
        "altered\n",
        encoding="utf-8",
    )
    failures: list[str] = []

    gate._validate_bound_documents(tmp_path, failures)  # noqa: SLF001

    assert any(
        "enrollment-output projection repair exact review digest" in value for value in failures
    )


def test_execution_checkout_rejects_descendant_dirty_and_extra_path(
    tmp_path: Path,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    (repo / "extra-control.txt").write_text("extra\n", encoding="utf-8")
    failures: list[str] = []
    gate._validate_execution_checkout(repo, failures)  # noqa: SLF001
    assert any("not clean" in value for value in failures)

    _run_git(repo, "add", "extra-control.txt")
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: forbidden descendant",
    )
    failures = []
    gate._validate_execution_checkout(repo, failures)  # noqa: SLF001
    assert any("not a single immediate child" in value for value in failures)
    assert any("not the exact control allowlist" in value for value in failures)


def test_historical_attempt_009_closure_remains_exact_for_descendants() -> None:
    failures: list[str] = []

    result = gate._validate_execution_checkout(  # noqa: SLF001
        ROOT,
        failures,
        candidate_parent_commit=gate.ATTEMPT_009_CANDIDATE_COMMIT,
        candidate_parent_tree=gate.ATTEMPT_009_CANDIDATE_TREE,
        reviewed_commit=gate.ENROLLMENT_OUTPUT_PROJECTION_REPAIR_COMMIT,
        control_paths=gate.ATTEMPT_009_CLOSURE_CONTROL_PATH_ALLOWLIST,
        repair_paths=gate.ENROLLMENT_OUTPUT_PROJECTION_REPAIR_PATHS,
        candidate_ref=gate.ATTEMPT_009_CLOSURE_COMMIT,
        require_clean_worktree=False,
    )

    assert failures == []
    assert result == (
        gate.ATTEMPT_009_CLOSURE_COMMIT,
        gate.ATTEMPT_009_CLOSURE_TREE,
    )


def test_execution_checkout_rejects_sibling_of_reviewed_parent(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "sibling"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(
        repo,
        "checkout",
        "--detach",
        f"{gate.ATTEMPT_009_CANDIDATE_COMMIT}^",
    )
    for relative in gate.ATTEMPT_009_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_009_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: wrong sibling",
    )
    failures: list[str] = []

    gate._validate_execution_checkout(repo, failures)  # noqa: SLF001

    assert any("not a single immediate child" in value for value in failures)


def test_execution_checkout_rejects_non_control_drift(tmp_path: Path) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    makefile = repo / "Makefile"
    makefile.write_text(
        makefile.read_text(encoding="utf-8") + "\n# repair drift\n",
        encoding="utf-8",
    )
    _run_git(repo, "add", "Makefile")
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: forbidden repair drift",
    )
    failures: list[str] = []

    gate._validate_execution_checkout(repo, failures)  # noqa: SLF001

    assert any("not a single immediate child" in value for value in failures)
    assert any("not the exact control allowlist" in value for value in failures)


def test_execution_checkout_rejects_runtime_byte_drift(tmp_path: Path) -> None:
    repo = tmp_path / "tiny-runtime"
    repo.mkdir()
    _run_git(repo, "init", "-q")
    (repo / "runtime.txt").write_text("reviewed\n", encoding="utf-8")
    _run_git(repo, "add", "runtime.txt")
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "reviewed runtime",
    )
    reviewed = _run_git(repo, "rev-parse", "HEAD")
    parent_tree = _run_git(repo, "show", "-s", "--format=%T", "HEAD")
    (repo / "control.txt").write_text("control\n", encoding="utf-8")
    (repo / "runtime.txt").write_text("drift\n", encoding="utf-8")
    _run_git(repo, "add", "control.txt", "runtime.txt")
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "candidate drift",
    )
    failures: list[str] = []

    gate._validate_execution_checkout(  # noqa: SLF001
        repo,
        failures,
        candidate_parent_commit=reviewed,
        candidate_parent_tree=parent_tree,
        reviewed_commit=reviewed,
        runtime_paths=["runtime.txt"],
        control_paths=["control.txt", "runtime.txt"],
        repair_paths=[],
    )

    assert any("runtime differs from the exact reviewed candidate" in value for value in failures)


def test_prior_attempt_roots_fail_closed_on_retained_or_unsafe_evidence(
    tmp_path: Path,
) -> None:
    safe_root = tmp_path / gate.PRIOR_ATTEMPT_ROOTS[0]
    safe_root.mkdir(parents=True, mode=0o700)
    safe_root.chmod(0o700)
    failures: list[str] = []
    gate._validate_prior_attempt_posture(tmp_path, failures)  # noqa: SLF001
    assert failures == []

    (safe_root / "attempt.json").write_text("{}\n", encoding="utf-8")
    failures = []
    gate._validate_prior_attempt_posture(tmp_path, failures)  # noqa: SLF001
    assert any("prior attempt or success evidence exists" in value for value in failures)

    (safe_root / "attempt.json").unlink()
    safe_root.chmod(0o755)
    failures = []
    gate._validate_prior_attempt_posture(tmp_path, failures)  # noqa: SLF001
    assert any("mode is not 0700" in value for value in failures)


def test_attempt_001_recorded_root_absence_rejects_any_present_root(
    tmp_path: Path,
) -> None:
    failures: list[str] = []
    gate._validate_recorded_root_absence(tmp_path, failures)  # noqa: SLF001
    assert failures == []

    present = tmp_path / gate.PRIOR_ATTEMPT_ROOTS[1]
    present.mkdir(parents=True)
    failures = []
    gate._validate_recorded_root_absence(tmp_path, failures)  # noqa: SLF001

    assert failures == [
        "O4 Attempt 001 observed-absent root is now present: var/local-v1-lv1-003-o4-runtime"
    ]


def test_source_binding_rejects_profile_or_compose_drift(tmp_path: Path) -> None:
    contract = _contract()
    for _, (relative, _) in gate.SOURCE_DIGESTS.items():
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    overlay = tmp_path / "deploy/hermes-node-bridge/compose.yaml"
    overlay.write_text(overlay.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    failures: list[str] = []

    gate._validate_source_bindings(  # noqa: SLF001
        tmp_path,
        contract,  # type: ignore[arg-type]
        failures,
    )

    assert any("overlay_compose_sha256" in failure for failure in failures)


def test_producer_contract_closes_sequence_no_retry_and_runtime_unknowns() -> None:
    document = gate.PRODUCER_CONTRACT.read_text(encoding="utf-8")
    failures: list[str] = []

    gate._validate_producer_contract(  # noqa: SLF001
        document,
        _contract(),  # type: ignore[arg-type]
        failures,
    )

    assert failures == []
    assert gate._digest(document) == gate.PRODUCER_CONTRACT_DIGEST  # noqa: SLF001
    assert document.count("Hermes service exactly once") == 1
    assert "There is no automatic retry" in " ".join(document.split())
    assert "Runtime-Only Facts Still Unproven" in document
    assert (
        "do not prove absence of transient malicious same-UID mutation while Docker reads "
        "the build context"
    ) in " ".join(document.split())
    assert "writes and verifies `node-revocation-recovery.json`" in " ".join(document.split())


@pytest.mark.parametrize(
    "drift",
    [
        lambda document: document.replace("17. Write", "18. Write", 1),
        lambda document: document.replace(
            "Agent Run record status\n    `active`",
            "Agent Run record status\n    `completed`",
            1,
        ),
        lambda document: document.replace(
            "route stdout and stderr directly to\n    `DEVNULL`",
            "capture stdout and stderr",
            1,
        ),
    ],
)
def test_producer_contract_rejects_stage_truth_or_output_custody_drift(
    drift: object,
) -> None:
    document = gate.PRODUCER_CONTRACT.read_text(encoding="utf-8")
    assert callable(drift)
    failures: list[str] = []
    drifted = drift(document)
    assert drifted != document

    gate._validate_producer_contract(  # noqa: SLF001
        drifted,
        _contract(),  # type: ignore[arg-type,operator]
        failures,
    )

    assert failures


def test_producer_contract_digest_is_bound_in_gate() -> None:
    contract = _contract()
    failures: list[str] = []
    contract["producer_contract_sha256"] = "sha256:" + "0" * 64

    gate._validate_producer_contract(  # noqa: SLF001
        gate.PRODUCER_CONTRACT.read_text(encoding="utf-8"),
        contract,  # type: ignore[arg-type]
        failures,
    )

    assert "O4 producer contract digest binding is invalid" in failures


def test_make_wiring_is_non_live_and_not_a_release_dependency() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    release_header = next(
        line for line in makefile.splitlines() if line.startswith("release-check:")
    )

    assert gate.AUTHORIZATION_TARGET not in release_header
    assert gate.PRODUCER_STATIC_TARGET not in release_header
    assert "local-v1-lv1-003-o4-live" not in makefile
    assert "docker compose" not in gate._target_body(  # noqa: SLF001
        makefile,
        gate.AUTHORIZATION_TARGET,
    )
    assert "docker compose" not in gate._target_body(  # noqa: SLF001
        makefile,
        gate.PRODUCER_STATIC_TARGET,
    )


def test_module_entrypoint_imports_without_executing_main_or_creating_runtime() -> None:
    run_root = ROOT / "var/local-v1-lv1-003-o4-runtime" / gate.ATTEMPT_002_RUN_ID
    disposition = (
        ROOT / "var/local-v1-lv1-003-o4-receipts" / gate.ATTEMPT_002_RUN_ID / "disposition.json"
    )
    manifest = disposition.with_name("candidate-manifest.json")
    assert not run_root.exists()
    disposition_digest = gate._file_digest(disposition, [])  # noqa: SLF001
    manifest_digest = gate._file_digest(manifest, [])  # noqa: SLF001

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from scripts import local_v1_lv1_003_o4_producer as producer;"
                "assert callable(producer.main)"
            ),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert not run_root.exists()
    assert gate._file_digest(disposition, []) == disposition_digest  # noqa: SLF001
    assert gate._file_digest(manifest, []) == manifest_digest  # noqa: SLF001


def test_live_module_make_target_is_exact_unique_and_not_transitively_wired() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert makefile.count(gate.PRODUCER_RUN_TARGET) == 2
    assert sum(line == f"{gate.PRODUCER_RUN_TARGET}:" for line in makefile.splitlines()) == 1
    assert (
        gate._target_body(  # noqa: SLF001
            makefile,
            gate.PRODUCER_RUN_TARGET,
        ).strip()
        == gate.PRODUCER_MODULE_INVOCATION
    )
    assert gate.FAILED_FILE_PATH_INVOCATION not in gate._target_body(  # noqa: SLF001
        makefile,
        gate.PRODUCER_RUN_TARGET,
    )
    for parent_target in (
        "release-check",
        "local-v1-milestone-check",
        gate.PRODUCER_STATIC_TARGET,
        gate.AUTHORIZATION_TARGET,
    ):
        assert gate.PRODUCER_RUN_TARGET not in gate._target_body(  # noqa: SLF001
            makefile,
            parent_target,
        )
    assert (
        sum(
            gate.PRODUCER_RUN_TARGET in line.split()
            for line in makefile.splitlines()
            if line.startswith(".PHONY:")
        )
        == 1
    )


@pytest.mark.parametrize(
    "parent_target",
    [
        "release-check",
        "local-v1-milestone-check",
        gate.PRODUCER_STATIC_TARGET,
        gate.AUTHORIZATION_TARGET,
    ],
)
def test_live_module_make_token_rejects_forbidden_prerequisite_headers(
    tmp_path: Path,
    parent_target: str,
) -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    drifted = makefile.replace(
        f"{parent_target}:",
        f"{parent_target}: {gate.PRODUCER_RUN_TARGET}",
        1,
    )
    failures = _wiring_failures(tmp_path, drifted)

    assert any("occurs outside its exact PHONY token" in value for value in failures)
    assert any("occurrence allowlist is not exact" in value for value in failures)


def test_live_module_make_token_rejects_recipe_reference(tmp_path: Path) -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    drifted = makefile.replace(
        "test-fast:\n",
        f"test-fast:\n\t$(MAKE) {gate.PRODUCER_RUN_TARGET}\n",
        1,
    )

    failures = _wiring_failures(tmp_path, drifted)

    assert any("occurs outside its exact PHONY token" in value for value in failures)


def test_live_module_make_token_rejects_intermediate_alias_dependency(
    tmp_path: Path,
) -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    drifted = makefile + f"\no4-producer-alias: {gate.PRODUCER_RUN_TARGET}\n"

    failures = _wiring_failures(tmp_path, drifted)

    assert any("occurs outside its exact PHONY token" in value for value in failures)


def _wiring_failures(tmp_path: Path, makefile: str) -> list[str]:
    (tmp_path / "Makefile").write_text(makefile, encoding="utf-8")
    (tmp_path / "README.md").write_text(
        Path("README.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    failures: list[str] = []
    gate._validate_wiring(tmp_path, failures)  # noqa: SLF001
    return failures


def test_wiring_rejects_stale_make_attempt_comment(tmp_path: Path) -> None:
    makefile = (
        Path("Makefile")
        .read_text(encoding="utf-8")
        .replace(
            gate.PRODUCER_RUN_COMMENT,
            "# LIVE, gate-protected operator entrypoint. Attempt 001 currently refuses.",
            1,
        )
    )

    failures = _wiring_failures(tmp_path, makefile)

    assert "O4 live producer Make target comment is not exact" in failures


def test_wiring_rejects_stale_readme_attempt_guidance(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text(
        Path("Makefile").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    readme = Path("README.md").read_text(encoding="utf-8").replace(
        "closed consumed successful Attempt 021 entrypoint",
        "currently refuses because Attempt 001 is consumed",
        1,
    )
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    failures: list[str] = []

    gate._validate_wiring(tmp_path, failures)  # noqa: SLF001

    assert any(
        "README is missing current O4 Attempt 021 guidance" in failure for failure in failures
    )


def test_wiring_rejects_direct_release_dependency(tmp_path: Path) -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    drifted = makefile.replace(
        "release-check:",
        f"release-check: {gate.AUTHORIZATION_TARGET} ",
        1,
    )
    (tmp_path / "Makefile").write_text(drifted, encoding="utf-8")
    (tmp_path / "README.md").write_text(
        Path("README.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    failures: list[str] = []

    gate._validate_wiring(tmp_path, failures)  # noqa: SLF001

    assert any("must not be wired into release-check" in failure for failure in failures)

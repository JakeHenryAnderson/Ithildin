from __future__ import annotations

import subprocess
from pathlib import Path
from typing import cast

import pytest
from ithildin_api.read_tools import FilesystemReadTools, GitReadTools, ReadToolError


def make_filesystem(tmp_path: Path, *, max_read_bytes: int = 128) -> FilesystemReadTools:
    return FilesystemReadTools(
        workspace_root=tmp_path / "workspace",
        max_read_bytes=max_read_bytes,
        search_result_limit=5,
    )


def test_filesystem_list_stat_read_and_search_under_workspace(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path)
    docs = filesystem.workspace_root / "docs"
    docs.mkdir()
    readme = docs / "README.md"
    readme.write_text("alpha\nneedle here\n", encoding="utf-8")

    listing = filesystem.list_path("docs")
    stat = filesystem.stat_path("docs/README.md")
    read = filesystem.read_file("docs/README.md")
    search = filesystem.search(path="docs", query="needle")

    assert listing["entries"] == [
        {
            "name": "README.md",
            "path": "docs/README.md",
            "type": "file",
            "size": 18,
            "modified_at": stat["modified_at"],
        }
    ]
    assert stat["path"] == "docs/README.md"
    assert read["content"] == "alpha\nneedle here\n"
    assert search["matches"] == [
        {"path": "docs/README.md", "line_number": 2, "preview": "needle here"}
    ]


def test_filesystem_denies_traversal_and_absolute_escape(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path)
    filesystem.workspace_root.joinpath("ok.txt").write_text("ok", encoding="utf-8")

    with pytest.raises(ReadToolError, match="traversal"):
        filesystem.read_file("../ok.txt")

    with pytest.raises(ReadToolError, match="absolute"):
        filesystem.read_file(str(tmp_path / "outside.txt"))


def test_filesystem_denies_symlink_escape(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    filesystem.workspace_root.joinpath("link.txt").symlink_to(outside)

    with pytest.raises(ReadToolError, match="symlink"):
        filesystem.read_file("link.txt")


def test_filesystem_denies_hidden_and_sensitive_paths(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path)
    filesystem.workspace_root.joinpath(".env").write_text("TOKEN=secret", encoding="utf-8")
    secrets = filesystem.workspace_root / "secrets"
    secrets.mkdir()
    secrets.joinpath("note.txt").write_text("secret", encoding="utf-8")

    with pytest.raises(ReadToolError, match="hidden or sensitive"):
        filesystem.read_file(".env")

    with pytest.raises(ReadToolError, match="hidden or sensitive"):
        filesystem.read_file("secrets/note.txt")


def test_filesystem_denies_oversized_reads(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4)
    filesystem.workspace_root.joinpath("large.txt").write_text("too large", encoding="utf-8")

    with pytest.raises(ReadToolError, match="read limit"):
        filesystem.read_file("large.txt")


def test_git_status_diff_and_log_inside_workspace_repo(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=1024)
    repo = filesystem.workspace_root / "repo"
    repo.mkdir()
    run_git(repo, ["init"])
    run_git(repo, ["config", "user.email", "test@example.com"])
    run_git(repo, ["config", "user.name", "Test User"])
    repo.joinpath("tracked.txt").write_text("old\n", encoding="utf-8")
    run_git(repo, ["add", "tracked.txt"])
    run_git(repo, ["commit", "-m", "initial"])
    repo.joinpath("tracked.txt").write_text("old\nnew\n", encoding="utf-8")
    repo.joinpath("untracked.txt").write_text("new", encoding="utf-8")

    git = GitReadTools(filesystem=filesystem, max_output_bytes=1024, git_log_limit=10)

    status = git.status("repo")
    diff = git.diff("repo")
    log = git.log(path="repo", limit=3)
    status_lines = cast(list[str], status["status"])
    diff_text = cast(str, diff["diff"])
    commits = cast(list[dict[str, str]], log["commits"])

    assert " M tracked.txt" in status_lines
    assert "?? untracked.txt" in status_lines
    assert "+new" in diff_text
    assert commits == [{"commit": commits[0]["commit"], "subject": "initial"}]


def test_git_non_repo_fails_safely(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path)
    filesystem.workspace_root.joinpath("plain").mkdir()
    git = GitReadTools(filesystem=filesystem, max_output_bytes=1024, git_log_limit=10)

    with pytest.raises(ReadToolError, match="git repository"):
        git.status("plain")


def test_git_output_is_bounded(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=1024)
    repo = filesystem.workspace_root / "repo"
    repo.mkdir()
    run_git(repo, ["init"])
    run_git(repo, ["config", "user.email", "test@example.com"])
    run_git(repo, ["config", "user.name", "Test User"])
    repo.joinpath("big.txt").write_text("a" * 200, encoding="utf-8")
    run_git(repo, ["add", "big.txt"])
    run_git(repo, ["commit", "-m", "initial"])
    repo.joinpath("big.txt").write_text("b" * 200, encoding="utf-8")
    git = GitReadTools(filesystem=filesystem, max_output_bytes=40, git_log_limit=10)

    diff = git.diff("repo")

    assert diff["truncated"] is True
    assert len(str(diff["diff"]).encode("utf-8")) <= 40


def run_git(repo: Path, args: list[str]) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)

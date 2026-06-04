from __future__ import annotations

import os
import subprocess
import unicodedata
from pathlib import Path
from typing import cast

import pytest
from ithildin_api.read_tools import (
    FilesystemReadTools,
    GitReadTools,
    ReadToolError,
    ReadToolExecutor,
)
from ithildin_schemas import JsonObject


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


def test_filesystem_denies_symlink_directory_component_inside_workspace(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path)
    real = filesystem.workspace_root / "real"
    real.mkdir()
    real.joinpath("README.md").write_text("safe\n", encoding="utf-8")
    filesystem.workspace_root.joinpath("linked").symlink_to(real)

    with pytest.raises(ReadToolError, match="symlink"):
        filesystem.read_file("linked/README.md")


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


@pytest.mark.parametrize("path", ["..%2fsecret.txt", "%2e%2e/secret.txt", "safe%5csecret.txt"])
def test_filesystem_denies_encoded_path_tokens(tmp_path: Path, path: str) -> None:
    filesystem = make_filesystem(tmp_path)

    with pytest.raises(ReadToolError, match="encoded path tokens"):
        filesystem.read_file(path)


@pytest.mark.parametrize(
    "path",
    [
        "bad\x00path.txt",
        "bad\npath.txt",
        "bad\x7fpath.txt",
        "bad\u0085path.txt",
        "bad\u202epath.txt",
    ],
)
def test_filesystem_denies_control_character_paths(tmp_path: Path, path: str) -> None:
    filesystem = make_filesystem(tmp_path)

    with pytest.raises(ReadToolError, match="control characters"):
        filesystem.read_file(path)


def test_filesystem_denies_non_normalized_unicode_paths(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path)
    decomposed = unicodedata.normalize("NFD", "café.txt")

    with pytest.raises(ReadToolError, match="Unicode-normalized"):
        filesystem.read_file(decomposed)


def test_filesystem_denies_hardlinked_file_targets(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path)
    target = filesystem.workspace_root / "README.md"
    target.write_text("linked\n", encoding="utf-8")
    try:
        os.link(target, filesystem.workspace_root / "README-copy.md")
    except OSError as exc:
        pytest.skip(f"hardlinks unavailable: {exc}")

    with pytest.raises(ReadToolError, match="hardlinked"):
        filesystem.read_file("README.md")


def test_filesystem_denies_hardlink_swap_between_resolution_and_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filesystem = make_filesystem(tmp_path)
    target = filesystem.workspace_root / "README.md"
    target.write_text("safe\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    original_resolver = filesystem.resolve_existing_path

    def swap_to_hardlink(path: str) -> Path:
        resolved = original_resolver(path)
        if path == "README.md":
            resolved.unlink()
            try:
                os.link(outside, resolved)
            except OSError as exc:
                pytest.skip(f"hardlinks unavailable: {exc}")
        return resolved

    monkeypatch.setattr(filesystem, "resolve_existing_path", swap_to_hardlink)

    with pytest.raises(ReadToolError, match="hardlinked"):
        filesystem.read_file("README.md")

    assert outside.read_text(encoding="utf-8") == "outside\n"


def test_filesystem_read_denies_ancestor_symlink_swap_between_resolution_and_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filesystem = make_filesystem(tmp_path)
    parent = filesystem.workspace_root / "docs"
    parent.mkdir()
    parent.joinpath("README.md").write_text("safe\n", encoding="utf-8")
    outside = tmp_path / "outside-docs"
    outside.mkdir()
    outside.joinpath("README.md").write_text("outside\n", encoding="utf-8")
    original_resolver = filesystem.resolve_existing_path

    def swap_parent_to_symlink(path: str) -> Path:
        resolved = original_resolver(path)
        if path == "docs/README.md":
            parent.rename(filesystem.workspace_root / "docs-old")
            parent.symlink_to(outside)
        return resolved

    monkeypatch.setattr(filesystem, "resolve_existing_path", swap_parent_to_symlink)

    with pytest.raises(ReadToolError, match="safe directory"):
        filesystem.read_file("docs/README.md")

    assert outside.joinpath("README.md").read_text(encoding="utf-8") == "outside\n"


def test_filesystem_search_denies_symlink_swap_between_resolution_and_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not hasattr(os, "O_NOFOLLOW"):
        pytest.skip("O_NOFOLLOW unavailable on this platform")
    filesystem = make_filesystem(tmp_path)
    target = filesystem.workspace_root / "race.txt"
    target.write_text("safe needle\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside needle\n", encoding="utf-8")
    original_resolver = filesystem.resolve_existing_path

    def swap_to_symlink(path: str) -> Path:
        resolved = original_resolver(path)
        if path == "race.txt":
            resolved.unlink()
            resolved.symlink_to(outside)
        return resolved

    monkeypatch.setattr(filesystem, "resolve_existing_path", swap_to_symlink)

    result = filesystem.search(path=".", query="needle")

    assert result["matches"] == []
    assert outside.read_text(encoding="utf-8") == "outside needle\n"


def test_filesystem_list_and_search_skip_symlink_entries_inside_workspace(
    tmp_path: Path,
) -> None:
    filesystem = make_filesystem(tmp_path)
    filesystem.workspace_root.joinpath("README.md").write_text("needle\n", encoding="utf-8")
    filesystem.workspace_root.joinpath("README-link.md").symlink_to(
        filesystem.workspace_root / "README.md"
    )

    listing = filesystem.list_path(".")
    search = filesystem.search(path=".", query="needle")
    entries = cast(list[dict[str, object]], listing["entries"])

    assert [entry["path"] for entry in entries] == ["README.md"]
    assert search["matches"] == [
        {"path": "README.md", "line_number": 1, "preview": "needle"}
    ]


@pytest.mark.parametrize(
    ("swap_kind", "expected_reason"),
    [
        ("missing", "safe regular file"),
        ("directory", "path is not a file"),
        ("binary", "binary"),
        ("oversized", "read limit"),
        ("symlink", "safe regular file"),
    ],
)
def test_filesystem_read_denies_bounded_target_swaps_between_resolution_and_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    swap_kind: str,
    expected_reason: str,
) -> None:
    if swap_kind == "symlink" and not hasattr(os, "O_NOFOLLOW"):
        pytest.skip("O_NOFOLLOW unavailable on this platform")
    filesystem = make_filesystem(tmp_path, max_read_bytes=8)
    target = filesystem.workspace_root / "race.txt"
    target.write_text("safe\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    original_resolver = filesystem.resolve_existing_path

    def swap_target(path: str) -> Path:
        resolved = original_resolver(path)
        if path == "race.txt":
            resolved.unlink()
            if swap_kind == "directory":
                resolved.mkdir()
            elif swap_kind == "binary":
                resolved.write_bytes(b"safe\x00")
            elif swap_kind == "oversized":
                resolved.write_text("too large\n", encoding="utf-8")
            elif swap_kind == "symlink":
                resolved.symlink_to(outside)
        return resolved

    monkeypatch.setattr(filesystem, "resolve_existing_path", swap_target)

    with pytest.raises(ReadToolError, match=expected_reason):
        filesystem.read_file("race.txt")

    assert outside.read_text(encoding="utf-8") == "outside\n"


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


def test_git_commit_metadata_returns_structured_bounded_metadata(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    repo = filesystem.workspace_root
    run_git(repo, ["init"])
    run_git(repo, ["config", "user.email", "test@example.com"])
    run_git(repo, ["config", "user.name", "Test User"])
    repo.joinpath("tracked.txt").write_text("hello\n", encoding="utf-8")
    run_git(repo, ["add", "tracked.txt"])
    run_git(repo, ["commit", "-m", "initial subject", "-m", "body line"])
    commit_hash = git_output(repo, ["rev-parse", "HEAD"])
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    metadata = git.commit_metadata(
        {
            "ref": {"kind": "object_id", "value": commit_hash},
            "include_body": True,
            "include_emails": False,
            "include_diffstat": True,
        }
    )

    assert metadata["resolved_commit_hash"] == commit_hash
    assert metadata["parent_hashes"] == []
    assert metadata["subject"] == "initial subject"
    assert metadata["body"] == "body line"
    assert metadata["body_included"] is True
    assert metadata["author"] == {
            "name": "Test User",
            "email_included": False,
            "email_hash": "sha256:cce878759375b6479cdf7131305e30163e3decec0da61df6840dafa3a747f3f2",
    }
    assert metadata["changed_files"] == [
        {"status": "A", "path": "tracked.txt", "path_redacted": False}
    ]
    output_policy = cast(dict[str, object], metadata["output_policy"])
    assert output_policy["raw_diff_included"] is False
    assert output_policy["file_contents_included"] is False


def test_git_commit_metadata_resolves_local_branch_and_tag(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    repo = filesystem.workspace_root
    run_git(repo, ["init"])
    run_git(repo, ["config", "user.email", "test@example.com"])
    run_git(repo, ["config", "user.name", "Test User"])
    repo.joinpath("tracked.txt").write_text("hello\n", encoding="utf-8")
    run_git(repo, ["add", "tracked.txt"])
    run_git(repo, ["commit", "-m", "initial"])
    run_git(repo, ["branch", "safe/topic"])
    run_git(repo, ["tag", "v1"])
    commit_hash = git_output(repo, ["rev-parse", "HEAD"])
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    branch_metadata = git.commit_metadata({"ref": {"kind": "branch", "value": "safe/topic"}})
    tag_metadata = git.commit_metadata({"ref": {"kind": "tag", "value": "v1"}})

    assert branch_metadata["resolved_commit_hash"] == commit_hash
    assert tag_metadata["resolved_commit_hash"] == commit_hash


def test_git_commit_metadata_redacts_emails_when_requested(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    repo = filesystem.workspace_root
    run_git(repo, ["init"])
    run_git(repo, ["config", "user.email", "test@example.com"])
    run_git(repo, ["config", "user.name", "Test User"])
    repo.joinpath("tracked.txt").write_text("hello\n", encoding="utf-8")
    run_git(repo, ["add", "tracked.txt"])
    run_git(repo, ["commit", "-m", "initial"])
    commit_hash = git_output(repo, ["rev-parse", "HEAD"])
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    metadata = git.commit_metadata(
        {"ref": {"kind": "object_id", "value": commit_hash}, "include_emails": True}
    )

    author = cast(dict[str, object], metadata["author"])
    committer = cast(dict[str, object], metadata["committer"])
    assert author["email"] == "[REDACTED]"
    assert committer["email"] == "[REDACTED]"
    assert "test@example.com" not in json_dump(metadata)


def test_git_commit_metadata_sanitizes_identity_separator_and_hides_email(
    tmp_path: Path,
) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    repo = filesystem.workspace_root
    run_git(repo, ["init"])
    repo.joinpath("tracked.txt").write_text("hello\n", encoding="utf-8")
    run_git(repo, ["add", "tracked.txt"])
    run_git(
        repo,
        ["commit", "-m", "separator identity"],
        env={
            "GIT_AUTHOR_NAME": f"Test\x1fUser <hidden@example.com>{'x' * 400}",
            "GIT_AUTHOR_EMAIL": "author@example.com",
            "GIT_COMMITTER_NAME": "Committer\x1fUser <hidden@example.com>",
            "GIT_COMMITTER_EMAIL": "committer@example.com",
        },
    )
    commit_hash = git_output(repo, ["rev-parse", "HEAD"])
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    metadata = git.commit_metadata(
        {"ref": {"kind": "object_id", "value": commit_hash}, "include_emails": False}
    )

    author = cast(dict[str, object], metadata["author"])
    committer = cast(dict[str, object], metadata["committer"])
    assert str(author["name"]).startswith("Test�User [REDACTED_EMAIL]")
    assert len(str(author["name"]).encode("utf-8")) <= 240
    assert committer["name"] == "Committer�User [REDACTED_EMAIL]"
    assert "hidden@example.com" not in json_dump(metadata)
    assert "author@example.com" not in json_dump(metadata)
    assert "committer@example.com" not in json_dump(metadata)


def test_git_commit_metadata_denies_unsupported_ref_syntax(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    repo = filesystem.workspace_root
    run_git(repo, ["init"])
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    denied_refs: list[dict[str, str]] = [
        {"kind": "branch", "value": "origin/main"},
        {"kind": "branch", "value": "refs/heads/main"},
        {"kind": "branch", "value": "refs/remotes/origin/main"},
        {"kind": "branch", "value": "feature..main"},
        {"kind": "branch", "value": "feature...main"},
        {"kind": "branch", "value": "HEAD~1"},
        {"kind": "branch", "value": "HEAD@{1}"},
        {"kind": "branch", "value": ":/message"},
        {"kind": "branch", "value": "main:path"},
        {"kind": "branch", "value": "bad\x1fref"},
        {"kind": "branch", "value": "cafe\u0301"},
        {"kind": "tag", "value": "-bad"},
        {"kind": "object_id", "value": "HEAD"},
    ]
    for ref in denied_refs:
        with pytest.raises(ReadToolError):
            git.commit_metadata({"ref": cast(JsonObject, ref)})


def test_git_commit_metadata_denies_non_commit_object_id(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    repo = filesystem.workspace_root
    run_git(repo, ["init"])
    repo.joinpath("blob.txt").write_text("blob\n", encoding="utf-8")
    blob_hash = git_output(repo, ["hash-object", "blob.txt"])
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    with pytest.raises(ReadToolError):
        git.commit_metadata({"ref": {"kind": "object_id", "value": blob_hash}})


def test_git_commit_metadata_redacts_hidden_or_sensitive_changed_paths(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    repo = filesystem.workspace_root
    run_git(repo, ["init"])
    run_git(repo, ["config", "user.email", "test@example.com"])
    run_git(repo, ["config", "user.name", "Test User"])
    repo.joinpath(".env").write_text("TOKEN=value\n", encoding="utf-8")
    run_git(repo, ["add", ".env"])
    run_git(repo, ["commit", "-m", "secret path"])
    commit_hash = git_output(repo, ["rev-parse", "HEAD"])
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    metadata = git.commit_metadata({"ref": {"kind": "object_id", "value": commit_hash}})

    assert metadata["sensitive_paths_redacted"] == 1
    assert metadata["changed_files"] == [
        {
            "status": "A",
            "path": "<redacted>",
            "path_redacted": True,
            "path_hash": "sha256:239a7b407f92134ace046281584ad04306c5d4c81d642e902124f8dcd1a6e680",
        }
    ]


def test_git_commit_metadata_redacts_private_key_and_credential_paths(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    repo = filesystem.workspace_root
    run_git(repo, ["init"])
    run_git(repo, ["config", "user.email", "test@example.com"])
    run_git(repo, ["config", "user.name", "Test User"])
    for name in ["id_rsa", "credentials.json", "private-key.pem"]:
        repo.joinpath(name).write_text("secret\n", encoding="utf-8")
    run_git(repo, ["add", "id_rsa", "credentials.json", "private-key.pem"])
    run_git(repo, ["commit", "-m", "credential paths"])
    commit_hash = git_output(repo, ["rev-parse", "HEAD"])
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    metadata = git.commit_metadata({"ref": {"kind": "object_id", "value": commit_hash}})
    changed_files = cast(list[dict[str, object]], metadata["changed_files"])

    assert metadata["sensitive_paths_redacted"] == 3
    assert all(record["path"] == "<redacted>" for record in changed_files)
    assert "id_rsa" not in json_dump(metadata)
    assert "credentials.json" not in json_dump(metadata)
    assert "private-key.pem" not in json_dump(metadata)


def test_git_commit_metadata_denies_parent_repo_outside_workspace(tmp_path: Path) -> None:
    parent_repo = tmp_path / "parent"
    parent_repo.mkdir()
    workspace_root = parent_repo / "workspace"
    workspace_root.mkdir()
    run_git(parent_repo, ["init"])
    run_git(parent_repo, ["config", "user.email", "test@example.com"])
    run_git(parent_repo, ["config", "user.name", "Test User"])
    workspace_root.joinpath("tracked.txt").write_text("hello\n", encoding="utf-8")
    run_git(parent_repo, ["add", "workspace/tracked.txt"])
    run_git(parent_repo, ["commit", "-m", "parent repo commit"])
    commit_hash = git_output(parent_repo, ["rev-parse", "HEAD"])
    filesystem = FilesystemReadTools(
        workspace_root=workspace_root,
        max_read_bytes=4096,
        search_result_limit=5,
    )
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    with pytest.raises(ReadToolError, match="workspace scope"):
        git.commit_metadata({"ref": {"kind": "object_id", "value": commit_hash}})


def test_git_commit_metadata_resource_denies_parent_repo_outside_workspace(
    tmp_path: Path,
) -> None:
    parent_repo = tmp_path / "parent"
    parent_repo.mkdir()
    workspace_root = parent_repo / "workspace"
    workspace_root.mkdir()
    run_git(parent_repo, ["init"])
    run_git(parent_repo, ["config", "user.email", "test@example.com"])
    run_git(parent_repo, ["config", "user.name", "Test User"])
    workspace_root.joinpath("tracked.txt").write_text("hello\n", encoding="utf-8")
    run_git(parent_repo, ["add", "workspace/tracked.txt"])
    run_git(parent_repo, ["commit", "-m", "parent repo commit"])
    commit_hash = git_output(parent_repo, ["rev-parse", "HEAD"])
    executor = ReadToolExecutor.from_settings(
        workspace_root=workspace_root,
        max_read_bytes=4096,
        search_result_limit=5,
        git_log_limit=10,
    )

    resource = executor.resource_from_arguments(
        {"ref": {"kind": "object_id", "value": commit_hash}},
        tool_name="git.show.commit_metadata",
    )

    assert resource["in_scope"] is False
    assert resource["scope_error"] == "git repository escapes the workspace scope"


def test_git_diff_denies_hidden_or_sensitive_tracked_paths(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=2048)
    repo = filesystem.workspace_root / "repo"
    repo.mkdir()
    run_git(repo, ["init"])
    run_git(repo, ["config", "user.email", "test@example.com"])
    run_git(repo, ["config", "user.name", "Test User"])
    repo.joinpath(".env").write_text("TOKEN=old\n", encoding="utf-8")
    run_git(repo, ["add", ".env"])
    run_git(repo, ["commit", "-m", "initial"])
    repo.joinpath(".env").write_text("TOKEN=new\n", encoding="utf-8")
    git = GitReadTools(filesystem=filesystem, max_output_bytes=2048, git_log_limit=10)

    with pytest.raises(ReadToolError, match="hidden or sensitive"):
        git.diff("repo")


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


def run_git(repo: Path, args: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )


def git_output(repo: Path, args: list[str]) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def json_dump(value: object) -> str:
    import json

    return json.dumps(value, sort_keys=True)

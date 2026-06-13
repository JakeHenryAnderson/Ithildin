from __future__ import annotations

import json
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


def test_git_ref_summary_returns_name_free_local_metadata(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    repo = filesystem.workspace_root
    run_git(repo, ["init"])
    run_git(repo, ["config", "user.email", "test@example.com"])
    run_git(repo, ["config", "user.name", "Test User"])
    repo.joinpath("tracked.txt").write_text("hello\n", encoding="utf-8")
    run_git(repo, ["add", "tracked.txt"])
    run_git(repo, ["commit", "-m", "initial"])
    run_git(repo, ["branch", "safe/topic"])
    run_git(repo, ["tag", "-a", "v1", "-m", "v1"])
    commit_hash = git_output(repo, ["rev-parse", "HEAD"])
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    summary = git.ref_summary({"selector": {"kind": "all_local"}, "limit": 10})

    assert summary["tool_name"] == "git.show.ref_summary"
    assert summary["selector"] == {"kind": "all_local"}
    assert summary["truncated"] is False
    refs = cast(list[dict[str, object]], summary["refs"])
    assert {ref["kind"] for ref in refs} == {"branch", "tag"}
    assert all(str(ref["ref_id"]).startswith("ref_") for ref in refs)
    assert all(ref["resolved_commit_hash"] == commit_hash for ref in refs)
    assert any(ref.get("is_current_branch") is True for ref in refs if ref["kind"] == "branch")
    output_policy = cast(dict[str, object], summary["output_policy"])
    assert output_policy["ref_names_included"] is False
    assert output_policy["stable_ref_hashes_included"] is False
    dumped = json_dump(summary)
    assert "safe/topic" not in dumped
    assert "refs/heads" not in dumped
    assert "v1" not in dumped


def test_git_ref_summary_selector_and_limit_are_bounded(tmp_path: Path) -> None:
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
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    branch_summary = git.ref_summary({"selector": {"kind": "branch"}, "limit": 1})
    tag_summary = git.ref_summary({"selector": {"kind": "tag"}, "limit": 10})

    assert branch_summary["ref_count"] == 1
    assert branch_summary["truncated"] is True
    branch_refs = cast(list[dict[str, str]], branch_summary["refs"])
    tag_refs = cast(list[dict[str, str]], tag_summary["refs"])
    assert all(ref["kind"] == "branch" for ref in branch_refs)
    assert tag_summary["ref_count"] == 1
    assert all(ref["kind"] == "tag" for ref in tag_refs)


def test_git_ref_summary_rejects_unsupported_arguments(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    repo = filesystem.workspace_root
    run_git(repo, ["init"])
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    denied_arguments = [
        {"selector": {"kind": "all_local", "ref": "main"}},
        {"selector": {"kind": "remote"}},
        {"selector": {"kind": "branch"}, "include_names": True},
        {"selector": {"kind": "branch"}, "include_current_branch": True},
        {"selector": {"kind": "branch"}, "format": "%(refname)"},
        {"selector": {"kind": "branch"}, "argv": ["for-each-ref"]},
        {"selector": {"kind": "branch"}, "ref": "main"},
        {"selector": {"kind": "branch"}, "remote": "origin"},
        {"selector": {"kind": "branch"}, "limit": 0},
        {"selector": {"kind": "branch"}, "limit": 201},
    ]
    for arguments in denied_arguments:
        with pytest.raises(ReadToolError):
            git.ref_summary(cast(JsonObject, arguments))


def test_git_ref_summary_skips_non_commit_refs(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    repo = filesystem.workspace_root
    run_git(repo, ["init"])
    run_git(repo, ["config", "user.email", "test@example.com"])
    run_git(repo, ["config", "user.name", "Test User"])
    repo.joinpath("tracked.txt").write_text("hello\n", encoding="utf-8")
    run_git(repo, ["add", "tracked.txt"])
    run_git(repo, ["commit", "-m", "initial"])
    blob_hash = git_output(repo, ["hash-object", "tracked.txt"])
    run_git(repo, ["tag", "blobtag", blob_hash])
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    summary = git.ref_summary({"selector": {"kind": "tag"}})

    assert summary["ref_count"] == 0
    assert summary["refs"] == []


def test_git_ref_summary_denies_parent_repo_outside_workspace(tmp_path: Path) -> None:
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
    filesystem = FilesystemReadTools(
        workspace_root=workspace_root,
        max_read_bytes=4096,
        search_result_limit=5,
    )
    git = GitReadTools(filesystem=filesystem, max_output_bytes=4096, git_log_limit=10)

    with pytest.raises(ReadToolError, match="workspace scope"):
        git.ref_summary({"selector": {"kind": "all_local"}})


def test_git_ref_summary_resource_denies_parent_repo_outside_workspace(
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
    executor = ReadToolExecutor.from_settings(
        workspace_root=workspace_root,
        max_read_bytes=4096,
        search_result_limit=5,
        git_log_limit=10,
    )

    resource = executor.resource_from_arguments(
        {"selector": {"kind": "all_local"}},
        tool_name="git.show.ref_summary",
    )

    assert resource["in_scope"] is False
    assert resource["scope_error"] == "git repository escapes the workspace scope"


def test_project_manifest_summary_returns_count_only_metadata(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("package.json").write_text(
        json.dumps(
            {
                "name": "private-service",
                "scripts": {"deploy": "TOKEN=secret npm publish"},
                "dependencies": {"internal-package": "1.0.0"},
                "devDependencies": {"test-helper": "2.0.0"},
                "repository": "https://example.test/private/repo",
            }
        ),
        encoding="utf-8",
    )
    root.joinpath("package-lock.json").write_text("{}", encoding="utf-8")

    summary = filesystem.project_manifest_summary(
        {"root": ".", "manifest_kinds": ["package.json"], "limit": 5}
    )

    assert summary["tool_name"] == "project.manifest.summary"
    assert summary["manifest_count"] == 1
    manifest = cast(list[dict[str, object]], summary["manifests"])[0]
    assert manifest["kind"] == "package.json"
    assert manifest["ecosystem"] == "node"
    assert manifest["dependency_section_counts"] == {
        "dependencies": 1,
        "devDependencies": 1,
    }
    assert manifest["script_count"] == 1
    assert manifest["dependency_names_included"] is False
    assert manifest["script_values_included"] is False
    assert manifest["file_contents_included"] is False
    assert cast(dict[str, object], manifest["lockfile_presence"])["package-lock.json"] is True
    output_policy = cast(dict[str, object], summary["output_policy"])
    assert output_policy["dependency_names_included"] is False
    assert output_policy["package_script_values_included"] is False
    assert output_policy["registry_or_network_access_used"] is False
    dumped = json_dump(summary)
    assert "private-service" not in dumped
    assert "internal-package" not in dumped
    assert "deploy" not in dumped
    assert "TOKEN=secret" not in dumped
    assert "repository" not in dumped


def test_project_manifest_summary_counts_multiple_ecosystems(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("pyproject.toml").write_text(
        """
[project]
dependencies = ["private-lib==1.0", "another-lib"]
[project.optional-dependencies]
dev = ["pytest"]
[project.scripts]
private-cli = "private.module:main"
""",
        encoding="utf-8",
    )
    root.joinpath("requirements.txt").write_text(
        "private-lib==1.0\n--index-url https://secret.example/simple\nvisible\n",
        encoding="utf-8",
    )

    summary = filesystem.project_manifest_summary(
        {"manifest_kinds": ["pyproject.toml", "requirements.txt"]}
    )

    manifests = cast(list[dict[str, object]], summary["manifests"])
    assert [manifest["kind"] for manifest in manifests] == [
        "pyproject.toml",
        "requirements.txt",
    ]
    pyproject = manifests[0]
    requirements = manifests[1]
    assert pyproject["dependency_section_counts"] == {
        "project.dependencies": 2,
        "project.optional-dependencies": 1,
    }
    assert pyproject["script_count"] == 1
    assert requirements["dependency_section_counts"] == {"requirements": 2}
    dumped = json_dump(summary)
    assert "private-lib" not in dumped
    assert "secret.example" not in dumped
    assert "private-cli" not in dumped


def test_project_manifest_summary_rejects_unsupported_arguments(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    denied_arguments = [
        {"path": "package.json"},
        {"root": "../outside"},
        {"root": "/tmp"},
        {"root": "bad\x1fpath"},
        {"manifest_kinds": ["../../secrets.env"]},
        {"manifest_kinds": ["package.json", "package.json"]},
        {"manifest_kinds": []},
        {"glob": "**/package.json"},
        {"recursive": True},
        {"include_file_contents": True},
        {"include_script_values": True},
        {"include_dependency_names": True},
        {"registry_url": "https://registry.example.test"},
        {"command": "npm install"},
        {"argv": ["npm", "ls"]},
        {"limit": 0},
        {"limit": 21},
    ]

    for arguments in denied_arguments:
        with pytest.raises(ReadToolError):
            filesystem.project_manifest_summary(cast(JsonObject, arguments))


def test_project_manifest_summary_malformed_manifest_fails_safely(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    filesystem.workspace_root.joinpath("package.json").write_text(
        '{"dependencies":{"private-package":"1.0"', encoding="utf-8"
    )

    summary = filesystem.project_manifest_summary({"manifest_kinds": ["package.json"]})

    manifest = cast(list[dict[str, object]], summary["manifests"])[0]
    assert manifest["parse_status"] == "parse_failed"
    assert manifest["parse_error_reason"] == "manifest parse failed safely"
    assert "private-package" not in json_dump(summary)


def test_project_manifest_summary_denies_symlinked_manifest(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    outside = tmp_path / "outside-package.json"
    outside.write_text("{}", encoding="utf-8")
    filesystem.workspace_root.joinpath("package.json").symlink_to(outside)

    with pytest.raises(ReadToolError, match="symlink"):
        filesystem.project_manifest_summary({"manifest_kinds": ["package.json"]})


def test_project_dependency_summary_returns_count_only_metadata(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("package.json").write_text(
        json.dumps(
            {
                "name": "private-service",
                "scripts": {"deploy": "TOKEN=secret npm publish"},
                "dependencies": {"internal-package": "1.0.0"},
                "devDependencies": {"test-helper": "2.0.0"},
                "repository": "https://example.test/private/repo",
            }
        ),
        encoding="utf-8",
    )
    root.joinpath("package-lock.json").write_text("{}", encoding="utf-8")

    summary = filesystem.project_dependency_summary(
        {"root": ".", "manifest_kinds": ["package.json"], "limit": 5}
    )

    assert summary["tool_name"] == "project.dependency.summary"
    assert summary["manifest_count"] == 1
    assert summary["total_direct_dependency_count"] == 2
    assert summary["dependency_section_totals"] == {
        "dependencies": 1,
        "devDependencies": 1,
    }
    manifest = cast(list[dict[str, object]], summary["manifests"])[0]
    assert manifest["kind"] == "package.json"
    assert manifest["ecosystem"] == "node"
    assert manifest["direct_dependency_count"] == 2
    assert manifest["dependency_names_included"] is False
    assert manifest["dependency_versions_included"] is False
    assert manifest["package_names_included"] is False
    assert manifest["package_script_names_included"] is False
    assert manifest["package_script_values_included"] is False
    assert manifest["lockfile_contents_included"] is False
    output_policy = cast(dict[str, object], summary["output_policy"])
    assert output_policy["dependency_names_included"] is False
    assert output_policy["dependency_versions_included"] is False
    assert output_policy["package_names_included"] is False
    assert output_policy["package_script_names_included"] is False
    assert output_policy["package_script_values_included"] is False
    assert output_policy["lockfile_contents_included"] is False
    assert output_policy["registry_or_network_access_used"] is False
    assert output_policy["package_manager_execution_used"] is False
    assert output_policy["transitive_dependencies_resolved"] is False
    dumped = json_dump(summary)
    assert "private-service" not in dumped
    assert "internal-package" not in dumped
    assert "1.0.0" not in dumped
    assert "deploy" not in dumped
    assert "TOKEN=secret" not in dumped
    assert "repository" not in dumped
    assert "package-lock.json" not in dumped


def test_project_structure_summary_returns_count_only_metadata(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("src").mkdir()
    root.joinpath("src", "secret_feature.py").write_text("TOKEN = 'secret'\n", encoding="utf-8")
    root.joinpath("tests").mkdir()
    root.joinpath("tests", "test_secret_feature.ts").write_text("secret\n", encoding="utf-8")
    root.joinpath("docs").mkdir()
    root.joinpath("docs", "Private Roadmap.md").write_text("private\n", encoding="utf-8")
    root.joinpath("package-lock.json").write_text("{}", encoding="utf-8")
    root.joinpath(".env").write_text("TOKEN=secret", encoding="utf-8")
    root.joinpath(".git").mkdir()
    root.joinpath(".git", "config").write_text("[remote]\n", encoding="utf-8")

    summary = filesystem.project_structure_summary({"root": ".", "max_depth": 2, "limit": 20})

    assert summary["tool_name"] == "project.structure.summary"
    assert summary["summary"] == {
        "visible_directory_count": 3,
        "visible_file_count": 4,
        "max_observed_depth": 2,
        "inspected_entry_count": 9,
    }
    assert cast(dict[str, int], summary["directory_categories"])["source"] == 1
    assert cast(dict[str, int], summary["directory_categories"])["tests"] == 1
    assert cast(dict[str, int], summary["directory_categories"])["docs"] == 1
    assert cast(dict[str, int], summary["file_kinds"])["python"] == 1
    assert cast(dict[str, int], summary["file_kinds"])["typescript"] == 1
    assert cast(dict[str, int], summary["file_kinds"])["markdown"] == 1
    assert cast(dict[str, int], summary["file_kinds"])["lockfile_present"] == 1
    assert cast(dict[str, int], summary["skipped_counts"])["hidden_or_sensitive"] == 1
    assert cast(dict[str, int], summary["skipped_counts"])["git_internal"] == 1
    output_policy = cast(dict[str, object], summary["output_policy"])
    assert output_policy["file_contents_included"] is False
    assert output_policy["raw_recursive_listing_included"] is False
    assert output_policy["raw_file_names_included"] is False
    assert output_policy["dependency_names_included"] is False
    assert output_policy["package_manager_execution_used"] is False
    assert output_policy["registry_or_network_access_used"] is False
    dumped = json_dump(summary)
    assert "secret_feature" not in dumped
    assert "Private Roadmap" not in dumped
    assert "TOKEN" not in dumped
    assert ".env" not in dumped
    assert ".git" not in dumped


def test_project_structure_summary_honors_limits_and_include_categories(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("src").mkdir()
    root.joinpath("src", "deep").mkdir()
    root.joinpath("src", "deep", "private.py").write_text("secret\n", encoding="utf-8")
    root.joinpath("README.md").write_text("hello\n", encoding="utf-8")

    summary = filesystem.project_structure_summary(
        {
            "root": ".",
            "max_depth": 1,
            "limit": 1,
            "include_categories": ["skipped_counts"],
        }
    )

    assert "directory_categories" not in summary
    assert "file_kinds" not in summary
    assert "skipped_counts" in summary
    assert summary["truncated"] is True
    skipped = cast(dict[str, int], summary["skipped_counts"])
    assert skipped["item_limit"] >= 1


def test_project_structure_summary_skips_symlink_and_hardlink_entries(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    target = root / "private.txt"
    target.write_text("private\n", encoding="utf-8")
    try:
        os.link(target, root / "private-copy.txt")
    except OSError:
        pytest.skip("hardlinks are not supported on this filesystem")
    outside = tmp_path / "outside"
    outside.mkdir()
    root.joinpath("outside-link").symlink_to(outside)

    summary = filesystem.project_structure_summary({"root": ".", "max_depth": 1, "limit": 20})

    skipped = cast(dict[str, int], summary["skipped_counts"])
    assert skipped["hardlink"] == 2
    assert skipped["symlink"] == 1
    dumped = json_dump(summary)
    assert "private" not in dumped
    assert "outside" not in dumped


def test_project_structure_summary_rejects_unsupported_arguments(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    denied_arguments = [
        {"path": "."},
        {"root": "../outside"},
        {"root": "/tmp"},
        {"root": "bad\x1fpath"},
        {"max_depth": -1},
        {"max_depth": 5},
        {"limit": 0},
        {"limit": 251},
        {"include_categories": []},
        {"include_categories": ["file_kinds", "file_kinds"]},
        {"include_categories": ["raw_names"]},
        {"glob": "**/*"},
        {"regex": ".*"},
        {"recursive": True},
        {"include_file_contents": True},
        {"include_file_names": True},
        {"include_dependency_names": True},
        {"include_package_names": True},
        {"include_script_values": True},
        {"registry_url": "https://registry.example.test"},
        {"command": "find ."},
        {"argv": ["find", "."]},
    ]

    for arguments in denied_arguments:
        with pytest.raises(ReadToolError):
            filesystem.project_structure_summary(cast(JsonObject, arguments))


def test_project_test_summary_returns_count_only_metadata(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("tests").mkdir()
    root.joinpath("tests", "test_secret_feature.py").write_text(
        "TOKEN = 'secret'\n", encoding="utf-8"
    )
    root.joinpath("src").mkdir()
    root.joinpath("src", "feature.test.ts").write_text("secret\n", encoding="utf-8")
    root.joinpath("docs").mkdir()
    root.joinpath("docs", "example_test.md").write_text("private\n", encoding="utf-8")
    root.joinpath(".env").write_text("TOKEN=secret", encoding="utf-8")
    root.joinpath(".git").mkdir()
    root.joinpath(".git", "config").write_text("[remote]\n", encoding="utf-8")

    summary = filesystem.project_test_summary({"root": ".", "max_depth": 3, "limit": 30})

    assert summary["tool_name"] == "project.test.summary"
    assert summary["summary"] == {
        "visible_test_directory_count": 1,
        "visible_test_file_count": 3,
        "max_observed_depth": 2,
        "inspected_entry_count": 8,
    }
    assert cast(dict[str, int], summary["framework_hints"])["python_pytest_hint"] == 1
    assert cast(dict[str, int], summary["framework_hints"])["typescript_test_hint"] == 1
    assert cast(dict[str, int], summary["framework_hints"])["unknown_test_hint"] == 1
    assert cast(dict[str, int], summary["test_location_counts"])["dedicated_test_directory"] == 2
    assert cast(dict[str, int], summary["test_location_counts"])["source_adjacent_test"] == 1
    assert cast(dict[str, int], summary["test_location_counts"])["documentation_example"] == 1
    assert cast(dict[str, int], summary["language_family_counts"])["python"] == 1
    assert cast(dict[str, int], summary["language_family_counts"])["typescript"] == 1
    assert cast(dict[str, int], summary["language_family_counts"])["markdown"] == 1
    assert cast(dict[str, int], summary["skipped_counts"])["hidden_or_sensitive"] == 1
    assert cast(dict[str, int], summary["skipped_counts"])["git_internal"] == 1
    output_policy = cast(dict[str, object], summary["output_policy"])
    assert output_policy["file_contents_included"] is False
    assert output_policy["test_file_names_included"] is False
    assert output_policy["raw_paths_included"] is False
    assert output_policy["test_execution_used"] is False
    assert output_policy["package_manager_execution_used"] is False
    dumped = json_dump(summary)
    assert "test_secret_feature" not in dumped
    assert "feature.test" not in dumped
    assert "example_test" not in dumped
    assert "TOKEN" not in dumped
    assert ".env" not in dumped
    assert ".git" not in dumped


def test_project_test_summary_honors_limits_and_include_categories(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("tests").mkdir()
    root.joinpath("tests", "test_private.py").write_text("secret\n", encoding="utf-8")
    root.joinpath("src").mkdir()
    root.joinpath("src", "feature.test.ts").write_text("secret\n", encoding="utf-8")

    summary = filesystem.project_test_summary(
        {
            "root": ".",
            "max_depth": 1,
            "limit": 1,
            "include_categories": ["skipped_counts"],
        }
    )

    assert "framework_hints" not in summary
    assert "test_location_counts" not in summary
    assert "language_family_counts" not in summary
    assert "skipped_counts" in summary
    assert summary["truncated"] is True
    assert cast(dict[str, int], summary["skipped_counts"])["item_limit"] >= 1


def test_project_test_summary_skips_symlink_and_hardlink_entries(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    tests = root / "tests"
    tests.mkdir()
    target = tests / "test_private.py"
    target.write_text("private\n", encoding="utf-8")
    try:
        os.link(target, tests / "test_private_copy.py")
    except OSError:
        pytest.skip("hardlinks are not supported on this filesystem")
    outside = tmp_path / "outside"
    outside.mkdir()
    root.joinpath("outside-link").symlink_to(outside)

    summary = filesystem.project_test_summary({"root": ".", "max_depth": 2, "limit": 20})

    skipped = cast(dict[str, int], summary["skipped_counts"])
    assert skipped["hardlink"] == 2
    assert skipped["symlink"] == 1
    dumped = json_dump(summary)
    assert "private" not in dumped
    assert "outside" not in dumped


def test_project_test_summary_rejects_unsupported_arguments(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    denied_arguments = [
        {"path": "."},
        {"root": "../outside"},
        {"root": "/tmp"},
        {"root": "bad\x1fpath"},
        {"max_depth": -1},
        {"max_depth": 6},
        {"limit": 0},
        {"limit": 301},
        {"include_categories": []},
        {"include_categories": ["framework_hints", "framework_hints"]},
        {"include_categories": ["raw_names"]},
        {"glob": "**/*"},
        {"regex": ".*"},
        {"recursive": True},
        {"include_file_contents": True},
        {"include_file_names": True},
        {"include_test_names": True},
        {"include_dependency_names": True},
        {"include_package_names": True},
        {"include_script_values": True},
        {"include_coverage": True},
        {"execute_tests": True},
        {"registry_url": "https://registry.example.test"},
        {"command": "pytest"},
        {"argv": ["pytest"]},
    ]

    for arguments in denied_arguments:
        with pytest.raises(ReadToolError):
            filesystem.project_test_summary(cast(JsonObject, arguments))


def test_project_docs_summary_returns_count_only_metadata(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("README.md").write_text("# Secret Project\n", encoding="utf-8")
    root.joinpath("docs").mkdir()
    root.joinpath("docs", "api.md").write_text("TOKEN = secret\n", encoding="utf-8")
    root.joinpath("docs", "tutorial.rst").write_text("private\n", encoding="utf-8")
    root.joinpath("src").mkdir()
    root.joinpath("src", "usage.md").write_text("internal\n", encoding="utf-8")
    root.joinpath(".env").write_text("TOKEN=secret", encoding="utf-8")
    root.joinpath(".git").mkdir()
    root.joinpath(".git", "config").write_text("[remote]\n", encoding="utf-8")

    summary = filesystem.project_docs_summary({"root": ".", "max_depth": 3, "limit": 30})

    assert summary["tool_name"] == "project.docs.summary"
    assert summary["summary"] == {
        "visible_documentation_directory_count": 1,
        "visible_documentation_file_count": 4,
        "max_observed_depth": 2,
        "inspected_entry_count": 8,
    }
    assert cast(dict[str, int], summary["documentation_type_counts"])["readme_docs"] == 1
    assert cast(dict[str, int], summary["documentation_type_counts"])["api_docs"] == 1
    assert cast(dict[str, int], summary["documentation_type_counts"])["tutorial_docs"] == 1
    assert cast(dict[str, int], summary["documentation_type_counts"])["unknown_docs"] == 1
    assert (
        cast(dict[str, int], summary["documentation_location_counts"])["root_documentation"] == 1
    )
    assert (
        cast(dict[str, int], summary["documentation_location_counts"])[
            "dedicated_docs_directory"
        ]
        == 3
    )
    assert (
        cast(dict[str, int], summary["documentation_location_counts"])[
            "source_adjacent_documentation"
        ]
        == 1
    )
    assert cast(dict[str, int], summary["language_family_counts"])["markdown"] == 3
    assert cast(dict[str, int], summary["language_family_counts"])["restructured_text"] == 1
    assert cast(dict[str, int], summary["skipped_counts"])["hidden_or_sensitive"] == 1
    assert cast(dict[str, int], summary["skipped_counts"])["git_internal"] == 1
    output_policy = cast(dict[str, object], summary["output_policy"])
    assert output_policy["file_contents_included"] is False
    assert output_policy["documentation_file_names_included"] is False
    assert output_policy["documentation_headings_included"] is False
    assert output_policy["raw_paths_included"] is False
    assert output_policy["documentation_build_execution_used"] is False
    assert output_policy["package_manager_execution_used"] is False
    dumped = json_dump(summary)
    assert "README" not in dumped
    assert "api.md" not in dumped
    assert "Secret Project" not in dumped
    assert "TOKEN" not in dumped
    assert ".env" not in dumped
    assert ".git" not in dumped


def test_project_docs_summary_honors_limits_and_include_categories(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("docs").mkdir()
    root.joinpath("docs", "api.md").write_text("secret\n", encoding="utf-8")
    root.joinpath("README.md").write_text("secret\n", encoding="utf-8")

    summary = filesystem.project_docs_summary(
        {
            "root": ".",
            "max_depth": 1,
            "limit": 1,
            "include_categories": ["skipped_counts"],
        }
    )

    assert "documentation_type_counts" not in summary
    assert "documentation_location_counts" not in summary
    assert "language_family_counts" not in summary
    assert "skipped_counts" in summary
    assert summary["truncated"] is True
    assert cast(dict[str, int], summary["skipped_counts"])["item_limit"] >= 1


def test_project_docs_summary_skips_symlink_and_hardlink_entries(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    docs = root / "docs"
    docs.mkdir()
    target = docs / "api.md"
    target.write_text("private\n", encoding="utf-8")
    try:
        os.link(target, docs / "api-copy.md")
    except OSError:
        pytest.skip("hardlinks are not supported on this filesystem")
    outside = tmp_path / "outside"
    outside.mkdir()
    root.joinpath("outside-link").symlink_to(outside)

    summary = filesystem.project_docs_summary({"root": ".", "max_depth": 2, "limit": 20})

    skipped = cast(dict[str, int], summary["skipped_counts"])
    assert skipped["hardlink"] == 2
    assert skipped["symlink"] == 1
    dumped = json_dump(summary)
    assert "private" not in dumped
    assert "outside" not in dumped


def test_project_docs_summary_rejects_unsupported_arguments(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    denied_arguments = [
        {"path": "."},
        {"root": "../outside"},
        {"root": "/tmp"},
        {"root": "bad\x1fpath"},
        {"max_depth": -1},
        {"max_depth": 6},
        {"limit": 0},
        {"limit": 301},
        {"include_categories": []},
        {"include_categories": ["documentation_type_counts", "documentation_type_counts"]},
        {"include_categories": ["raw_names"]},
        {"glob": "**/*"},
        {"regex": ".*"},
        {"recursive": True},
        {"include_file_contents": True},
        {"include_file_names": True},
        {"include_documentation_file_names": True},
        {"include_documentation_headings": True},
        {"include_dependency_names": True},
        {"include_package_names": True},
        {"include_script_values": True},
        {"include_coverage": True},
        {"build_docs": True},
        {"execute_docs": True},
        {"registry_url": "https://registry.example.test"},
        {"command": "mkdocs build"},
        {"argv": ["mkdocs", "build"]},
    ]

    for arguments in denied_arguments:
        with pytest.raises(ReadToolError):
            filesystem.project_docs_summary(cast(JsonObject, arguments))


def test_project_language_summary_returns_count_only_metadata(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("main.py").write_text("SECRET = 'token'\n", encoding="utf-8")
    root.joinpath("src").mkdir()
    root.joinpath("src", "app.ts").write_text("const secret = 'private';\n", encoding="utf-8")
    root.joinpath("src", "view.html").write_text("<h1>private</h1>\n", encoding="utf-8")
    root.joinpath("tests").mkdir()
    root.joinpath("tests", "test_app.py").write_text("def test_secret(): pass\n", encoding="utf-8")
    root.joinpath("docs").mkdir()
    root.joinpath("docs", "guide.md").write_text("# Secret\n", encoding="utf-8")
    root.joinpath("config").mkdir()
    root.joinpath("config", "app.yaml").write_text("token: private\n", encoding="utf-8")
    root.joinpath("data.bin").write_bytes(b"\x00\x01")
    root.joinpath(".env").write_text("TOKEN=secret", encoding="utf-8")
    root.joinpath(".git").mkdir()
    root.joinpath(".git", "config").write_text("[remote]\n", encoding="utf-8")

    summary = filesystem.project_language_summary({"root": ".", "max_depth": 3, "limit": 40})

    assert summary["tool_name"] == "project.language.summary"
    assert summary["summary"] == {
        "visible_source_directory_count": 4,
        "visible_source_like_file_count": 6,
        "max_observed_depth": 2,
        "inspected_entry_count": 13,
    }
    assert cast(dict[str, int], summary["language_family_counts"])["python"] == 2
    assert cast(dict[str, int], summary["language_family_counts"])["typescript"] == 1
    assert cast(dict[str, int], summary["language_family_counts"])["markup"] == 1
    assert cast(dict[str, int], summary["language_family_counts"])["documentation"] == 1
    assert cast(dict[str, int], summary["language_family_counts"])["configuration"] == 1
    assert cast(dict[str, int], summary["extension_family_counts"])["source_code"] == 3
    assert cast(dict[str, int], summary["extension_family_counts"])["markup"] == 1
    assert cast(dict[str, int], summary["extension_family_counts"])["documentation"] == 1
    assert cast(dict[str, int], summary["extension_family_counts"])["configuration"] == 1
    assert cast(dict[str, int], summary["source_location_counts"])["root_level"] == 1
    assert cast(dict[str, int], summary["source_location_counts"])["source_directory"] == 2
    assert cast(dict[str, int], summary["source_location_counts"])["test_directory"] == 1
    assert cast(dict[str, int], summary["source_location_counts"])["docs_directory"] == 1
    assert cast(dict[str, int], summary["source_location_counts"])["config_directory"] == 1
    assert cast(dict[str, int], summary["skipped_counts"])["hidden_or_sensitive"] == 1
    assert cast(dict[str, int], summary["skipped_counts"])["git_internal"] == 1
    output_policy = cast(dict[str, object], summary["output_policy"])
    assert output_policy["file_contents_included"] is False
    assert output_policy["language_file_names_included"] is False
    assert output_policy["raw_paths_included"] is False
    assert output_policy["raw_extensions_included"] is False
    assert output_policy["dependency_names_included"] is False
    assert output_policy["language_detector_execution_used"] is False
    assert output_policy["package_manager_execution_used"] is False
    dumped = json_dump(summary)
    assert "main.py" not in dumped
    assert "app.ts" not in dumped
    assert ".py" not in dumped
    assert "SECRET" not in dumped
    assert "TOKEN" not in dumped
    assert ".env" not in dumped
    assert ".git" not in dumped


def test_project_language_summary_honors_limits_and_include_categories(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("src").mkdir()
    root.joinpath("src", "app.py").write_text("private\n", encoding="utf-8")
    root.joinpath("README.md").write_text("private\n", encoding="utf-8")

    summary = filesystem.project_language_summary(
        {
            "root": ".",
            "max_depth": 1,
            "limit": 1,
            "include_categories": ["skipped_counts"],
        }
    )

    assert "language_family_counts" not in summary
    assert "extension_family_counts" not in summary
    assert "source_location_counts" not in summary
    assert "skipped_counts" in summary
    assert summary["truncated"] is True
    assert cast(dict[str, int], summary["skipped_counts"])["item_limit"] >= 1


def test_project_language_summary_skips_symlink_and_hardlink_entries(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    src = root / "src"
    src.mkdir()
    target = src / "app.py"
    target.write_text("private\n", encoding="utf-8")
    try:
        os.link(target, src / "app-copy.py")
    except OSError:
        pytest.skip("hardlinks are not supported on this filesystem")
    outside = tmp_path / "outside"
    outside.mkdir()
    root.joinpath("outside-link").symlink_to(outside)

    summary = filesystem.project_language_summary({"root": ".", "max_depth": 2, "limit": 20})

    skipped = cast(dict[str, int], summary["skipped_counts"])
    assert skipped["hardlink"] == 2
    assert skipped["symlink"] == 1
    dumped = json_dump(summary)
    assert "private" not in dumped
    assert "outside" not in dumped


def test_project_language_summary_rejects_unsupported_arguments(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    denied_arguments = [
        {"path": "."},
        {"root": "../outside"},
        {"root": "/tmp"},
        {"root": "bad\x1fpath"},
        {"max_depth": -1},
        {"max_depth": 6},
        {"limit": 0},
        {"limit": 301},
        {"include_categories": []},
        {"include_categories": ["language_family_counts", "language_family_counts"]},
        {"include_categories": ["raw_extensions"]},
        {"glob": "**/*"},
        {"regex": ".*"},
        {"recursive": True},
        {"include_file_contents": True},
        {"include_file_names": True},
        {"include_language_file_names": True},
        {"include_raw_extensions": True},
        {"include_dependency_names": True},
        {"include_package_names": True},
        {"include_script_values": True},
        {"include_coverage": True},
        {"detect_languages": True},
        {"execute_detector": True},
        {"registry_url": "https://registry.example.test"},
        {"command": "detect-languages"},
        {"argv": ["detect-languages"]},
    ]

    for arguments in denied_arguments:
        with pytest.raises(ReadToolError):
            filesystem.project_language_summary(cast(JsonObject, arguments))


def test_project_config_summary_returns_count_only_metadata(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("pyproject.toml").write_text("[project]\nname='secret'\n", encoding="utf-8")
    root.joinpath("vite.config.ts").write_text(
        "export default { secret: true }\n",
        encoding="utf-8",
    )
    root.joinpath("pytest.ini").write_text("[pytest]\naddopts=-q\n", encoding="utf-8")
    root.joinpath("eslint.config.js").write_text("const token = 'secret'\n", encoding="utf-8")
    root.joinpath("docker-compose.yml").write_text("services:\n  app:\n", encoding="utf-8")
    root.joinpath("config").mkdir()
    root.joinpath("config", "app.yaml").write_text("token: private\n", encoding="utf-8")
    root.joinpath("src").mkdir()
    root.joinpath("src", "settings.ini").write_text("password=secret\n", encoding="utf-8")
    root.joinpath("data.bin").write_bytes(b"\x00\x01")
    root.joinpath(".env").write_text("TOKEN=secret", encoding="utf-8")
    root.joinpath(".git").mkdir()
    root.joinpath(".git", "config").write_text("[remote]\n", encoding="utf-8")

    summary = filesystem.project_config_summary({"root": ".", "max_depth": 3, "limit": 40})

    assert summary["tool_name"] == "project.config.summary"
    assert summary["summary"] == {
        "visible_config_directory_count": 1,
        "visible_config_like_file_count": 7,
        "max_observed_depth": 2,
        "inspected_entry_count": 12,
    }
    assert cast(dict[str, int], summary["config_category_counts"])["build_config"] == 2
    assert cast(dict[str, int], summary["config_category_counts"])["test_config"] == 1
    assert cast(dict[str, int], summary["config_category_counts"])["lint_format_config"] == 1
    assert cast(dict[str, int], summary["config_category_counts"])["runtime_app_config"] == 2
    assert (
        cast(dict[str, int], summary["config_category_counts"])["container_deployment_config"]
        == 1
    )
    assert cast(dict[str, int], summary["config_location_counts"])["root_level"] == 5
    assert cast(dict[str, int], summary["config_location_counts"])["config_directory"] == 1
    assert cast(dict[str, int], summary["config_location_counts"])["source_adjacent_config"] == 1
    assert cast(dict[str, int], summary["skipped_counts"])["hidden_or_sensitive"] == 1
    assert cast(dict[str, int], summary["skipped_counts"])["git_internal"] == 1
    output_policy = cast(dict[str, object], summary["output_policy"])
    assert output_policy["file_contents_included"] is False
    assert output_policy["config_file_names_included"] is False
    assert output_policy["config_contents_included"] is False
    assert output_policy["config_values_included"] is False
    assert output_policy["raw_paths_included"] is False
    assert output_policy["environment_names_or_values_included"] is False
    assert output_policy["config_parser_execution_used"] is False
    dumped = json_dump(summary)
    assert "pyproject" not in dumped
    assert "vite.config" not in dumped
    assert "app.yaml" not in dumped
    assert "settings.ini" not in dumped
    assert "secret" not in dumped
    assert "TOKEN" not in dumped
    assert ".env" not in dumped
    assert ".git" not in dumped


def test_project_config_summary_honors_limits_and_include_categories(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("config").mkdir()
    root.joinpath("config", "app.yaml").write_text("private\n", encoding="utf-8")
    root.joinpath("pyproject.toml").write_text("private\n", encoding="utf-8")

    summary = filesystem.project_config_summary(
        {
            "root": ".",
            "max_depth": 1,
            "limit": 1,
            "include_categories": ["skipped_counts"],
        }
    )

    assert "config_category_counts" not in summary
    assert "config_location_counts" not in summary
    assert "skipped_counts" in summary
    assert summary["truncated"] is True
    assert cast(dict[str, int], summary["skipped_counts"])["item_limit"] >= 1


def test_project_config_summary_skips_symlink_and_hardlink_entries(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    config = root / "config"
    config.mkdir()
    target = config / "app.yaml"
    target.write_text("private\n", encoding="utf-8")
    try:
        os.link(target, config / "app-copy.yaml")
    except OSError:
        pytest.skip("hardlinks are not supported on this filesystem")
    outside = tmp_path / "outside"
    outside.mkdir()
    root.joinpath("outside-link").symlink_to(outside)

    summary = filesystem.project_config_summary({"root": ".", "max_depth": 2, "limit": 20})

    skipped = cast(dict[str, int], summary["skipped_counts"])
    assert skipped["hardlink"] == 2
    assert skipped["symlink"] == 1
    dumped = json_dump(summary)
    assert "private" not in dumped
    assert "outside" not in dumped


def test_project_config_summary_rejects_unsupported_arguments(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    denied_arguments = [
        {"path": "."},
        {"root": "../outside"},
        {"root": "/tmp"},
        {"root": "%2e%2e/outside"},
        {"root": "bad\x1fpath"},
        {"max_depth": -1},
        {"max_depth": 6},
        {"limit": 0},
        {"limit": 301},
        {"include_categories": []},
        {"include_categories": ["config_category_counts", "config_category_counts"]},
        {"include_categories": ["raw_names"]},
        {"glob": "**/*"},
        {"regex": ".*"},
        {"recursive": True},
        {"include_file_contents": True},
        {"include_file_names": True},
        {"include_config_file_names": True},
        {"include_config_contents": True},
        {"include_config_values": True},
        {"include_dependency_names": True},
        {"include_package_names": True},
        {"include_script_values": True},
        {"include_environment": True},
        {"parse_config": True},
        {"execute_parser": True},
        {"registry_url": "https://registry.example.test"},
        {"command": "npm config list"},
        {"argv": ["npm", "config", "list"]},
    ]

    for arguments in denied_arguments:
        with pytest.raises(ReadToolError):
            filesystem.project_config_summary(cast(JsonObject, arguments))


def test_project_dependency_summary_counts_multiple_ecosystems(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    root = filesystem.workspace_root
    root.joinpath("pyproject.toml").write_text(
        """
[project]
dependencies = ["private-lib==1.0", "another-lib"]
[project.optional-dependencies]
dev = ["pytest"]
[project.scripts]
private-cli = "private.module:main"
""",
        encoding="utf-8",
    )
    root.joinpath("requirements.txt").write_text(
        "private-lib==1.0\n--index-url https://secret.example/simple\nvisible\n",
        encoding="utf-8",
    )

    summary = filesystem.project_dependency_summary(
        {"manifest_kinds": ["pyproject.toml", "requirements.txt"]}
    )

    assert summary["total_direct_dependency_count"] == 5
    assert summary["ecosystem_counts"] == {"python": 2}
    assert summary["manifest_kind_counts"] == {
        "pyproject.toml": 1,
        "requirements.txt": 1,
    }
    dumped = json_dump(summary)
    assert "private-lib" not in dumped
    assert "secret.example" not in dumped
    assert "private-cli" not in dumped


def test_project_dependency_summary_rejects_unsupported_arguments(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    denied_arguments = [
        {"path": "package.json"},
        {"root": "../outside"},
        {"root": "/tmp"},
        {"manifest_kinds": ["package.json", "package.json"]},
        {"manifest_kinds": []},
        {"glob": "**/package.json"},
        {"recursive": True},
        {"include_file_contents": True},
        {"include_dependency_names": True},
        {"include_versions": True},
        {"include_lockfile_contents": True},
        {"include_script_values": True},
        {"registry_url": "https://registry.example.test"},
        {"command": "npm install"},
        {"argv": ["npm", "ls"]},
        {"limit": 0},
        {"limit": 21},
    ]

    for arguments in denied_arguments:
        with pytest.raises(ReadToolError):
            filesystem.project_dependency_summary(cast(JsonObject, arguments))


def test_project_dependency_summary_malformed_manifest_fails_safely(tmp_path: Path) -> None:
    filesystem = make_filesystem(tmp_path, max_read_bytes=4096)
    filesystem.workspace_root.joinpath("package.json").write_text(
        '{"dependencies":{"private-package":"1.0"', encoding="utf-8"
    )

    summary = filesystem.project_dependency_summary({"manifest_kinds": ["package.json"]})

    manifest = cast(list[dict[str, object]], summary["manifests"])[0]
    assert manifest["parse_status"] == "parse_failed"
    assert manifest["parse_error_reason"] == "manifest parse failed safely"
    assert manifest["direct_dependency_count"] == 0
    assert "private-package" not in json_dump(summary)


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

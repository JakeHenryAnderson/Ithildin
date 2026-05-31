from __future__ import annotations

import difflib
import os
import unicodedata
from pathlib import Path

import pytest
from ithildin_api.patches import PatchProposalError, PatchProposalService, PatchProposalStore
from ithildin_api.read_tools import FilesystemReadTools


def make_service(tmp_path: Path, *, max_patch_bytes: int = 4096) -> PatchProposalService:
    filesystem = FilesystemReadTools(
        workspace_root=tmp_path / "workspace",
        max_read_bytes=4096,
        search_result_limit=10,
    )
    store = PatchProposalStore(tmp_path / "ithildin.sqlite3")
    store.initialize()
    return PatchProposalService(store, filesystem, max_patch_bytes)


def make_multi_workspace_service(tmp_path: Path) -> PatchProposalService:
    alpha = FilesystemReadTools(
        workspace_root=tmp_path / "alpha",
        max_read_bytes=4096,
        search_result_limit=10,
        workspace_id="alpha",
    )
    beta = FilesystemReadTools(
        workspace_root=tmp_path / "beta",
        max_read_bytes=4096,
        search_result_limit=10,
        workspace_id="beta",
    )
    store = PatchProposalStore(tmp_path / "ithildin.sqlite3")
    store.initialize()
    return PatchProposalService(
        store,
        alpha,
        4096,
        {"alpha": alpha, "beta": beta},
        "alpha",
    )


def unified_diff(path: str, before: str, after: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
        )
    )


def test_valid_unified_diff_proposal_is_stored_with_stable_hash(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    target = service.filesystem.workspace_root / "README.md"
    target.write_text("old\n", encoding="utf-8")
    diff = unified_diff("README.md", "old\n", "new\n")

    first = service.create_proposal(
        request_id="req_1",
        principal={"id": "agent:test"},
        path="README.md",
        unified_diff=diff,
    )
    second = service.create_proposal(
        request_id="req_2",
        principal={"id": "agent:test"},
        path="README.md",
        unified_diff=diff,
    )

    assert first.proposal_id.startswith("patch_")
    assert first.workspace_id == "default"
    assert first.path == "README.md"
    assert first.status == "proposed"
    assert first.base_file_hash == second.base_file_hash
    assert first.proposal_hash == second.proposal_hash
    assert service.get_proposal(first.proposal_id).proposal_hash == first.proposal_hash
    assert [proposal.proposal_id for proposal in service.list_proposals()] == [
        first.proposal_id,
        second.proposal_id,
    ]


def test_proposal_hash_and_storage_bind_workspace_id(tmp_path: Path) -> None:
    service = make_multi_workspace_service(tmp_path)
    for filesystem in service.filesystems.values():
        filesystem.workspace_root.joinpath("README.md").write_text("old\n", encoding="utf-8")
    diff = unified_diff("README.md", "old\n", "new\n")

    alpha = service.create_proposal(
        request_id="req_1",
        principal={"id": "agent:test"},
        path="README.md",
        unified_diff=diff,
        workspace_id="alpha",
    )
    beta = service.create_proposal(
        request_id="req_2",
        principal={"id": "agent:test"},
        path="README.md",
        unified_diff=diff,
        workspace_id="beta",
    )

    assert alpha.workspace_id == "alpha"
    assert beta.workspace_id == "beta"
    assert alpha.proposal_hash != beta.proposal_hash
    assert service.get_proposal(beta.proposal_id).workspace_id == "beta"


def test_invalid_patch_paths_are_denied(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    service.filesystem.workspace_root.joinpath("README.md").write_text("old\n", encoding="utf-8")
    service.filesystem.workspace_root.joinpath(".env").write_text("TOKEN=secret", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("old\n", encoding="utf-8")
    service.filesystem.workspace_root.joinpath("link.txt").symlink_to(outside)
    diff = unified_diff("README.md", "old\n", "new\n")

    for path, reason in [
        ("../README.md", "traversal"),
        (str(outside), "absolute"),
        ("link.txt", "symlink"),
        (".env", "hidden or sensitive"),
        ("..%2fREADME.md", "encoded path tokens"),
        (unicodedata.normalize("NFD", "café.txt"), "Unicode-normalized"),
    ]:
        with pytest.raises(PatchProposalError, match=reason):
            service.create_proposal(
                request_id="req_1",
                principal={"id": "agent:test"},
                path=path,
                unified_diff=diff,
            )

    try:
        os.link(
            service.filesystem.workspace_root / "README.md",
            service.filesystem.workspace_root / "README-hardlink.md",
        )
    except OSError as exc:
        pytest.skip(f"hardlinks unavailable: {exc}")
    with pytest.raises(PatchProposalError, match="hardlinked"):
        service.create_proposal(
            request_id="req_1",
            principal={"id": "agent:test"},
            path="README.md",
            unified_diff=diff,
        )


def test_patch_proposal_denies_symlink_swap_before_file_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not hasattr(os, "O_NOFOLLOW"):
        pytest.skip("O_NOFOLLOW unavailable on this platform")
    service = make_service(tmp_path)
    target = service.filesystem.workspace_root / "README.md"
    target.write_text("old\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    diff = unified_diff("README.md", "old\n", "new\n")
    original_resolver = service.filesystem.resolve_existing_path

    def swap_to_symlink(path: str) -> Path:
        resolved = original_resolver(path)
        if path == "README.md":
            resolved.unlink()
            resolved.symlink_to(outside)
        return resolved

    monkeypatch.setattr(service.filesystem, "resolve_existing_path", swap_to_symlink)

    with pytest.raises(PatchProposalError, match="safe regular file"):
        service.create_proposal(
            request_id="req_1",
            principal={"id": "agent:test"},
            path="README.md",
            unified_diff=diff,
        )

    assert outside.read_text(encoding="utf-8") == "outside\n"


@pytest.mark.parametrize(
    ("swap_kind", "expected_reason"),
    [
        ("missing", "patch target is not a file"),
        ("directory", "patch target is not a file"),
        ("binary", "binary"),
        ("oversized", "read limit"),
        ("symlink", "safe regular file"),
    ],
)
def test_patch_proposal_denies_bounded_target_swaps_before_file_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    swap_kind: str,
    expected_reason: str,
) -> None:
    if swap_kind == "symlink" and not hasattr(os, "O_NOFOLLOW"):
        pytest.skip("O_NOFOLLOW unavailable on this platform")
    service = make_service(tmp_path)
    service.filesystem.max_read_bytes = 8
    target = service.filesystem.workspace_root / "README.md"
    target.write_text("old\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    diff = unified_diff("README.md", "old\n", "new\n")
    original_resolver = service.filesystem.resolve_existing_path

    def swap_target(path: str) -> Path:
        resolved = original_resolver(path)
        if path == "README.md":
            resolved.unlink()
            if swap_kind == "directory":
                resolved.mkdir()
            elif swap_kind == "binary":
                resolved.write_bytes(b"old\x00")
            elif swap_kind == "oversized":
                resolved.write_text("too large\n", encoding="utf-8")
            elif swap_kind == "symlink":
                resolved.symlink_to(outside)
        return resolved

    monkeypatch.setattr(service.filesystem, "resolve_existing_path", swap_target)

    with pytest.raises(PatchProposalError, match=expected_reason):
        service.create_proposal(
            request_id="req_1",
            principal={"id": "agent:test"},
            path="README.md",
            unified_diff=diff,
        )

    assert outside.read_text(encoding="utf-8") == "outside\n"


def test_invalid_diff_shapes_are_denied(tmp_path: Path) -> None:
    service = make_service(tmp_path, max_patch_bytes=200)
    service.filesystem.workspace_root.joinpath("README.md").write_text("old\n", encoding="utf-8")

    invalid_diffs = [
        "not a diff",
        "Binary files a/README.md and b/README.md differ\n",
        "--- a/README.md\n+++ b/other.md\n@@ -1 +1 @@\n-old\n+new\n",
        "--- /dev/null\n+++ b/README.md\n@@ -0,0 +1 @@\n+new\n",
        "rename from README.md\nrename to OTHER.md\n--- a/README.md\n+++ b/README.md\n",
        "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-stale\n+new\n",
        unified_diff("README.md", "old\n", "new\n") + ("x" * 300),
    ]

    for invalid_diff in invalid_diffs:
        with pytest.raises(PatchProposalError):
            service.create_proposal(
                request_id="req_1",
                principal={"id": "agent:test"},
                path="README.md",
                unified_diff=invalid_diff,
            )

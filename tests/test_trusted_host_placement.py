from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from ithildin_api.trusted_host_placement import (
    TrustedHostPlacement,
    TrustedHostPlacementError,
    descriptor_relative_placement_supported,
)

pytestmark = pytest.mark.skipif(
    not descriptor_relative_placement_supported(),
    reason="descriptor-relative placement primitives are unavailable",
)


def test_descriptor_relative_placement_writes_and_hashes_retained_buffer(
    tmp_path: Path,
) -> None:
    root = tmp_path / "staging"
    root.mkdir()
    data = b"governed artifact\n"

    with TrustedHostPlacement(root) as placement:
        result = placement.place(
            data,
            workspace_id="default",
            proposal_id="thp_1234",
            destination_leaf="thpa_1234-artifact.artifact",
        )

    destination = root / "default" / "thp_1234" / "thpa_1234-artifact.artifact"
    assert destination.read_bytes() == data
    assert result.staged_sha256.startswith("sha256:")
    assert destination.stat().st_nlink == 1
    assert destination.stat().st_mode & 0o777 == 0o600


def test_descriptor_relative_placement_is_create_exclusive_under_concurrency(
    tmp_path: Path,
) -> None:
    root = tmp_path / "staging"
    root.mkdir()

    def place() -> str:
        try:
            with TrustedHostPlacement(root) as placement:
                placement.place(
                    b"same bytes\n",
                    workspace_id="default",
                    proposal_id="thp_replay",
                    destination_leaf="thpa_replay-artifact.artifact",
                )
        except TrustedHostPlacementError as exc:
            return exc.reason
        return "placed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: place(), range(2)))

    assert sorted(outcomes) == ["destination_conflict", "placed"]
    destination_dir = root / "default" / "thp_replay"
    assert len(list(destination_dir.iterdir())) == 1


@pytest.mark.parametrize("leaf_kind", ["file", "directory", "symlink", "hardlink"])
def test_descriptor_relative_placement_preserves_existing_leaf(
    tmp_path: Path,
    leaf_kind: str,
) -> None:
    root = tmp_path / "staging"
    destination_dir = root / "default" / "thp_conflict"
    destination_dir.mkdir(parents=True)
    destination = destination_dir / "thpa_conflict-artifact.artifact"
    if leaf_kind == "file":
        destination.write_bytes(b"existing")
    elif leaf_kind == "directory":
        destination.mkdir()
    elif leaf_kind == "symlink":
        destination.symlink_to(tmp_path / "elsewhere")
    else:
        source = tmp_path / "hardlink-source"
        source.write_bytes(b"existing")
        os.link(source, destination)

    with TrustedHostPlacement(root) as placement:
        with pytest.raises(TrustedHostPlacementError, match="destination_conflict"):
            placement.place(
                b"new bytes",
                workspace_id="default",
                proposal_id="thp_conflict",
                destination_leaf=destination.name,
            )

    if leaf_kind in {"file", "hardlink"}:
        assert destination.read_bytes() == b"existing"


def test_descriptor_relative_placement_rejects_symlink_ancestor(tmp_path: Path) -> None:
    root = tmp_path / "staging"
    root.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    root.joinpath("default").symlink_to(elsewhere, target_is_directory=True)

    with TrustedHostPlacement(root) as placement:
        with pytest.raises(TrustedHostPlacementError, match="destination_ancestor_unsafe"):
            placement.place(
                b"bytes",
                workspace_id="default",
                proposal_id="thp_symlink",
                destination_leaf="thpa_symlink-artifact.artifact",
            )

    assert list(elsewhere.iterdir()) == []


def test_descriptor_relative_placement_rejects_writable_managed_root(tmp_path: Path) -> None:
    root = tmp_path / "staging"
    root.mkdir(mode=0o700)
    root.chmod(0o777)
    with pytest.raises(TrustedHostPlacementError, match="staging_root_unsafe"):
        TrustedHostPlacement(root)


def test_descriptor_relative_placement_rejects_root_permission_drift(tmp_path: Path) -> None:
    root = tmp_path / "staging"
    root.mkdir(mode=0o700)
    with TrustedHostPlacement(root) as placement:
        root.chmod(0o777)
        with pytest.raises(TrustedHostPlacementError) as exc_info:
            placement.place(
                b"bytes",
                workspace_id="default",
                proposal_id="thp_permissions",
                destination_leaf="thpa_permissions-artifact.artifact",
            )
    assert exc_info.value.reason == "staging_root_namespace_drift"
    assert exc_info.value.effect_possible is False
    assert list(root.iterdir()) == []


def test_descriptor_relative_placement_rejects_writable_destination_ancestor(
    tmp_path: Path,
) -> None:
    root = tmp_path / "staging"
    root.mkdir(mode=0o700)
    workspace = root / "default"
    workspace.mkdir(mode=0o700)
    workspace.chmod(0o777)
    with TrustedHostPlacement(root) as placement:
        with pytest.raises(TrustedHostPlacementError, match="destination_ancestor_unsafe"):
            placement.place(
                b"bytes",
                workspace_id="default",
                proposal_id="thp_permissions",
                destination_leaf="thpa_permissions-artifact.artifact",
            )


@pytest.mark.parametrize("component", ["../escape", "nested/path", "..", "bad\\path"])
def test_descriptor_relative_placement_rejects_traversal_component(
    tmp_path: Path,
    component: str,
) -> None:
    root = tmp_path / "staging"
    root.mkdir()
    with TrustedHostPlacement(root) as placement:
        with pytest.raises(TrustedHostPlacementError, match="destination_component_unsafe"):
            placement.place(
                b"bytes",
                workspace_id=component,
                proposal_id="thp_safe",
                destination_leaf="thpa_safe-artifact.artifact",
            )


def test_staging_root_replacement_before_first_effect_fails_without_placement(
    tmp_path: Path,
) -> None:
    root = tmp_path / "staging"
    retained = tmp_path / "retained"
    root.mkdir()
    with TrustedHostPlacement(root) as placement:
        root.rename(retained)
        root.mkdir()
        with pytest.raises(TrustedHostPlacementError) as exc_info:
            placement.place(
                b"bytes",
                workspace_id="default",
                proposal_id="thp_root_drift",
                destination_leaf="thpa_root-drift.artifact",
            )

    assert exc_info.value.reason == "staging_root_namespace_drift"
    assert exc_info.value.effect_possible is False
    assert list(root.iterdir()) == []
    assert list(retained.iterdir()) == []


def test_staging_root_replacement_after_write_requires_recovery(tmp_path: Path) -> None:
    root = tmp_path / "staging"
    retained = tmp_path / "retained"
    root.mkdir()

    def replace_root() -> None:
        root.rename(retained)
        root.mkdir()

    with TrustedHostPlacement(root, after_write_hook=replace_root) as placement:
        with pytest.raises(TrustedHostPlacementError) as exc_info:
            placement.place(
                b"bytes",
                workspace_id="default",
                proposal_id="thp_postwrite_drift",
                destination_leaf="thpa_postwrite-drift.artifact",
            )

    assert exc_info.value.reason == "staging_root_namespace_drift"
    assert exc_info.value.effect_possible is True
    assert list(root.iterdir()) == []
    assert (
        retained
        / "default"
        / "thp_postwrite_drift"
        / "thpa_postwrite-drift.artifact"
    ).read_bytes() == b"bytes"


def test_descriptor_relative_capability_fails_closed_without_dir_fd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(os, "supports_dir_fd", set())
    assert descriptor_relative_placement_supported() is False

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from scripts import local_v1_operations_rehearsal as operations
from scripts import local_v1_operations_rehearsal_check as operations_check


def test_compose_document_is_loopback_only_read_only_and_has_no_docker_socket(
    tmp_path: Path,
) -> None:
    document = operations.compose_document(
        state_root=tmp_path / "state",
        workspace_root=tmp_path / "workspaces",
        api_port=18080,
        ui_port=15173,
        api_image="ithildin/api:test",
        ui_image="ithildin/ui:test",
        token="synthetic-test-token",
    )
    serialized = json.dumps(document)
    api = document["services"]["ithildin-api"]
    ui = document["services"]["ithildin-ui"]

    assert api["ports"] == ["127.0.0.1:18080:8000"]
    assert ui["ports"] == ["127.0.0.1:15173:8080"]
    assert api["read_only"] is True
    assert ui["read_only"] is True
    assert api["cap_drop"] == ["ALL"]
    assert ui["cap_drop"] == ["ALL"]
    assert "/var/run/docker.sock" not in serialized
    assert document["services"].keys() == {"ithildin-api", "ithildin-ui"}


def test_snapshot_copy_round_trip_is_digest_exact_and_private(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    source.joinpath("nested").mkdir()
    source.joinpath("nested/state.sqlite3").write_bytes(b"synthetic sqlite")
    source.joinpath("audit.jsonl").write_text('{"event":"synthetic"}\n', encoding="utf-8")
    destination = tmp_path / "destination"

    operations._copy_regular_tree(source, destination)  # noqa: SLF001

    assert operations.snapshot_manifest({"state": source}) == operations.snapshot_manifest(
        {"state": destination}
    )
    assert stat.S_IMODE(destination.stat().st_mode) == 0o700
    assert all(
        stat.S_IMODE(path.stat().st_mode) == 0o600
        for path in destination.rglob("*")
        if path.is_file()
    )


def test_copy_rejects_symlink_and_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    target.write_text("synthetic", encoding="utf-8")
    source.joinpath("link").symlink_to(target)

    with pytest.raises(operations.OperationsError, match="symlink"):
        operations._copy_regular_tree(source, tmp_path / "copy")  # noqa: SLF001

    clean_source = tmp_path / "clean"
    clean_source.mkdir()
    destination = tmp_path / "existing"
    destination.mkdir()
    with pytest.raises(operations.OperationsError, match="destination"):
        operations._copy_regular_tree(clean_source, destination)  # noqa: SLF001


def test_private_json_refuses_overwrite_and_uses_owner_only_mode(tmp_path: Path) -> None:
    target = tmp_path / "private.json"

    operations._write_private_json(target, {"safe": True})  # noqa: SLF001

    assert stat.S_IMODE(os.lstat(target).st_mode) == 0o600
    with pytest.raises(FileExistsError):
        operations._write_private_json(target, {"safe": False})  # noqa: SLF001


@pytest.mark.parametrize("port", [0, 1023, 65536])
def test_port_validation_rejects_unsafe_values(port: int) -> None:
    with pytest.raises(ValueError, match="between 1024 and 65535"):
        operations._require_port(port)  # noqa: SLF001


def test_checker_rejects_unconfined_report(tmp_path: Path) -> None:
    failures = operations_check.validate_report(
        tmp_path / operations.REPORT_NAME,
        expected_candidate="a" * 40,
    )

    assert failures == ["report_path_not_confined"]

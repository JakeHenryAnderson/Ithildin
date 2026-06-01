from __future__ import annotations

from pathlib import Path

import pytest
from ithildin_api.read_tools import ReadToolError, ReadToolExecutor
from ithildin_api.workspaces import WorkspaceRegistry, WorkspaceRegistryError


def write_registry(path: Path, root_a: Path, root_b: Path) -> None:
    path.write_text(
        f"""
version: test-workspaces-v1
default_workspace_id: alpha
workspaces:
  - id: alpha
    root: {root_a.as_posix()}
    display_name: Alpha
    enabled: true
  - id: beta
    root: {root_b.as_posix()}
    display_name: Beta
    enabled: true
""",
        encoding="utf-8",
    )


def test_workspace_registry_loads_and_reports_status(tmp_path: Path) -> None:
    registry_path = tmp_path / "workspaces.yaml"
    write_registry(registry_path, tmp_path / "alpha", tmp_path / "beta")

    registry = WorkspaceRegistry.load(
        registry_path,
        require_registry=True,
        fallback_root=tmp_path / "fallback",
        default_workspace_id="alpha",
    )

    assert registry.default_workspace_id == "alpha"
    assert registry.resolve_active("beta")[0].display_name == "Beta"
    assert registry.status() == {
        "required": True,
        "path": registry_path.as_posix(),
        "default_workspace_id": "alpha",
        "count": 2,
        "enabled_count": 2,
    }


def test_workspace_registry_fails_closed_on_duplicate_ids(tmp_path: Path) -> None:
    registry_path = tmp_path / "workspaces.yaml"
    registry_path.write_text(
        f"""
version: test-workspaces-v1
default_workspace_id: alpha
workspaces:
  - id: alpha
    root: {(tmp_path / "alpha").as_posix()}
    display_name: Alpha
  - id: alpha
    root: {(tmp_path / "other").as_posix()}
    display_name: Other
""",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceRegistryError, match="duplicate workspace id"):
        WorkspaceRegistry.load(
            registry_path,
            require_registry=True,
            fallback_root=tmp_path / "fallback",
            default_workspace_id="alpha",
        )


def test_workspace_registry_fails_closed_on_missing_strict_registry(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceRegistryError, match="workspace registry not found"):
        WorkspaceRegistry.load(
            tmp_path / "missing.yaml",
            require_registry=True,
            fallback_root=tmp_path / "fallback",
            default_workspace_id="alpha",
        )


def test_workspace_registry_strict_mode_does_not_fallback_to_overridden_root(
    tmp_path: Path,
) -> None:
    default_like_path = tmp_path / "workspaces" / "local.yaml"

    with pytest.raises(WorkspaceRegistryError, match="workspace registry not found"):
        WorkspaceRegistry.load(
            default_like_path,
            require_registry=True,
            fallback_root=tmp_path / "overridden-workspace",
            default_workspace_id="default",
        )


def test_workspace_registry_can_opt_out_to_fallback_root(tmp_path: Path) -> None:
    registry = WorkspaceRegistry.load(
        tmp_path / "missing.yaml",
        require_registry=False,
        fallback_root=tmp_path / "fallback",
        default_workspace_id="alpha",
    )

    record, root = registry.resolve_active()

    assert record.id == "alpha"
    assert root == (tmp_path / "fallback").resolve(strict=False)
    assert registry.status()["required"] is False


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("version: [", "invalid workspace registry YAML"),
        ("null\n", "workspace registry must be a mapping"),
        ("- alpha\n", "workspace registry must be a mapping"),
        ("1: bad\n", "workspace registry keys must be strings"),
        (
            """
version: test-workspaces-v1
default_workspace_id: alpha
workspaces: []
unexpected: true
""",
            "invalid workspace registry schema",
        ),
        (
            """
version: test-workspaces-v1
default_workspace_id: alpha
workspaces:
  - id: alpha
    root: workspaces
    display_name: Alpha
    metadata: not-an-object
""",
            "invalid workspace registry schema",
        ),
    ],
)
def test_workspace_registry_negative_shapes_fail_closed(
    tmp_path: Path,
    body: str,
    message: str,
) -> None:
    registry_path = tmp_path / "workspaces.yaml"
    registry_path.write_text(body, encoding="utf-8")

    with pytest.raises(WorkspaceRegistryError, match=message):
        WorkspaceRegistry.load(
            registry_path,
            require_registry=True,
            fallback_root=tmp_path / "fallback",
            default_workspace_id="alpha",
        )


def test_workspace_registry_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    registry_path = tmp_path / "workspaces.yaml"
    registry_path.write_text(
        f"""
version: test-workspaces-v1
default_workspace_id: alpha
workspaces:
  - id: alpha
    root: {(tmp_path / "alpha").as_posix()}
    display_name: Alpha
    display_name: Duplicate
""",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceRegistryError, match="duplicate YAML key"):
        WorkspaceRegistry.load(
            registry_path,
            require_registry=True,
            fallback_root=tmp_path / "fallback",
            default_workspace_id="alpha",
        )


def test_workspace_registry_rejects_traversal_roots(tmp_path: Path) -> None:
    registry_path = tmp_path / "workspaces.yaml"
    registry_path.write_text(
        """
version: test-workspaces-v1
default_workspace_id: alpha
workspaces:
  - id: alpha
    root: ../outside
    display_name: Alpha
""",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceRegistryError, match="workspace root must not contain traversal"):
        WorkspaceRegistry.load(
            registry_path,
            require_registry=True,
            fallback_root=tmp_path / "fallback",
            default_workspace_id="alpha",
        )


def test_workspace_registry_rejects_malformed_workspace_ids(tmp_path: Path) -> None:
    registry_path = tmp_path / "workspaces.yaml"
    registry_path.write_text(
        f"""
version: test-workspaces-v1
default_workspace_id: alpha/beta
workspaces:
  - id: alpha/beta
    root: {(tmp_path / "alpha").as_posix()}
    display_name: Alpha
""",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceRegistryError, match="malformed workspace id"):
        WorkspaceRegistry.load(
            registry_path,
            require_registry=True,
            fallback_root=tmp_path / "fallback",
            default_workspace_id="alpha",
        )


def test_workspace_registry_rejects_missing_default_workspace(tmp_path: Path) -> None:
    registry_path = tmp_path / "workspaces.yaml"
    registry_path.write_text(
        f"""
version: test-workspaces-v1
default_workspace_id: missing
workspaces:
  - id: alpha
    root: {(tmp_path / "alpha").as_posix()}
    display_name: Alpha
""",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceRegistryError, match="default workspace not found"):
        WorkspaceRegistry.load(
            registry_path,
            require_registry=True,
            fallback_root=tmp_path / "fallback",
            default_workspace_id="alpha",
        )


def test_workspace_registry_rejects_disabled_default_workspace(tmp_path: Path) -> None:
    registry_path = tmp_path / "workspaces.yaml"
    registry_path.write_text(
        f"""
version: test-workspaces-v1
default_workspace_id: alpha
workspaces:
  - id: alpha
    root: {(tmp_path / "alpha").as_posix()}
    display_name: Alpha
    enabled: false
""",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceRegistryError, match="default workspace is disabled"):
        WorkspaceRegistry.load(
            registry_path,
            require_registry=True,
            fallback_root=tmp_path / "fallback",
            default_workspace_id="alpha",
        )


def test_workspace_registry_rejects_disabled_named_workspace_for_active_use(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "workspaces.yaml"
    registry_path.write_text(
        f"""
version: test-workspaces-v1
default_workspace_id: alpha
workspaces:
  - id: alpha
    root: {(tmp_path / "alpha").as_posix()}
    display_name: Alpha
  - id: beta
    root: {(tmp_path / "beta").as_posix()}
    display_name: Beta
    enabled: false
""",
        encoding="utf-8",
    )
    registry = WorkspaceRegistry.load(
        registry_path,
        require_registry=True,
        fallback_root=tmp_path / "fallback",
        default_workspace_id="alpha",
    )

    with pytest.raises(WorkspaceRegistryError, match="workspace is disabled: beta"):
        registry.resolve_active("beta")


def test_read_executor_keeps_named_workspaces_isolated(tmp_path: Path) -> None:
    registry_path = tmp_path / "workspaces.yaml"
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    alpha.mkdir()
    beta.mkdir()
    alpha.joinpath("note.txt").write_text("alpha", encoding="utf-8")
    beta.joinpath("note.txt").write_text("beta", encoding="utf-8")
    write_registry(registry_path, alpha, beta)
    registry = WorkspaceRegistry.load(
        registry_path,
        require_registry=True,
        fallback_root=tmp_path / "fallback",
        default_workspace_id="alpha",
    )
    executor = ReadToolExecutor.from_settings(
        workspace_root=tmp_path / "fallback",
        max_read_bytes=1024,
        search_result_limit=10,
        git_log_limit=10,
        workspace_registry=registry,
    )

    assert executor.execute("fs.read", {"path": "note.txt"})["content"] == "alpha"
    beta_read = executor.execute("fs.read", {"workspace_id": "beta", "path": "note.txt"})
    assert beta_read["workspace_id"] == "beta"
    assert beta_read["content"] == "beta"
    with pytest.raises(ReadToolError, match="unknown workspace"):
        executor.execute("fs.read", {"workspace_id": "missing", "path": "note.txt"})

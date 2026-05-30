from __future__ import annotations

from pathlib import Path

import pytest
from ithildin_api.identity import (
    DisabledPrincipalError,
    PrincipalRegistry,
    PrincipalRegistryError,
    UnknownPrincipalError,
)


def write_registry(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_principal_registry_loads_seed_records() -> None:
    registry = PrincipalRegistry.load(Path("principals/local.yaml"))

    principal = registry.resolve_active("agent:mcp-local")
    model_principal = registry.resolve_active("model:ollama-local")

    assert registry.count >= 3
    assert principal.trusted_principal() == {
        "id": "agent:mcp-local",
        "type": "agent",
        "roles": ["AgentDeveloper"],
    }
    assert model_principal.trusted_principal() == {
        "id": "model:ollama-local",
        "type": "model",
        "roles": ["AgentReadOnly"],
    }


def test_principal_registry_requires_file_when_strict(tmp_path: Path) -> None:
    with pytest.raises(PrincipalRegistryError, match="not found"):
        PrincipalRegistry.load(tmp_path / "missing.yaml", require_registry=True)


def test_principal_registry_can_opt_out_of_missing_file(tmp_path: Path) -> None:
    registry = PrincipalRegistry.load(tmp_path / "missing.yaml", require_registry=False)

    assert registry.count == 0


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("principals: [", "invalid YAML principal registry"),
        ("null\n", "principal registry must be a mapping"),
        ("- agent:test\n", "principal registry must be a mapping"),
        ("1: bad\n", "principal registry keys must be strings"),
        (
            """
principals:
  - id: agent:test
    type: agent
    display_name: Test
    roles: [AgentDeveloper]
    unexpected: true
""",
            "invalid principal registry schema",
        ),
        (
            """
principals:
  - id: agent:test
    type: agent
    display_name: Test
    roles: [AgentDeveloper]
    metadata: not-an-object
""",
            "invalid principal registry schema",
        ),
    ],
)
def test_principal_registry_negative_shapes_fail_closed(
    tmp_path: Path,
    body: str,
    message: str,
) -> None:
    registry_path = tmp_path / "principals.yaml"
    write_registry(registry_path, body)

    with pytest.raises(PrincipalRegistryError, match=message):
        PrincipalRegistry.load(registry_path)


def test_principal_registry_rejects_duplicate_ids(tmp_path: Path) -> None:
    registry_path = tmp_path / "principals.yaml"
    write_registry(
        registry_path,
        """
principals:
  - id: agent:test
    type: agent
    display_name: One
    roles: [AgentDeveloper]
  - id: agent:test
    type: agent
    display_name: Two
    roles: [AgentReadOnly]
""",
    )

    with pytest.raises(PrincipalRegistryError, match="duplicate principal id"):
        PrincipalRegistry.load(registry_path)


def test_principal_registry_rejects_invalid_roles(tmp_path: Path) -> None:
    registry_path = tmp_path / "principals.yaml"
    write_registry(
        registry_path,
        """
principals:
  - id: agent:test
    type: agent
    display_name: Test
    roles: [Root]
""",
    )

    with pytest.raises(PrincipalRegistryError, match="invalid principal registry schema"):
        PrincipalRegistry.load(registry_path)


def test_principal_registry_rejects_malformed_ids(tmp_path: Path) -> None:
    registry_path = tmp_path / "principals.yaml"
    write_registry(
        registry_path,
        """
principals:
  - id: local-dev
    type: agent
    display_name: Test
    roles: [AgentDeveloper]
""",
    )

    with pytest.raises(PrincipalRegistryError, match="invalid principal registry schema"):
        PrincipalRegistry.load(registry_path)


def test_principal_registry_rejects_id_type_mismatch(tmp_path: Path) -> None:
    registry_path = tmp_path / "principals.yaml"
    write_registry(
        registry_path,
        """
principals:
  - id: agent:test
    type: user
    display_name: Test
    roles: [AgentDeveloper]
""",
    )

    with pytest.raises(PrincipalRegistryError, match="principal id/type mismatch"):
        PrincipalRegistry.load(registry_path)


def test_principal_registry_rejects_disabled_principal_for_active_use(tmp_path: Path) -> None:
    registry_path = tmp_path / "principals.yaml"
    write_registry(
        registry_path,
        """
principals:
  - id: agent:test
    type: agent
    display_name: Test
    roles: [AgentDeveloper]
    enabled: false
""",
    )
    registry = PrincipalRegistry.load(registry_path)

    with pytest.raises(DisabledPrincipalError, match="disabled principal"):
        registry.resolve_active("agent:test")


def test_principal_registry_rejects_unknown_principal() -> None:
    registry = PrincipalRegistry.load(Path("principals/local.yaml"))

    with pytest.raises(UnknownPrincipalError, match="unknown principal"):
        registry.get("agent:missing")

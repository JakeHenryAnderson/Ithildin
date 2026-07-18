from __future__ import annotations

from pathlib import Path

import pytest
from ithildin_api.trusted_host_registry import (
    TRUSTED_HOST_REGISTRY_SCHEMA_DIGEST,
    TrustedHostDescriptorRegistry,
    TrustedHostRegistryError,
)


def test_local_trusted_host_registry_resolves_safe_authority() -> None:
    registry = TrustedHostDescriptorRegistry.load(Path("trusted-hosts/local.yaml"))
    authority = registry.resolve(
        workspace_id="default",
        staging_label="host-staging://artifact",
    )

    assert authority.descriptor_id == "thd_manager_local_artifact"
    assert authority.registry_schema_digest == TRUSTED_HOST_REGISTRY_SCHEMA_DIGEST
    assert authority.descriptor_hash.startswith("sha256:")
    assert registry.status()["raw_paths_included"] is False


def test_trusted_host_registry_rejects_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "trusted-hosts.yaml"
    path.write_text(_registry_yaml("    raw_root: /tmp/not-allowed\n"), encoding="utf-8")

    with pytest.raises(TrustedHostRegistryError, match="invalid trusted-host registry schema"):
        TrustedHostDescriptorRegistry.load(path)


def test_trusted_host_registry_rejects_duplicate_binding(tmp_path: Path) -> None:
    path = tmp_path / "trusted-hosts.yaml"
    path.write_text(
        "version: \"2\"\n"
        f"registry_schema_digest: \"{TRUSTED_HOST_REGISTRY_SCHEMA_DIGEST}\"\n"
        "descriptors:\n"
        f"{_descriptor_yaml('thd_first')}{_descriptor_yaml('thd_second')}",
        encoding="utf-8",
    )

    with pytest.raises(TrustedHostRegistryError, match="duplicate trusted-host workspace/label"):
        TrustedHostDescriptorRegistry.load(path)


def test_trusted_host_registry_rejects_unknown_or_disabled_destination(tmp_path: Path) -> None:
    path = tmp_path / "trusted-hosts.yaml"
    path.write_text(_registry_yaml("", enabled=False), encoding="utf-8")
    registry = TrustedHostDescriptorRegistry.load(path)

    with pytest.raises(TrustedHostRegistryError, match="does not resolve exactly once"):
        registry.resolve(workspace_id="default", staging_label="host-staging://artifact")
    with pytest.raises(TrustedHostRegistryError, match="does not resolve exactly once"):
        registry.resolve(workspace_id="other", staging_label="host-staging://artifact")


def _registry_yaml(extra: str, *, enabled: bool = True) -> str:
    return (
        "version: \"2\"\n"
        f"registry_schema_digest: \"{TRUSTED_HOST_REGISTRY_SCHEMA_DIGEST}\"\n"
        "descriptors:\n"
        + _descriptor_yaml("thd_test", extra=extra, enabled=enabled)
    )


def _descriptor_yaml(
    descriptor_id: str,
    *,
    extra: str = "",
    enabled: bool = True,
) -> str:
    return (
        "  - descriptor_schema_version: \"2\"\n"
        f"    descriptor_id: {descriptor_id}\n"
        f"    enabled: {str(enabled).lower()}\n"
        "    os_family: darwin\n"
        "    filesystem_posture: local_create_exclusive\n"
        "    operator_review_status: reviewed\n"
        "    evidence_timestamp: 2026-07-18T00:00:00Z\n"
        "    workspace_id: default\n"
        "    staging_label: host-staging://artifact\n"
        "    staging_root_resolver_ref: manager_local_trusted_host_staging_root\n"
        "    staging_create_exclusive_allowed: true\n"
        "    host_write_allowed: false\n"
        "    broad_host_write_allowed: false\n"
        f"{extra}"
    )

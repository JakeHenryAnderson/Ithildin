from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts import enterprise_e1_single_site, enterprise_e1_single_site_deployment_check


def _environment(tmp_path: Path) -> dict[str, str]:
    inventory = tmp_path / "runtime-candidate-inventory.json"
    inventory.write_text('{"inventory":"fixture"}\n', encoding="utf-8")
    inventory.chmod(0o444)
    authority = tmp_path / "api-candidate.json"
    authority.write_text('{"candidate":"fixture"}\n', encoding="utf-8")
    authority.chmod(0o400)
    return {
        "ITHILDIN_E1_SITE_ID": "site-001",
        "ITHILDIN_E1_VERSION": "1.0.0-e1",
        "ITHILDIN_E1_SOURCE_REVISION": enterprise_e1_single_site._git_one(
            enterprise_e1_single_site.ROOT,
            "rev-parse",
            "HEAD",
        ),
        "ITHILDIN_E1_API_PORT": "18000",
        "ITHILDIN_E1_UI_PORT": "15173",
        "ITHILDIN_E1_DATA_ROOT": str(tmp_path / "site-001"),
        "ITHILDIN_E1_RUNTIME_INVENTORY_PATH": str(inventory),
        "ITHILDIN_E1_RUNTIME_AUTHORITY_PATH": str(authority),
        "ITHILDIN_E1_EXPECTED_RUNTIME_POSTURE": "unreviewed_local",
        "ITHILDIN_ADMIN_TOKEN": "fixture-token-with-more-than-32-characters",
        "ITHILDIN_CONTAINER_UID": str(os.getuid()),
        "ITHILDIN_CONTAINER_GID": str(os.getgid()),
    }


def test_single_site_bootstrap_creates_only_private_owned_state(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    config = enterprise_e1_single_site.validate_environment(
        environment,
        enterprise_e1_single_site.ROOT,
        require_current_source=False,
    )

    enterprise_e1_single_site.bootstrap_state(config)

    expected = (Path("."), *enterprise_e1_single_site.STATE_DIRECTORIES)
    for relative in expected:
        path = config.data_root / relative
        assert path.is_dir()
        assert path.stat().st_mode & 0o777 == 0o700
        assert path.stat().st_uid == os.getuid()
        assert path.stat().st_gid == os.getgid()
    summary = config.safe_summary()
    assert summary["admin_token_configured"] is True
    assert "fixture-token" not in str(summary)
    assert summary["storage_backend"] == "sqlite"
    assert summary["docker_authority_granted"] is False
    assert summary["optional_node_in_m1"] is False
    assert summary["expected_runtime_posture"] == "unreviewed_local"


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("ITHILDIN_ADMIN_TOKEN", "dev-admin-token-change-me", "admin token"),
        ("ITHILDIN_E1_API_PORT", "15173", "ports must be distinct"),
        ("ITHILDIN_E1_DATA_ROOT", "relative/state", "explicit absolute path"),
        ("ITHILDIN_E1_SOURCE_REVISION", "0" * 40, "does not match"),
        ("ITHILDIN_CONTAINER_UID", "999999", "must match"),
        ("ITHILDIN_E1_EXPECTED_RUNTIME_POSTURE", "assumed", "expected runtime posture"),
    ],
)
def test_single_site_environment_rejects_unsafe_inputs(
    tmp_path: Path,
    key: str,
    value: str,
    message: str,
) -> None:
    environment = _environment(tmp_path)
    environment[key] = value

    with pytest.raises(enterprise_e1_single_site.SingleSiteError, match=message):
        enterprise_e1_single_site.validate_environment(
            environment,
            enterprise_e1_single_site.ROOT,
            require_current_source=key == "ITHILDIN_E1_SOURCE_REVISION",
        )


def test_single_site_environment_file_is_closed_owner_only_and_duplicate_safe(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    path = tmp_path / "ithildin-e1.env"
    path.write_text(
        "\n".join(f"{key}={value}" for key, value in environment.items()) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)

    assert enterprise_e1_single_site.load_env_file(path) == environment
    path.chmod(0o644)
    with pytest.raises(enterprise_e1_single_site.SingleSiteError, match="mode must be 0600"):
        enterprise_e1_single_site.load_env_file(path)
    path.chmod(0o600)
    text = path.read_text(encoding="utf-8")
    path.write_text(text + f"ITHILDIN_E1_SITE_ID={environment['ITHILDIN_E1_SITE_ID']}\n")
    with pytest.raises(enterprise_e1_single_site.SingleSiteError, match="duplicate key"):
        enterprise_e1_single_site.load_env_file(path)


def test_single_site_state_rejects_symlink_or_unsafe_mode(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    config = enterprise_e1_single_site.validate_environment(
        environment,
        enterprise_e1_single_site.ROOT,
        require_current_source=False,
    )
    target = tmp_path / "elsewhere"
    target.mkdir(mode=0o700)
    config.data_root.symlink_to(target)

    with pytest.raises(enterprise_e1_single_site.SingleSiteError, match="not a directory"):
        enterprise_e1_single_site.bootstrap_state(config)

    config.data_root.unlink()
    enterprise_e1_single_site.bootstrap_state(config)
    (config.data_root / "gateway").chmod(0o755)
    with pytest.raises(enterprise_e1_single_site.SingleSiteError, match="mode must be 0700"):
        enterprise_e1_single_site.validate_state(config)
    (config.data_root / "gateway").chmod(0o700)
    config.runtime_inventory_path.chmod(0o600)
    with pytest.raises(enterprise_e1_single_site.SingleSiteError, match="inventory mode"):
        enterprise_e1_single_site.validate_state(config)


def test_single_site_static_deployment_contract_is_valid() -> None:
    report = enterprise_e1_single_site_deployment_check.build_report(
        enterprise_e1_single_site_deployment_check.ROOT
    )

    assert report["valid"] is True, report["failures"]
    assert report["services"] == ["ithildin-api", "ithildin-ui"]
    assert report["service_count"] == 2
    assert report["tool_count"] == 24
    assert report["loopback_only"] is True
    assert report["storage_backend"] == "sqlite"
    assert report["runtime_postgres_allowed"] is False
    assert report["docker_authority_granted"] is False
    assert report["optional_node_in_m1"] is False
    assert report["human_uat_complete"] is False

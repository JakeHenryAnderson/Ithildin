from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import filesystem_contract_check


def test_filesystem_contract_check_json_contains_required_fields(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = filesystem_contract_check.main(["--json"])

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["probe"]["uses_temporary_directory"] is True
    assert payload["probe"]["touches_workspace"] is False
    assert "o_no_follow_available" in payload["capabilities"]
    assert "symlink_supported" in payload["capabilities"]
    assert "hardlink_supported" in payload["capabilities"]
    assert "case_sensitive" in payload["capabilities"]
    assert payload["support"]["status"] in {"supported", "degraded", "unsupported"}


def test_platform_profiles_report_supported_for_macos_and_linux(tmp_path: Path) -> None:
    macos = filesystem_contract_check.collect_filesystem_contract_status(
        system="Darwin",
        release="23.0.0",
        probe_parent=tmp_path,
    )
    linux = filesystem_contract_check.collect_filesystem_contract_status(
        system="Linux",
        release="6.8.0",
        probe_parent=tmp_path,
    )

    assert macos["platform"]["profile"] == "macos"
    assert linux["platform"]["profile"] == "linux"
    assert macos["support"]["status"] in {"supported", "degraded"}
    assert linux["support"]["status"] in {"supported", "degraded"}


def test_platform_profiles_report_windows_and_wsl_as_unsupported(tmp_path: Path) -> None:
    windows = filesystem_contract_check.collect_filesystem_contract_status(
        system="Windows",
        release="11",
        probe_parent=tmp_path,
    )
    wsl = filesystem_contract_check.collect_filesystem_contract_status(
        system="Linux",
        release="5.15.90.1-microsoft-standard-WSL2",
        probe_parent=tmp_path,
    )
    unknown = filesystem_contract_check.collect_filesystem_contract_status(
        system="Plan9",
        release="unknown",
        probe_parent=tmp_path,
    )

    assert windows["platform"]["profile"] == "windows"
    assert wsl["platform"]["profile"] == "wsl"
    assert unknown["platform"]["profile"] == "unknown"
    assert windows["support"]["status"] == "unsupported"
    assert wsl["support"]["status"] == "unsupported"
    assert unknown["support"]["status"] == "unsupported"


def test_probe_uses_only_temporary_directory(tmp_path: Path) -> None:
    before = set(tmp_path.iterdir())

    filesystem_contract_check.collect_filesystem_contract_status(probe_parent=tmp_path)

    assert set(tmp_path.iterdir()) == before

"""Report local filesystem capability evidence for Ithildin's executor contract."""

from __future__ import annotations

import argparse
import json
import os
import platform
import tempfile
from pathlib import Path
from typing import Any


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv)

    status = collect_filesystem_contract_status()
    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        print(_format_human(status))
    return 0 if status["support"]["local_preview_security_supported"] is True else 1


def collect_filesystem_contract_status(
    *,
    system: str | None = None,
    release: str | None = None,
    machine: str | None = None,
    python_version: str | None = None,
    probe_parent: Path | None = None,
) -> dict[str, Any]:
    resolved_system = system or platform.system()
    resolved_release = release or platform.release()
    profile = _platform_profile(resolved_system, resolved_release)
    capabilities = _probe_capabilities(probe_parent)
    supported_platform = profile in {"macos", "linux"}
    required_capabilities = bool(capabilities["o_no_follow_available"])
    local_preview_supported = supported_platform and required_capabilities

    if not supported_platform:
        support_status = "unsupported"
        reason = "platform is not security-supported for local-preview filesystem claims"
    elif not required_capabilities:
        support_status = "degraded"
        reason = "platform is supported, but required filesystem capability evidence is missing"
    else:
        support_status = "supported"
        reason = "platform and required filesystem capability evidence match the contract"

    return {
        "platform": {
            "system": resolved_system,
            "profile": profile,
            "release": resolved_release,
            "machine": machine or platform.machine(),
        },
        "python": {"version": python_version or platform.python_version()},
        "capabilities": capabilities,
        "support": {
            "status": support_status,
            "local_preview_security_supported": local_preview_supported,
            "reason": reason,
        },
        "probe": {
            "uses_temporary_directory": True,
            "touches_workspace": False,
        },
    }


def _probe_capabilities(probe_parent: Path | None) -> dict[str, bool]:
    with tempfile.TemporaryDirectory(prefix="ithildin-fs-contract-", dir=probe_parent) as tmp:
        root = Path(tmp)
        target = root / "target.txt"
        target.write_text("probe\n", encoding="utf-8")
        symlink_supported = _probe_symlink(target, root / "target-link.txt")
        hardlink_supported = _probe_hardlink(target, root / "target-hardlink.txt")
        return {
            "o_no_follow_available": hasattr(os, "O_NOFOLLOW"),
            "symlink_supported": symlink_supported,
            "hardlink_supported": hardlink_supported,
            "case_sensitive": _probe_case_sensitive(root),
        }


def _probe_symlink(target: Path, link: Path) -> bool:
    try:
        link.symlink_to(target)
    except OSError:
        return False
    return link.is_symlink()


def _probe_hardlink(target: Path, link: Path) -> bool:
    try:
        os.link(target, link)
    except OSError:
        return False
    return link.exists()


def _probe_case_sensitive(root: Path) -> bool:
    lower = root / "case_probe"
    upper = root / "CASE_PROBE"
    lower.write_text("case\n", encoding="utf-8")
    return not upper.exists()


def _platform_profile(system: str, release: str) -> str:
    normalized_system = system.lower()
    normalized_release = release.lower()
    if normalized_system == "darwin":
        return "macos"
    if normalized_system == "linux":
        if "microsoft" in normalized_release or "wsl" in normalized_release:
            return "wsl"
        return "linux"
    if normalized_system == "windows":
        return "windows"
    return "unknown"


def _format_human(status: dict[str, Any]) -> str:
    platform_status = status["platform"]
    capabilities = status["capabilities"]
    support = status["support"]
    return "\n".join(
        [
            "Ithildin filesystem contract check",
            f"platform: {platform_status['system']} ({platform_status['profile']})",
            f"python: {status['python']['version']}",
            f"O_NOFOLLOW available: {capabilities['o_no_follow_available']}",
            f"symlink supported: {capabilities['symlink_supported']}",
            f"hardlink supported: {capabilities['hardlink_supported']}",
            f"temporary filesystem case-sensitive: {capabilities['case_sensitive']}",
            f"local-preview support status: {support['status']}",
            f"reason: {support['reason']}",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())

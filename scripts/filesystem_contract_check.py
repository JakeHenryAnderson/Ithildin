"""Report local filesystem capability evidence for Ithildin's executor contract."""

from __future__ import annotations

import argparse
import json
from typing import Any

from ithildin_api.filesystem_contract import collect_filesystem_contract_status

__all__ = ["collect_filesystem_contract_status", "main"]


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
            f"O_DIRECTORY available: {capabilities.get('o_directory_available', False)}",
            f"dir_fd open supported: {capabilities.get('dir_fd_open_supported', False)}",
            f"dir_fd mkdir supported: {capabilities.get('dir_fd_mkdir_supported', False)}",
            f"dir_fd stat supported: {capabilities.get('dir_fd_stat_supported', False)}",
            f"symlink supported: {capabilities['symlink_supported']}",
            f"hardlink supported: {capabilities['hardlink_supported']}",
            f"temporary filesystem case-sensitive: {capabilities['case_sensitive']}",
            f"local-preview support status: {support['status']}",
            "descriptor-relative placement supported: "
            f"{support.get('descriptor_relative_placement_supported', False)}",
            f"reason: {support['reason']}",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())

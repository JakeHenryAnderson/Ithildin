"""Print local MCP Inspector recipe prerequisites and stdio configuration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_MARKERS = (
    "pyproject.toml",
    "Makefile",
    "apps/mcp-server",
    "tool-manifests.lock.json",
    "docs/codex/mcp-inspector-recipes.md",
)

RECIPES = [
    "tools/list shows role-filtered governed tools",
    "fs.list reads the configured demo workspace",
    "unknown tool calls return safe denial metadata",
    "fs.patch.propose stores a reviewable patch proposal",
    "fs.patch.apply with proposal_id returns approval_required",
    "approved fs.patch.apply with approval_id consumes the approval once",
    "audit verification shows the resulting evidence chain",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    marker_status = {marker: repo_root.joinpath(marker).exists() for marker in PROJECT_MARKERS}
    missing = [marker for marker, present in marker_status.items() if not present]
    if missing:
        print(
            "MCP Inspector recipes must be run from the Ithildin repo root; "
            f"missing markers: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    payload: dict[str, Any] = {
        "repo_root": repo_root.as_posix(),
        "server": {
            "command": "uv",
            "args": ["run", "python", "-m", "ithildin_mcp_server"],
            "cwd": repo_root.as_posix(),
        },
        "env_notes": [
            "Use the same .env settings as the API.",
            "Set a unique ITHILDIN_ADMIN_TOKEN for local use.",
            "Keep ITHILDIN_WORKSPACE_ROOT narrow.",
        ],
        "recipes": RECIPES,
        "docs": "docs/codex/mcp-inspector-recipes.md",
    }

    if args.json:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    print("MCP Inspector recipe prerequisites passed.")
    print(f"Docs: {payload['docs']}")
    print("Stdio server:")
    print("  command: uv")
    print("  args: run python -m ithildin_mcp_server")
    print(f"  cwd: {repo_root}")
    print("Recipes:")
    for recipe in RECIPES:
        print(f"  - {recipe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
